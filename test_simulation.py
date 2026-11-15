"""Regressioni deterministiche sul motore dei fermi configurabili."""
from copy import deepcopy
import random
import unittest

import pandas as pd

from process_simulation import load_config, run_simulation, sample


def fixed(value, unit='hours'):
    return dict(distribution='fixed', value=value, unit=unit)


def stop(trigger, duration=1):
    return dict(trigger=trigger, time_to_repair=fixed(duration))


def line(stops=None, cycle=1):
    return dict(buffers=[], machines=[dict(name='test', cycle_time=fixed(cycle), stops=stops or {})])


def simulate(config, hours):
    return run_simulation(hours, seed=42, config=config, return_events=True)


class SimulationTests(unittest.TestCase):
    def test_default_line_reproducibility_and_capacity(self):
        first = run_simulation(24, 42, return_events=True)
        second = run_simulation(24, 42, return_events=True)
        for a, b in zip(first, second):
            pd.testing.assert_frame_equal(a, b)
        machines, buffers, _ = first
        self.assertEqual(machines.name.nunique(), 12)
        self.assertEqual(buffers.name.nunique(), 6)
        self.assertTrue((buffers.level.between(0, buffers.capacity)).all())
        last = machines.groupby('name').last()
        self.assertTrue(((last.running + last.standby + last.failed_time - 24).abs() < 1e-8).all())

    def test_repeated_operating_stops_resume_same_cycle(self):
        config = line({'maintenance': stop(dict(type='operating_time', **fixed(2)))}, cycle=5)
        machines, _, events = simulate(config, 7.5)
        self.assertEqual(events.start.tolist(), [2, 5])
        self.assertEqual(machines.iloc[-1].counter, 1)
        self.assertAlmostEqual(machines.iloc[-1].running, 5.5)
        self.assertAlmostEqual(machines.iloc[-1].failed_time, 2)

    def test_cycle_count_and_custom_names(self):
        config = line({'tool_change': stop(dict(type='cycle_count', every=2)),
                       'special_tool_change': stop(dict(type='cycle_count', every=4), 3)})
        machines, _, events = simulate(config, 9.5)
        self.assertEqual(events.reason.tolist(), ['tool_change', 'tool_change', 'special_tool_change'])
        self.assertEqual(events.start.tolist(), [2, 5, 6])
        self.assertEqual(machines.iloc[-1]['stop_count:tool_change'], 2)
        self.assertEqual(machines.iloc[-1]['stop_count:special_tool_change'], 1)
        self.assertEqual(machines.iloc[-1].counter, 4)

    def test_simultaneous_time_stops_keep_config_order(self):
        config = line({'second_name': stop(dict(type='operating_time', **fixed(2)), 1),
                       'first_name': stop(dict(type='operating_time', **fixed(2)), 2)}, cycle=10)
        _, _, events = simulate(config, 5.1)
        self.assertEqual(events.reason.tolist(), ['second_name', 'first_name'])
        self.assertEqual(events.start.tolist(), [2, 3])
        self.assertEqual(events.end.tolist(), [3, 5])

    def test_per_cycle_independent_probability(self):
        config = line({'never': stop(dict(type='per_cycle', probability=0)),
                       'always': stop(dict(type='per_cycle', probability=1), 0.5),
                       'also_always': stop(dict(type='per_cycle', probability=1), 0.5)})
        machines, _, events = simulate(config, 2.01)
        self.assertNotIn('never', events.reason.tolist())
        # Il primo pezzo ha avuto entrambi i fermi e termina esattamente a t=2.
        completed = machines[machines.counter == 1].iloc[0]
        self.assertAlmostEqual(completed.time, 2)
        self.assertEqual(completed['stop_count:always'], 1)
        self.assertEqual(completed['stop_count:also_always'], 1)

    def test_mixed_triggers_at_cycle_boundary(self):
        config = line({'timed': stop(dict(type='operating_time', **fixed(2))),
                       'counted': stop(dict(type='cycle_count', every=2))})
        machines, _, events = simulate(config, 4.01)
        self.assertEqual(events.reason.tolist(), ['timed', 'counted'])
        self.assertEqual(events.start.tolist(), [2, 3])
        self.assertEqual(machines.iloc[-1].counter, 2)
        self.assertAlmostEqual(machines.iloc[-1].running, 2.01)

    def test_partial_repair_at_horizon(self):
        config = line({'repair': stop(dict(type='operating_time', **fixed(1)), 5)})
        machines, _, events = simulate(config, 3)
        self.assertAlmostEqual(machines.iloc[-1].failed_time, 2)
        self.assertAlmostEqual(machines.iloc[-1]['downtime:repair'], 2)
        self.assertFalse(events.iloc[0].completed)
        self.assertTrue(pd.isna(events.iloc[0].end))
        self.assertEqual(events.iloc[0].elapsed_duration, 2)

    def test_inlet_wait_does_not_consume_operating_time(self):
        config = line({'repair': stop(dict(type='operating_time', **fixed(2)))})
        config['buffers'] = [dict(name='input', capacity=1, init=0)]
        config['machines'][0]['inlet'] = 'input'
        machines, _, events = simulate(config, 10)
        self.assertTrue(events.empty)
        self.assertEqual(machines.iloc[-1].standby, 10)
        self.assertEqual(machines.iloc[-1].running, 0)

    def test_output_block_does_not_consume_operating_time(self):
        config = line({'repair': stop(dict(type='operating_time', **fixed(2)))})
        config['buffers'] = [dict(name='output', capacity=1, init=1)]
        config['machines'][0]['outlet'] = 'output'
        machines, _, events = simulate(config, 10)
        self.assertTrue(events.empty)
        self.assertEqual(machines.iloc[-1].running, 1)
        self.assertEqual(machines.iloc[-1].standby, 9)

    def test_units_and_lognormal_physical_parameters(self):
        self.assertEqual(sample(fixed(60, 'minutes'), random.Random()), 1)
        rng = random.Random(12)
        spec = dict(distribution='lognormal', mean=2, std=0.5, unit='hours')
        values = pd.Series([sample(spec, rng) for _ in range(20000)])
        self.assertAlmostEqual(values.mean(), 2, delta=0.03)
        self.assertAlmostEqual(values.std(), .5, delta=.03)

    def test_validation(self):
        configs = []
        for trigger in [dict(type='cycle_count', every=0), dict(type='cycle_count', every=1.5),
                        dict(type='per_cycle', probability=1.1), dict(type='unknown'),
                        dict(type='operating_time', **fixed(0))]:
            configs.append(line({'bad': stop(trigger)}))
        c = line(); c['machines'][0]['cycle_time']['unit'] = 'bad'; configs.append(c)
        c = line(); c['machines'][0]['cycle_time'] = fixed(0); configs.append(c)
        c = line(); c['machines'][0]['inlet'] = 'missing'; configs.append(c)
        for config in configs:
            with self.subTest(config=config), self.assertRaises(ValueError):
                simulate(config, 1)
        for hours in [0, -1, float('nan'), float('inf')]:
            with self.assertRaises(ValueError):
                simulate(line(), hours)

    def test_examples_load_and_input_not_mutated(self):
        from pathlib import Path
        config = load_config(Path(__file__).with_name('example_config.md'))
        original = deepcopy(config)
        simulate(config, 24)
        self.assertEqual(config, original)


if __name__ == '__main__':
    unittest.main()
