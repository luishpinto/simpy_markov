"""Controlli del pacchetto installato, fuori dalla directory del repository."""
from importlib.resources import files
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from simpy_markov import load_config, validate_line


class PackageTests(unittest.TestCase):
    def test_bundled_examples_match_editable_examples(self):
        root = Path(__file__).resolve().parents[1] / 'examples'
        for name in ('line_config.md', 'example_config.md'):
            self.assertEqual(files('simpy_markov').joinpath('data', name).read_text(encoding='utf-8'),
                             (root / name).read_text(encoding='utf-8'))
        default = load_config()
        validate_line(default)
        self.assertEqual(len(default['machines']), 12)

    def test_import_and_run_from_unrelated_directory(self):
        code = '''
from importlib.metadata import version
import sys
import simpy_markov
assert simpy_markov.__version__ == version('simpy-markov') == '0.2.0'
assert 'matplotlib.pyplot' not in sys.modules
machines, buffers = simpy_markov.run_simulation(hours=1, seed=42)
assert machines.name.nunique() == 12
assert buffers.name.nunique() == 6
'''
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, '-I', '-c', code], cwd=folder,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_module_and_console_command_from_unrelated_directory(self):
        scripts = Path(sys.executable).parent
        console = scripts / ('simpy-markov.exe' if sys.platform == 'win32' else 'simpy-markov')
        self.assertTrue(console.is_file())
        with tempfile.TemporaryDirectory() as folder:
            for command in ([sys.executable, '-I', '-m', 'simpy_markov'], [str(console)]):
                result = subprocess.run(command + ['--version'], cwd=folder, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('0.2.0', result.stdout)
            result = subprocess.run([str(console), '--hours', '1', '--no-plots', '--quiet'],
                                    cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({p.name for p in (Path(folder) / 'results').iterdir()},
                             {'machines.csv', 'buffers.csv', 'stops.csv'})


if __name__ == '__main__':
    unittest.main()
