"""Esecuzione della linea con memoria limitata e CSV incrementali."""
from copy import deepcopy
from contextlib import ExitStack
import random

import pandas as pd
import simpy

from .buffer import Buffer
from .config import load_config, validate_line
from .distributions import number
from .history import CsvRecorder, History
from .machine import ProductionMachine

EVENT_COLUMNS = ['machine', 'reason', 'trigger', 'start', 'end', 'planned_duration',
                 'elapsed_duration', 'completed', 'blocks_machine']
MACHINE_COLUMNS = ['name', 'time', 'status', 'stop_reason', 'takt', 'running',
                   'standby', 'failed_time', 'counter', 'stops', 'processing_time',
                   'actual_cycle_time', 'time_between_completions']


def run_simulation(hours=8736.0, seed=None, config=None, return_events=False,
                   history_limit=2000, csv_dir=None, progress=None):
    """Esegue il modello con storici limitati; csv_dir registra ogni record.

    I DataFrame restituiti sono campionati oltre history_limit righe per serie.
    history_limit=None conserva tutto in memoria, per sole prove brevi.
    """
    number(hours, 'hours')
    if hours <= 0:
        raise ValueError('hours deve essere positivo')
    History(history_limit)  # Valida prima di creare file o avviare processi.
    config = deepcopy(config) if config is not None else load_config()
    validate_line(config)
    env, rng = simpy.Environment(), random.Random(seed)
    reasons = list(dict.fromkeys(reason for m in config['machines'] for reason in m.get('stops', {})))
    fields = [*MACHINE_COLUMNS, *[f'stop_count:{r}' for r in reasons],
              *[f'downtime:{r}' for r in reasons], *[f'event_time:{r}' for r in reasons]]
    with ExitStack() as stack:
        recorder = stack.enter_context(CsvRecorder(csv_dir, fields, EVENT_COLUMNS)) if csv_dir is not None else None
        buffers = {b['name']: Buffer(env, **b, history_limit=history_limit, recorder=recorder)
                   for b in config.get('buffers', [])}
        machines = [ProductionMachine(env, m, buffers.get(m.get('inlet')),
                                      buffers.get(m.get('outlet')), rng,
                                      history_limit=history_limit, recorder=recorder)
                    for m in config['machines']]
        if progress is None:
            env.run(until=hours)
        else:
            for part in range(1, 21):
                target = hours if part == 20 else hours * part / 20
                if target > env.now:
                    env.run(until=target)
                    progress(env.now, hours)
        for machine in machines:
            machine.save()
            if recorder is not None:
                active = list(machine.parallel_events.values())
                if machine.current_event is not None:
                    active.append(machine.current_event)
                for event in active:
                    recorder.write('stops', event)
        for buffer in buffers.values():
            buffer.save()
    machine_df = pd.DataFrame([row for m in machines for row in m.stat.records()])
    buffer_df = pd.DataFrame([row for b in buffers.values() for row in b.stat.records()],
                             columns=['name', 'time', 'level', 'capacity'])
    events = pd.DataFrame([event for m in machines for event in m.events.records()], columns=EVENT_COLUMNS)
    events = events.sort_values('start', kind='stable').reset_index(drop=True)
    for frame, histories in [(machine_df, [m.stat for m in machines]),
                              (buffer_df, [b.stat for b in buffers.values()]),
                              (events, [m.events for m in machines])]:
        frame.attrs['history_sampled'] = any(h.sampled for h in histories)
        frame.attrs['total_records'] = sum(h.total for h in histories)
    if return_events:
        return machine_df, buffer_df, events
    return machine_df, buffer_df
