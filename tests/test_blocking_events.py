"""Eventi bloccanti/paralleli e tempi ciclo osservati."""
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from simpy_markov import run_simulation, validate_line
from simpy_markov.markdown_config import parse_markdown
from tests.test_simulation import fixed, line, stop


def configured(trigger, duration, blocks):
    return stop(dict(trigger, blocks_machine=blocks), duration)


def run(config, hours, **kwargs):
    return run_simulation(hours, 42, config, True, history_limit=None, **kwargs)


class BlockingEventTests(unittest.TestCase):
    def test_blocking_maintenance_extends_actual_cycle(self):
        config = line({'maintenance': configured(dict(type='operating_time', **fixed(12/60)), 10/60, True)}, cycle=18/60)
        machines, _, events = run(config, 28.01/60)
        row = machines.iloc[-1]
        self.assertEqual(row.counter, 1)
        self.assertAlmostEqual(row.processing_time * 60, 18)
        self.assertAlmostEqual(row.actual_cycle_time * 60, 28)
        self.assertAlmostEqual(row.failed_time * 60, 10)
        self.assertTrue(events.blocks_machine.all())

    def test_parallel_time_trigger_rearms_without_shortening_interval(self):
        config = line({'custom': configured(dict(type='operating_time', **fixed(2)), 3, False)}, cycle=10)
        machines, _, events = run(config, 10.01)
        self.assertEqual(events.start.tolist(), [2, 7])
        self.assertEqual(events.end.tolist(), [5, 10])
        row = machines.iloc[-1]
        self.assertEqual(row.counter, 1)
        self.assertAlmostEqual(row.actual_cycle_time, 10)
        self.assertAlmostEqual(row.failed_time, 0)
        self.assertAlmostEqual(row['downtime:custom'], 0)
        self.assertAlmostEqual(row['event_time:custom'], 6)

    def test_parallel_event_continues_during_blocking_maintenance(self):
        config = line({'tool': configured(dict(type='cycle_count', every=2), 20, False),
                       'maintenance': configured(dict(type='operating_time', **fixed(8)), 3, True)})
        machines, _, events = run(config, 12.1)
        row = machines.iloc[-1]
        self.assertEqual(row['stop_count:tool'], 1)
        self.assertAlmostEqual(row['event_time:tool'], 10.1)
        self.assertAlmostEqual(row['downtime:tool'], 0)
        self.assertAlmostEqual(row.failed_time, 3)
        self.assertAlmostEqual(row.running + row.standby + row.failed_time, 12.1)
        after_stop = machines[machines.counter == 8].iloc[0]
        self.assertAlmostEqual(after_stop.actual_cycle_time, 4)
        self.assertAlmostEqual(after_stop.time_between_completions, 4)
        self.assertFalse(events.iloc[0].completed)

    def test_parallel_event_finishes_while_output_is_blocked(self):
        config = line({'tool': configured(dict(type='cycle_count', every=1), 2, False)})
        config['buffers'] = [dict(name='out', init=0, capacity=1)]
        config['machines'][0]['outlet'] = 'out'
        machines, _, events = run(config, 5)
        row = machines.iloc[-1]
        self.assertEqual(row.counter, 1)
        self.assertEqual(row.running, 2)
        self.assertEqual(row.standby, 3)
        self.assertEqual(events.iloc[0].end, 3)
        self.assertTrue(events.iloc[0].completed)

    def test_partial_parallel_events_are_written_once_to_csv(self):
        config = line({name: configured(dict(type='cycle_count', every=1), 10, False)
                       for name in ['tool_change', 'quality_control']})
        with tempfile.TemporaryDirectory() as folder:
            machines, _, events = run(config, 2, csv_dir=folder)
            csv = pd.read_csv(Path(folder) / 'stops.csv')
            self.assertEqual(len(csv), 2)
            self.assertTrue((csv.elapsed_duration == 1).all())
            self.assertFalse(csv.completed.any())
            self.assertFalse(csv.blocks_machine.any())
            self.assertEqual(machines.iloc[-1].failed_time, 0)
            self.assertEqual(len(events), 2)

    def test_probability_trigger_does_not_duplicate_active_category(self):
        config = line({'quality_control': configured(dict(type='per_cycle', probability=1), 10, False)})
        machines, _, events = run(config, 3.1)
        self.assertEqual(len(events), 1)
        self.assertEqual(machines.iloc[-1].counter, 3)
        self.assertAlmostEqual(machines.iloc[-1].actual_cycle_time, 1)
        self.assertEqual(machines.iloc[-1].failed_time, 0)

    def test_zero_duration_parallel_event_and_cycle_count_block(self):
        config = line({'tool': configured(dict(type='cycle_count', every=1), 0, False)})
        machines, _, events = run(config, 5.1)
        self.assertEqual(machines.iloc[-1].counter, 5)
        self.assertEqual(len(events), 5)
        self.assertTrue(events.completed.all())
        config['machines'][0]['stops']['tool'] = configured(dict(type='cycle_count', every=1), 2, True)
        machines, _, _ = run(config, 4.1)
        row = machines[machines.counter == 2].iloc[0]
        self.assertEqual(row.actual_cycle_time, 1)
        self.assertEqual(row.time_between_completions, 3)

    def test_markdown_and_legacy_defaults(self):
        path = Path(__file__).resolve().parents[1] / 'examples' / 'example_config.md'
        text = path.read_text()
        config = parse_markdown(text)
        self.assertTrue(config['machines'][0]['stops']['maintenance']['trigger']['blocks_machine'])
        self.assertFalse(config['machines'][0]['stops']['tool_change']['trigger']['blocks_machine'])
        # Vecchia tabella senza l'ultima colonna.
        old = '\n'.join('|' + '|'.join(line.split('|')[1:-2]) + '|'
                        if line.startswith('|') and len(line.split('|')) == 13 else line
                        for line in text.splitlines())
        legacy = parse_markdown(old)
        validate_line(legacy)
        self.assertNotIn('blocks_machine', legacy['machines'][0]['stops']['tool_change']['trigger'])
        for invalid in (text.replace('| false |', '| yes |', 1),
                        text.replace('| minutes | - | - | - |', '| minutes | - | - | true |', 1)):
            with self.assertRaises(ValueError):
                parse_markdown(invalid)
        legacy['machines'][0]['stops']['maintenance']['trigger']['blocks_machine'] = 'false'
        with self.assertRaises(ValueError):
            validate_line(legacy)

    def test_progress_does_not_change_parallel_timing(self):
        config = line({'tool': configured(dict(type='operating_time', **fixed(2)), 3, False)}, cycle=10)
        for a, b in zip(run(config, 20), run(config, 20, progress=lambda current, total: None)):
            pd.testing.assert_frame_equal(a, b)


if __name__ == '__main__':
    unittest.main()
