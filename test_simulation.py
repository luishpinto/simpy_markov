"""Controlli di regressione per la conversione del notebook."""
import unittest

import pandas as pd
import simpy

from ford_scorpion_process_simulation import CategoryMachine, Machine, run_simulation


class SimulationTests(unittest.TestCase):
    def test_reproducibility_and_line_constraints(self):
        machines, buffers = run_simulation(hours=24, seed=42)
        other_machines, other_buffers = run_simulation(hours=24, seed=42)
        pd.testing.assert_frame_equal(machines, other_machines)
        pd.testing.assert_frame_equal(buffers, other_buffers)
        self.assertEqual(machines.name.nunique(), 12)
        self.assertEqual(buffers.name.nunique(), 6)
        self.assertTrue((buffers.level >= 0).all())
        self.assertTrue((buffers.level <= buffers.capacity).all())
        for _, group in machines.groupby('name'):
            self.assertTrue(group.counter.is_monotonic_increasing)
            self.assertTrue((group.running <= group.time + 1e-9).all())
        # Ogni macchina inizialmente vuota può trattenere al massimo un pezzo.
        counters = machines.groupby('name').counter.last()
        stages = [('CU-115', 'CU-075'), ('CU-201', 'CU-192'),
                  ('CU-133', 'CU-119'), ('FR-160',), ('CU-120', 'CU-121'),
                  ('CU-134', 'CU-135'), ('FR-113',)]
        final_levels = buffers.groupby('name', sort=False)['level'].last().tolist()
        for i, (upstream, downstream) in enumerate(zip(stages, stages[1:])):
            in_progress = sum(counters[n] for n in upstream) - final_levels[i] - sum(counters[n] for n in downstream)
            self.assertGreaterEqual(in_progress, 0)
            self.assertLessEqual(in_progress, len(downstream))

    def test_repeated_interruptions_preserve_remaining_cycle(self):
        class ScheduledMachine(Machine):
            def ftcy(self):
                return 10.0

            def fttr(self):
                return 1.0

            def failure(self):
                yield self.env.timeout(2)
                self.action.interrupt()
                yield self.env.timeout(3)
                self.action.interrupt()

        env = simpy.Environment()
        machine = ScheduledMachine(env, 'test', (10, 0), 200, 1, None, None)
        env.run(until=12.01)
        self.assertEqual(machine.counter, 1)
        self.assertEqual(machine.failures, 2)
        self.assertEqual(machine.running, 10)
        self.assertEqual(machine.stat[-1][1], 12)

    def test_category_model(self):
        env = simpy.Environment()
        machine = CategoryMachine(env, 'test', (1, 0),
                                  {'repair': (100, 0)}, {'repair': (2, 0)})
        env.run(until=3.01)
        self.assertEqual(machine.counter, 1)
        self.assertEqual(machine.failures_by_category['repair'], 1)
        self.assertEqual(machine.downtime_by_category['repair'], 2)
        self.assertAlmostEqual(machine.running, 1)

    def test_invalid_duration(self):
        for hours in (0, -1, float('nan'), float('inf')):
            with self.subTest(hours=hours), self.assertRaises(ValueError):
                run_simulation(hours=hours)


if __name__ == '__main__':
    unittest.main()
