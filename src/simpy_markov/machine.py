"""Macchina configurabile con tre tipi di trigger per i fermi."""
from copy import deepcopy
import random

from .config import validate_machine
from .distributions import sample
from .history import History

class ProductionMachine:
    """Fermi bloccanti sequenziali o attività parallele; timer di tempo operativo."""

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
        self.event_times = dict.fromkeys(self.stops, 0.0)
        self.parallel_events = {}
        self.processing_time = self.actual_cycle_time = None
        self.time_between_completions = self.previous_completion = None
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
        active = list(self.parallel_events.values())
        if self.current_event is not None:
            active.append(self.current_event)
        for event in active:
            elapsed_event = self.env.now - event['start']
            self.event_times[event['reason']] += elapsed_event - event['elapsed_duration']
            event['elapsed_duration'] = elapsed_event

    def save(self):
        self.accrue()
        row = dict(name=self.name, time=self.env.now, status=self.status,
                   stop_reason=self.reason, takt=self.takt, running=self.running,
                   standby=self.standby, failed_time=self.failed_time,
                   counter=self.counter, stops=sum(self.counts.values()),
                   processing_time=self.processing_time, actual_cycle_time=self.actual_cycle_time,
                   time_between_completions=self.time_between_completions)
        row.update({f'stop_count:{k}': v for k, v in self.counts.items()})
        row.update({f'downtime:{k}': v for k, v in self.downtimes.items()})
        row.update({f'event_time:{k}': v for k, v in self.event_times.items()})
        self.stat.append(row)

    def set_state(self, status, reason=None):
        self.accrue()
        self.status, self.reason = status, reason
        self.save()

    def finish_event(self, event):
        self.accrue()
        event.update(end=self.env.now, completed=True)
        if self.recorder is not None:
            self.recorder.write('stops', event)
        reason = event['reason']
        if self.stops[reason]['trigger']['type'] == 'operating_time':
            self.remaining[reason] = sample(self.stops[reason]['trigger'], self.rng, positive=True)

    def recover_parallel(self, reason, event):
        yield self.env.timeout(event['planned_duration'])
        self.finish_event(event)
        del self.parallel_events[reason]
        self.save()

    def repair(self, reason):
        # Una categoria già impegnata non genera interventi sovrapposti a sé stessa.
        if reason in self.parallel_events:
            return
        self.accrue()
        stop = self.stops[reason]
        duration = sample(stop['time_to_repair'], self.rng)
        blocks = stop['trigger'].get('blocks_machine', True)
        self.counts[reason] += 1
        self.remaining.pop(reason, None)
        event = dict(machine=self.name, reason=reason, trigger=stop['trigger']['type'],
                     blocks_machine=blocks, start=self.env.now, end=None,
                     planned_duration=duration, elapsed_duration=0.0, completed=False)
        self.events.append(event)
        if not blocks:
            self.parallel_events[reason] = event
            self.save()
            self.env.process(self.recover_parallel(reason, event))
            return
        self.current_event = event
        self.set_state('stopped', reason)
        yield self.env.timeout(duration)
        self.finish_event(event)
        self.current_event = None
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
            cycle_start = self.env.now
            # Ciascun fermo probabilistico è indipendente e può scattare una volta per ciclo.
            per_cycle = {
                reason: self.rng.uniform(0, self.takt)
                for reason, stop in self.stops.items()
                if stop['trigger']['type'] == 'per_cycle' and reason not in self.parallel_events
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
                parallel_ends = [max(0.0, e['start'] + e['planned_duration'] - self.env.now)
                                 for e in self.parallel_events.values()]
                timed_at_start = list(self.remaining)
                elapsed = min([work_left, *deadlines.values(), *parallel_ends])
                yield self.env.timeout(elapsed)
                self.accrue()
                work_left = max(0.0, work_left - elapsed)
                for reason in timed_at_start:
                    if reason in self.remaining:
                        self.remaining[reason] = max(0.0, self.remaining[reason] - elapsed)
                for reason in per_cycle:
                    per_cycle[reason] = max(0.0, per_cycle[reason] - elapsed)
            self.processing_time = self.takt
            self.actual_cycle_time = self.env.now - cycle_start
            if self.outlet is not None:
                self.set_state('stand-by')
                yield self.outlet.buff.put(1)
                self.outlet.save()
            self.counter += 1
            if self.previous_completion is not None:
                self.time_between_completions = self.env.now - self.previous_completion
            self.previous_completion = self.env.now
            self.set_state('running')
            for reason, stop in self.stops.items():
                trigger = stop['trigger']
                if trigger['type'] == 'cycle_count' and self.counter % trigger['every'] == 0:
                    yield from self.repair(reason)
