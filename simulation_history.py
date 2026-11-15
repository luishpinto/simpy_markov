"""Storici a memoria limitata e scrittura incrementale dei CSV completi."""
import csv
from contextlib import ExitStack
from pathlib import Path


class History:
    """Dirada uniformemente i campioni, preservando primo e ultimo record.

    Non usa il generatore casuale del modello. Il limite riguarda ciascuna
    serie (macchina, buffer o registro fermi), non i CSV scritti su disco.
    """

    def __init__(self, limit=2000, write=None):
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 2):
            raise ValueError('history_limit deve essere un intero >= 2 oppure None')
        self.limit, self.write = limit, write
        self.rows, self.last = [], None
        self.total, self.stride = 0, 1

    def append(self, row):
        if self.write is not None:
            self.write(row)
        index = self.total
        self.total += 1
        self.last = row
        if index % self.stride == 0:
            self.rows.append(row)
            if self.limit is not None and len(self.rows) >= self.limit:
                self.rows = self.rows[::2]
                self.stride *= 2

    def records(self):
        if self.last is not None and (not self.rows or self.rows[-1] is not self.last):
            return [*self.rows, self.last]
        return list(self.rows)

    @property
    def sampled(self):
        return self.total > len(self.records())


class CsvRecorder:
    """Una riga alla volta: nessuna ricostruzione del CSV a fine simulazione."""

    def __init__(self, output_dir, machine_fields, event_fields):
        self.output_dir = Path(output_dir)
        self.fields = {
            'machines': machine_fields,
            'buffers': ['name', 'time', 'level', 'capacity'],
            'stops': event_fields,
        }
        self.stack = ExitStack()
        self.writers = {}

    def __enter__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            for name, fields in self.fields.items():
                stream = self.stack.enter_context((self.output_dir / f'{name}.csv').open(
                    'w', encoding='utf-8', newline=''))
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                self.writers[name] = writer
        except BaseException:
            self.stack.close()
            raise
        return self

    def write(self, name, row):
        self.writers[name].writerow(row)

    def __exit__(self, *args):
        return self.stack.__exit__(*args)
