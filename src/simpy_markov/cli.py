"""Simulazione di processi con fermi configurabili; tempi interni in ore."""
import argparse
from pathlib import Path

from . import __version__
from .config import load_config, validate_line
from .simulation import run_simulation
from .plotting import save_plots

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.add_argument('--config', type=Path, default=None, help='Input .md; senza percorso usa la linea inclusa')
    duration = parser.add_mutually_exclusive_group()
    duration.add_argument('--hours', type=float, default=None)
    duration.add_argument('--weeks', type=float, help='Durata in settimane da 168 ore')
    parser.add_argument('--history-limit', type=int, default=2000,
                        help='Massimo di campioni in RAM per serie (default: 2000)')
    parser.add_argument('--quiet', action='store_true', help='Nasconde avanzamento')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--output-dir', type=Path, help='Sovrascrive output_dir del documento')
    parser.add_argument('--no-plots', action='store_true')
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        output = config.get('output', {})
        validate_line(config)
        output_dir = args.output_dir or Path(output.get('output_dir', 'results'))
        hours = args.weeks * 168 if args.weeks is not None else (args.hours if args.hours is not None else 8736.0)
        def report(current, total):
            print(f'Avanzamento: {current / total:.0%} ({current / 168:.1f} settimane)', flush=True)
        machines, buffers, events = run_simulation(
            hours, args.seed, config, return_events=True, history_limit=args.history_limit,
            csv_dir=output_dir if output.get('csv', True) else None,
            progress=None if args.quiet else report)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    output = config.get('output', {})
    output_dir = args.output_dir or Path(output.get('output_dir', 'results'))
    output_dir.mkdir(parents=True, exist_ok=True)
    if output.get('plots', True) and not args.no_plots:
        save_plots(machines, buffers, events, output_dir)
    if config.get('title'):
        print(config['title'])
    print(machines.groupby('name', sort=False)[['counter', 'stops', 'running', 'failed_time']].last())
    if any(frame.attrs.get('history_sampled') for frame in (machines, buffers, events)):
        print('Storici per grafici campionati; contatori e tempi finali completi.')
    if output.get('csv', True):
        print('CSV completi scritti progressivamente su disco.')
    print(f'Risultati salvati in {output_dir.resolve()}')
