"""Verifiche del documento Markdown e delle opzioni di esportazione."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pandas as pd

from markdown_config import parse_markdown
from process_simulation import load_config, run_simulation

ROOT = Path(__file__).resolve().parent


class MarkdownTests(unittest.TestCase):
    def test_markdown_loads_and_matches_direct_config(self):
        for stem in ('line_config', 'example_config'):
            with self.subTest(stem=stem):
                md = load_config(ROOT / f'{stem}.md')
                direct = parse_markdown((ROOT / f'{stem}.md').read_text())
                self.assertEqual(md, direct)
                self.assertTrue(md['title'])
                self.assertEqual(md['output'], dict(output_dir='results', csv=True, plots=True))
                for a, b in zip(run_simulation(24, 42, md, True), run_simulation(24, 42, direct, True)):
                    pd.testing.assert_frame_equal(a, b)

    def test_invalid_documents_are_rejected(self):
        text = (ROOT / 'example_config.md').read_text()
        invalid = [text.replace('# Esempio: fermi configurabili', '', 1),
                   text.replace('## Output', '## Unknown'),
                   text.replace('| inlet | outlet |', '| inlet | unknown |'),
                   text.replace('| csv | true |', '| csv | yes |'),
                   text.replace('| output_dir | results |', '| unknown | results |'),
                   text.replace('#### Connections', '#### Unknown'),
                   text.replace('| mean |', '| unknown |'),
                   text + '\n## Output\n',
                   text.replace('| cycle_count |', '| cycle_count | extra |', 1)]
        for doc in invalid:
            with self.subTest(doc=doc[-60:]), self.assertRaises(ValueError):
                parse_markdown(doc)

    def test_cli_output_definition_and_override(self):
        text = (ROOT / 'example_config.md').read_text()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = root / 'project.md'
            config.write_text(text.replace('| plots | true |', '| plots | false |')
                              .replace('| output_dir | results |', '| output_dir | configured |'))
            command = [sys.executable, str(ROOT / 'process_simulation.py'), '--config', str(config),
                       '--hours', '1', '--seed', '42']
            result = subprocess.run(command, cwd=root, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Esempio: fermi configurabili', result.stdout)
            self.assertEqual({p.name for p in (root / 'configured').iterdir()},
                             {'machines.csv', 'buffers.csv', 'stops.csv'})
            config.write_text(text.replace('| csv | true |', '| csv | false |'))
            result = subprocess.run(command + ['--output-dir', str(root / 'override'), '--no-plots'],
                                    cwd=root, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list((root / 'override').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
