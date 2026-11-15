"""Macchina configurabile con tre tipi di trigger per i fermi."""
from copy import deepcopy
import random

from .config import validate_machine
from .distributions import sample
from .history import History

class ProductionMachine:
    """Unico processo: riparazioni sequenziali, orologi attivi solo in lavorazione."""

    def __init__(self, env, config, inlet=None, outlet=None, rng=None,
                 history_limit=2000, recorder=None):
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
        self.recorder = recorder
        self.stat = History(history_limit,
                            (lambda row: recorder.write('machines', row)) if recorder else None)
        self.events = History(history_limit)
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
        if self.recorder is not None:
            self.recorder.write('stops', event)
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
