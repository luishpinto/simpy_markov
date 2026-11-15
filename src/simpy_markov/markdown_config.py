"""Lettura del formato Markdown tabellare delle configurazioni di processo."""
import re


PARAM_COLUMNS = {'name', 'parameter', 'type', 'distribution', 'mean', 'std',
                 'value', 'unit', 'probability', 'every', 'blocks_machine'}


def parse_markdown(text):
    """Legge esclusivamente titoli e tabelle, senza eseguire contenuti Markdown."""
    config = {'buffers': [], 'machines': [], 'output': {}}
    section = subsection = None
    machine = None
    table_headers = None
    need_separator = False
    seen_sections = set()
    seen_tables = set()
    definitions = set()

    def fail(line, message):
        raise ValueError(f'Markdown, riga {line}: {message}')

    def numeric(value, key, line):
        try:
            if key == 'every':
                return int(value)
            result = float(value)
            if key in ('init', 'capacity') and result.is_integer():
                return int(result)
            return result
        except ValueError:
            fail(line, f'{key}: numero non valido {value!r}')

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            table_headers = None
            continue
        heading = re.fullmatch(r'(#{1,4})\s+(.+)', line)
        if heading:
            if need_separator:
                fail(lineno, 'manca il separatore della tabella')
            table_headers = None
            level, title = len(heading[1]), heading[2].strip()
            if level == 1:
                if 'title' in config or seen_sections:
                    fail(lineno, 'titolo duplicato o fuori posizione')
                config['title'] = title
            elif level == 2:
                if 'title' not in config:
                    fail(lineno, 'manca il titolo del progetto')
                if title not in ('Buffer', 'Machine', 'Output') or title in seen_sections:
                    fail(lineno, 'sezione sconosciuta o duplicata')
                seen_sections.add(title)
                section, subsection, machine = title, None, None
            elif level == 3 and section == 'Machine':
                machine = {'name': title, 'stops': {}}
                config['machines'].append(machine)
                subsection = None
            elif level == 4 and machine is not None and title in ('Connections', 'Parameters'):
                subsection = title
            else:
                fail(lineno, 'sottosezione non valida')
            continue
        if not line.startswith('|') or not line.endswith('|'):
            fail(lineno, 'attesi un titolo o una riga di tabella delimitata da |')
        cells = [value.strip() for value in line[1:-1].split('|')]
        if table_headers is None:
            if need_separator:
                fail(lineno, 'manca il separatore della tabella')
            if section == 'Buffer':
                expected = {'name', 'init', 'capacity'}
            elif section == 'Output':
                expected = {'parameter', 'value'}
            elif machine is not None and subsection == 'Connections':
                expected = {'inlet', 'outlet'}
            elif machine is not None and subsection == 'Parameters':
                expected = PARAM_COLUMNS
            else:
                fail(lineno, 'tabella fuori da una sezione valida')
            valid_columns = [expected]
            if section == 'Machine' and subsection == 'Parameters':
                valid_columns.append(expected - {'blocks_machine'})
            if len(cells) != len(set(cells)) or set(cells) not in valid_columns:
                fail(lineno, f'colonne richieste: {", ".join(sorted(expected))}')
            table_key = (section, machine['name'] if machine else None, subsection)
            if table_key in seen_tables:
                fail(lineno, 'tabella duplicata')
            seen_tables.add(table_key)
            table_headers, need_separator = cells, True
            continue
        if len(cells) != len(table_headers):
            fail(lineno, 'numero di celle diverso dalle intestazioni')
        if need_separator:
            if not all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells):
                fail(lineno, 'separatore della tabella non valido')
            need_separator = False
            continue
        row = dict(zip(table_headers, cells))
        if section == 'Buffer':
            config['buffers'].append({'name': row['name'],
                'init': numeric(row['init'], 'init', lineno),
                'capacity': numeric(row['capacity'], 'capacity', lineno)})
        elif section == 'Output':
            key, value = row['parameter'], row['value']
            if key not in ('output_dir', 'csv', 'plots') or key in config['output']:
                fail(lineno, 'parametro output sconosciuto o duplicato')
            if key in ('csv', 'plots'):
                if value not in ('true', 'false'):
                    fail(lineno, 'usare true oppure false')
                value = value == 'true'
            elif not value:
                fail(lineno, 'output_dir vuoto')
            config['output'][key] = value
        elif subsection == 'Connections':
            if 'inlet' in machine:
                fail(lineno, 'serve una sola riga di collegamenti')
            machine.update({k: None if v in ('', '-', 'null') else v for k, v in row.items()})
        else:
            name, parameter = row['name'], row['parameter']
            key = (machine['name'], name, parameter)
            if key in definitions:
                fail(lineno, 'parametro duplicato')
            definitions.add(key)
            values = {k: numeric(v, k, lineno) if k in ('mean', 'std', 'value', 'probability', 'every') else v
                      for k, v in row.items() if k not in ('name', 'parameter') and v not in ('', '-')}
            if 'blocks_machine' in values:
                if parameter != 'trigger' or values['blocks_machine'] not in ('true', 'false'):
                    fail(lineno, 'blocks_machine: usare true/false soltanto nella riga trigger')
                values['blocks_machine'] = values['blocks_machine'] == 'true'
            if parameter == 'cycle_time' and name == '-':
                if 'cycle_time' in machine:
                    fail(lineno, 'cycle_time duplicato')
                machine['cycle_time'] = values
            elif parameter in ('trigger', 'time_to_repair') and name not in ('', '-'):
                machine['stops'].setdefault(name, {})[parameter] = values
            else:
                fail(lineno, 'usare cycle_time con name=-, oppure trigger/time_to_repair con nome del fermo')
    if need_separator:
        fail(len(text.splitlines()), 'manca il separatore della tabella')
    if 'title' not in config or seen_sections != {'Buffer', 'Machine', 'Output'}:
        raise ValueError('Markdown: richiesti titolo e sezioni Buffer, Machine, Output')
    for m in config['machines']:
        for subsection in ('Connections', 'Parameters'):
            if ('Machine', m['name'], subsection) not in seen_tables:
                raise ValueError(f"Markdown: manca {subsection} per {m['name']}")
        if 'inlet' not in m:
            raise ValueError(f"Markdown: mancano i collegamenti per {m['name']}")
    for section in ('Buffer', 'Output'):
        if (section, None, None) not in seen_tables:
            raise ValueError(f'Markdown: manca la tabella {section}')
    return config
