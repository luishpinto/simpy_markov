"""Caricamento e validazione delle configurazioni di processo."""
from importlib.resources import files
import json
from pathlib import Path

from .distributions import number, validate_distribution
from .markdown_config import parse_markdown

def load_config(path=None):
    """Legge un input; senza percorso usa la linea inclusa nel pacchetto."""
    if path is None:
        return parse_markdown(files('simpy_markov').joinpath('data', 'line_config.md').read_text(encoding='utf-8'))
    path = Path(path)
    if path.suffix.lower() == '.md':
        return parse_markdown(path.read_text(encoding='utf-8'))
    if path.suffix.lower() == '.json':
        with path.open(encoding='utf-8') as stream:
            return json.load(stream)
    raise ValueError('Formato input supportato: .md oppure .json')


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
