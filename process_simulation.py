"""Simulazione Ford Scorpion con fermi configurabili; tempi interni in ore."""

import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import random

import pandas as pd
import simpy

UNITS = {'seconds': 1 / 3600, 'minutes': 1 / 60, 'hours': 1.0}
DEFAULT_CONFIG = Path(__file__).with_name('line_config.md')
EVENT_COLUMNS = ['machine', 'reason', 'trigger', 'start', 'end', 'planned_duration',
                 'elapsed_duration', 'completed']


def number(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label}: richiesto un numero')
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f'{label}: valore non valido {value}')
    return value


def validate_distribution(spec, positive=False):
    if not isinstance(spec, dict):
        raise ValueError('La distribuzione deve essere un oggetto')
    kind = spec.get('distribution')
    if spec.get('unit') not in UNITS:
        raise ValueError('Unità consentite: seconds, minutes, hours')
    if kind == 'fixed':
        mean = number(spec.get('value'), 'value')
    elif kind in ('normal', 'lognormal', 'exponential'):
        mean = number(spec.get('mean'), 'mean')
        if kind != 'exponential':
            std = number(spec.get('std'), 'std')
            if kind == 'lognormal' and mean == 0 and std != 0:
                raise ValueError('Lognormale: mean deve essere positivo se std > 0')
    else:
        raise ValueError(f'Distribuzione sconosciuta: {kind}')
    if (positive or kind == 'exponential') and mean <= 0:
        raise ValueError('La media deve essere positiva')


def sample(spec, rng, positive=False):
    """Lognormale parametrizzata con media e deviazione fisiche, non logaritmiche."""
    kind = spec['distribution']
    for _ in range(1000):
        if kind == 'fixed':
            value = spec['value']
        elif kind == 'normal':
            value = rng.gauss(spec['mean'], spec['std'])
        elif kind == 'exponential':
            value = rng.expovariate(1 / spec['mean'])
        else:
            mean, std = spec['mean'], spec['std']
            if std == 0:
                value = mean
            else:
                sigma2 = math.log1p((std / mean) ** 2)
                value = rng.lognormvariate(math.log(mean) - sigma2 / 2, math.sqrt(sigma2))
        value *= UNITS[spec['unit']]
        if not math.isfinite(value):
            raise ValueError('Campione non finito: verificare i parametri')
        if not positive:
            return max(0.0, value)
        if value > 0:
            return value
    raise ValueError('Impossibile campionare un tempo strettamente positivo')


def validate_machine(config):
    if not isinstance(config, dict) or not isinstance(config.get('name'), str) or not config['name']:
        raise ValueError('Ogni macchina deve avere un nome non vuoto')
    validate_distribution(config.get('cycle_time'), positive=True)
    stops = config.get('stops', {})
    if not isinstance(stops, dict):
        raise ValueError('stops deve essere un oggetto con nomi liberi')
    for reason, stop in stops.items():
        if not isinstance(reason, str) or not reason or not isinstance(stop, dict):
            raise ValueError('Definizione del fermo non valida')
        validate_distribution(stop.get('time_to_repair'))
        trigger = stop.get('trigger', {})
        if not isinstance(trigger, dict):
            raise ValueError('trigger deve essere un oggetto')
        kind = trigger.get('type')
        if kind == 'operating_time':
            validate_distribution(trigger, positive=True)
        elif kind == 'per_cycle':
            if number(trigger.get('probability'), 'probability') > 1:
                raise ValueError('probability deve essere compresa tra 0 e 1')
        elif kind == 'cycle_count':
            every = trigger.get('every')
            if isinstance(every, bool) or not isinstance(every, int) or every <= 0:
                raise ValueError('every deve essere un intero positivo')
        else:
            raise ValueError(f'Trigger sconosciuto: {kind}')


class Buffer:
    def __init__(self, env, name, capacity, init=0):
        self.env, self.name = env, name
        self.capacity = capacity
        self.buff = simpy.Container(env, capacity=capacity, init=init)
        self.stat = []
        self.save()

    def save(self):
        self.stat.append(dict(name=self.name, time=self.env.now,
                              level=self.buff.level, capacity=self.capacity))


class ProductionMachine:
    """Unico processo: riparazioni sequenziali, orologi attivi solo in lavorazione."""

    def __init__(self, env, config, inlet=None, outlet=None, rng=None):
        validate_machine(config)
        self.env, self.config = env, deepcopy(config)
        self.name = config['name']
        self.inlet, self.outlet = inlet, outlet
        self.rng = rng if rng is not None else random.Random()
        self.stops = self.config.get('stops', {})
        self.remaining = {
            reason: sample(stop['trigger'], self.rng, positive=True)
            for reason, stop in self.stops.items()
            if stop['trigger']['type'] == 'operating_time'
        }
        self.counts = dict.fromkeys(self.stops, 0)
        self.downtimes = dict.fromkeys(self.stops, 0.0)
        self.counter = 0
        self.running = self.standby = self.failed_time = self.takt = 0.0
        self.status, self.reason = 'stand-by', None
        self.since = env.now
        self.stat, self.events = [], []
        self.current_event = None
        self.action = env.process(self.run())

    def accrue(self):
        elapsed = self.env.now - self.since
        if self.status == 'running':
            self.running += elapsed
        elif self.status == 'stand-by':
            self.standby += elapsed
        else:
            self.failed_time += elapsed
            self.downtimes[self.reason] += elapsed
        self.since = self.env.now
        if self.current_event is not None:
            self.current_event['elapsed_duration'] = self.env.now - self.current_event['start']

    def save(self):
        self.accrue()
        row = dict(name=self.name, time=self.env.now, status=self.status,
                   stop_reason=self.reason, takt=self.takt, running=self.running,
                   standby=self.standby, failed_time=self.failed_time,
                   counter=self.counter, stops=sum(self.counts.values()))
        row.update({f'stop_count:{k}': v for k, v in self.counts.items()})
        row.update({f'downtime:{k}': v for k, v in self.downtimes.items()})
        self.stat.append(row)

    def set_state(self, status, reason=None):
        self.accrue()
        self.status, self.reason = status, reason
        self.save()

    def repair(self, reason):
        stop = self.stops[reason]
        duration = sample(stop['time_to_repair'], self.rng)
        self.counts[reason] += 1
        self.set_state('stopped', reason)
        event = dict(machine=self.name, reason=reason, trigger=stop['trigger']['type'],
                     start=self.env.now, end=None, planned_duration=duration,
                     elapsed_duration=0.0, completed=False)
        self.events.append(event)
        self.current_event = event
        yield self.env.timeout(duration)
        self.accrue()
        event.update(end=self.env.now, completed=True)
        self.current_event = None
        if reason in self.remaining:
            self.remaining[reason] = sample(stop['trigger'], self.rng, positive=True)
        self.set_state('running')

    def run(self):
        self.save()
        while True:
            if self.inlet is not None:
                self.set_state('stand-by')
                yield self.inlet.buff.get(1)
                self.inlet.save()
            self.takt = sample(self.config['cycle_time'], self.rng, positive=True)
            work_left = self.takt
            # Ciascun fermo probabilistico è indipendente e può scattare una volta per ciclo.
            per_cycle = {
                reason: self.rng.uniform(0, self.takt)
                for reason, stop in self.stops.items()
                if stop['trigger']['type'] == 'per_cycle'
                and self.rng.random() < stop['trigger']['probability']
            }
            self.set_state('running')
            while True:
                # Anche gli eventi coincidenti con fine ciclo vengono serviti prima dell'uscita.
                deadlines = {**self.remaining, **per_cycle}
                due = [reason for reason in self.stops
                       if reason in deadlines and deadlines[reason] <= 0]
                if due:
                    for reason in due:
                        per_cycle.pop(reason, None)
                        yield from self.repair(reason)
                    continue
                if work_left <= 0:
                    break
                elapsed = min([work_left, *deadlines.values()])
                yield self.env.timeout(elapsed)
                self.accrue()
                work_left = max(0.0, work_left - elapsed)
                for timers in (self.remaining, per_cycle):
                    for reason in timers:
                        timers[reason] = max(0.0, timers[reason] - elapsed)
            if self.outlet is not None:
                self.set_state('stand-by')
                yield self.outlet.buff.put(1)
                self.outlet.save()
            self.counter += 1
            self.set_state('running')
            for reason, stop in self.stops.items():
                trigger = stop['trigger']
                if trigger['type'] == 'cycle_count' and self.counter % trigger['every'] == 0:
                    yield from self.repair(reason)


def load_config(path=DEFAULT_CONFIG):
    path = Path(path)
    if path.suffix.lower() == '.md':
        from markdown_config import parse_markdown
        return parse_markdown(path.read_text(encoding='utf-8'))
    if path.suffix.lower() == '.json':
        with path.open(encoding='utf-8') as stream:
            return json.load(stream)
    raise ValueError('Formato input supportato: .md oppure .json')


def validate_line(config):
    if not isinstance(config, dict) or not config.get('machines'):
        raise ValueError('La linea deve contenere almeno una macchina')
    output = config.get('output', {})
    if not isinstance(output, dict) or set(output) - {'output_dir', 'csv', 'plots'}:
        raise ValueError('Configurazione output non valida')
    for key in ('csv', 'plots'):
        if key in output and not isinstance(output[key], bool):
            raise ValueError(f'output.{key} deve essere booleano')
    if 'output_dir' in output and (not isinstance(output['output_dir'], str) or not output['output_dir']):
        raise ValueError('output_dir deve essere una stringa non vuota')
    buffers = config.get('buffers', [])
    names = [b['name'] for b in buffers]
    if len(names) != len(set(names)):
        raise ValueError('Nomi buffer duplicati')
    for b in buffers:
        if not isinstance(b['name'], str) or not b['name']:
            raise ValueError('Nome buffer non valido')
        if number(b['capacity'], 'capacity') <= 0:
            raise ValueError('capacity deve essere positiva')
        if number(b.get('init', 0), 'init') > b['capacity']:
            raise ValueError('init supera capacity')
    machines = config['machines']
    if len({m['name'] for m in machines}) != len(machines):
        raise ValueError('Nomi macchina duplicati')
    for m in machines:
        validate_machine(m)
        for connection in ('inlet', 'outlet'):
            if m.get(connection) is not None and m[connection] not in names:
                raise ValueError(f"Buffer inesistente: {m[connection]}")


def run_simulation(hours=8736.0, seed=None, config=None, return_events=False):
    number(hours, 'hours')
    if hours <= 0:
        raise ValueError('hours deve essere positivo')
    config = deepcopy(config) if config is not None else load_config()
    validate_line(config)
    env, rng = simpy.Environment(), random.Random(seed)
    buffers = {b['name']: Buffer(env, **b) for b in config.get('buffers', [])}
    machines = [ProductionMachine(env, m, buffers.get(m.get('inlet')),
                                  buffers.get(m.get('outlet')), rng)
                for m in config['machines']]
    env.run(until=hours)
    for machine in machines:
        machine.save()  # Include anche le frazioni di lavoro/attesa/riparazione in corso.
    for buffer in buffers.values():
        buffer.save()
    machine_df = pd.DataFrame([row for m in machines for row in m.stat])
    buffer_df = pd.DataFrame([row for b in buffers.values() for row in b.stat],
                             columns=['name', 'time', 'level', 'capacity'])
    events = pd.DataFrame([event for m in machines for event in m.events], columns=EVENT_COLUMNS)
    events = events.sort_values('start', kind='stable').reset_index(drop=True)
    if return_events:
        return machine_df, buffer_df, events
    return machine_df, buffer_df


def save_plots(machines, buffers, events, output_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    last = machines.groupby('name', sort=False).last()
    charts = [('running', 'Operating time [h]', 'running_time.png'),
              ('failed_time', 'Downtime [h]', 'downtime.png'),
              ('stops', 'Stops', 'stop_count.png')]
    for column, ylabel, filename in charts:
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.bar(last.index, last[column])
        ax.set_ylabel(ylabel)
        ax.tick_params(axis='x', rotation=45)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 3))
    cycles = machines[machines.takt > 0].groupby('name', sort=False)
    groups = list(cycles)
    if groups:
        ax.boxplot([g.takt.to_numpy() * 60 for _, g in groups], showfliers=False)
        ax.set_xticks(range(1, len(groups) + 1), [name for name, _ in groups], rotation=45)
    ax.set_ylabel('Cycle time [min] (samples at state changes)')
    fig.tight_layout()
    fig.savefig(output_dir / 'cycle_time.png', dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 3))
    for name, group in buffers.groupby('name', sort=False):
        ax.step(group.time, group.level, where='post', label=name)
    if not buffers.empty:
        ax.legend()
    ax.set(xlabel='Time [h]', ylabel='Buffer level [units]')
    fig.tight_layout()
    fig.savefig(output_dir / 'buffer_level.png', dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--hours', type=float, default=8736.0)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--output-dir', type=Path, help='Sovrascrive output_dir del documento')
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        machines, buffers, events = run_simulation(args.hours, args.seed,
                                                  config, return_events=True)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    output = config.get('output', {})
    output_dir = args.output_dir or Path(output.get('output_dir', 'results'))
    output_dir.mkdir(parents=True, exist_ok=True)
    if output.get('csv', True):
        for filename, frame in [('machines.csv', machines), ('buffers.csv', buffers), ('stops.csv', events)]:
            frame.to_csv(output_dir / filename, index=False)
    if output.get('plots', True) and not args.no_plots:
        save_plots(machines, buffers, events, output_dir)
    if config.get('title'):
        print(config['title'])
    print(machines.groupby('name', sort=False)[['counter', 'stops', 'running', 'failed_time']].last())
    print(f'Risultati salvati in {output_dir.resolve()}')


if __name__ == '__main__':
    main()
