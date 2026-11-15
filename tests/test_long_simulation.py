"""Controlli su memoria limitata, equivalenza del modello e CSV incrementali."""
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from simpy_markov import run_simulation
from simpy_markov.history import History
from tests.test_simulation import fixed, line, stop


class LongSimulationTests(unittest.TestCase):
    def test_history_bound_preserves_first_and_latest(self):
        for limit in (2, 3, 20, 2000):
            history = History(limit)
            first = {'i': 0}
            history.append(first)
            for i in range(1, 10001):
                history.append({'i': i})
                self.assertLessEqual(len(history.rows), limit)
            rows = history.records()
            self.assertLessEqual(len(rows), limit)
            self.assertIs(rows[0], first)
            self.assertEqual(rows[-1]['i'], 10000)
            self.assertEqual([r['i'] for r in rows], sorted(r['i'] for r in rows))
            self.assertTrue(history.sampled)
            self.assertEqual(history.total, 10001)

    def test_bounded_results_have_identical_totals(self):
        config = line({'timed': stop(dict(type='operating_time', **fixed(2)), .5),
                       'tool': stop(dict(type='cycle_count', every=5), .2),
                       'quality': stop(dict(type='per_cycle', probability=.3), .1)})
        full = run_simulation(100, 42, config, True, history_limit=None)
        limited = run_simulation(100, 42, config, True, history_limit=8)
        pd.testing.assert_frame_equal(full[0].tail(1).reset_index(drop=True),
                                      limited[0].tail(1).reset_index(drop=True))
        self.assertEqual(full[0].attrs['total_records'], limited[0].attrs['total_records'])
        self.assertFalse(full[0].attrs['history_sampled'])
        self.assertTrue(limited[0].attrs['history_sampled'])
        self.assertLessEqual(len(limited[0]), 8)
        self.assertLessEqual(len(limited[2]), 8)

    def test_streamed_csv_keeps_every_row_and_partial_repair(self):
        config = line({'repair': stop(dict(type='operating_time', **fixed(2)), 1)}, cycle=.5)
        config['buffers'] = [dict(name='out', capacity=100, init=0)]
        config['machines'][0]['outlet'] = 'out'
        full = run_simulation(8.5, 42, config, True, history_limit=None)
        with tempfile.TemporaryDirectory() as folder:
            limited = run_simulation(8.5, 42, config, True, history_limit=3, csv_dir=folder)
            for name, expected in zip(('machines', 'buffers', 'stops'), full):
                actual = pd.read_csv(Path(folder) / f'{name}.csv')
                # Uniforma solo l'inferenza dei tipi CSV, senza ignorare record o valori.
                baseline = Path(folder) / 'expected.csv'
                expected.to_csv(baseline, index=False)
                expected = pd.read_csv(baseline)
                keys = ['machine', 'start'] if name == 'stops' else ['name', 'time']
                pd.testing.assert_frame_equal(actual.sort_values(keys, kind='stable').reset_index(drop=True),
                                              expected.sort_values(keys, kind='stable').reset_index(drop=True))
            events = pd.read_csv(Path(folder) / 'stops.csv')
            self.assertFalse(events.iloc[-1].completed)
            self.assertEqual(events.iloc[-1].elapsed_duration, .5)
            self.assertEqual(len(events), limited[2].attrs['total_records'])

    def test_progress_does_not_change_results(self):
        config = line({'quality': stop(dict(type='per_cycle', probability=.4), .5)})
        updates = []
        baseline = run_simulation(10, 42, config, True, history_limit=None)
        progress = run_simulation(10, 42, config, True, history_limit=None,
                                  progress=lambda now, end: updates.append((now, end)))
        for a, b in zip(baseline, progress):
            pd.testing.assert_frame_equal(a, b)
        self.assertEqual(updates[-1], (10, 10))

    def test_invalid_limit_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'results'
            for limit in (0, 1, -1, True, 2.5):
                with self.subTest(limit=limit), self.assertRaises(ValueError):
                    run_simulation(1, 42, line(), history_limit=limit, csv_dir=output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
