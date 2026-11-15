"""Grafici degli storici campionati e dei totali finali."""
from pathlib import Path

def save_plots(machines, buffers, events, output_dir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    last = machines.groupby('name', sort=False).last()
    charts = [('running', 'Operating time [h]', 'running_time.png'),
              ('failed_time', 'Downtime [h]', 'downtime.png'),
              ('stops', 'Stops', 'stop_count.png')]
    for column, ylabel, filename in charts:
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.bar(last.index, last[column])
        ax.set_ylabel(ylabel)
        ax.tick_params(axis='x', rotation=45)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 3))
    cycles = machines[machines.takt > 0].groupby('name', sort=False)
    groups = list(cycles)
    if groups:
        ax.boxplot([g.takt.to_numpy() * 60 for _, g in groups], showfliers=False)
        ax.set_xticks(range(1, len(groups) + 1), [name for name, _ in groups], rotation=45)
    ax.set_ylabel('Cycle time [min] (sampled state history)')
    fig.tight_layout()
    fig.savefig(output_dir / 'cycle_time.png', dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 3))
    for name, group in buffers.groupby('name', sort=False):
        ax.step(group.time, group.level, where='post', label=name)
    if not buffers.empty:
        ax.legend()
    ax.set(xlabel='Time [h]', ylabel='Buffer level [units] (sampled history)')
    fig.tight_layout()
    fig.savefig(output_dir / 'buffer_level.png', dpi=150)
    plt.close(fig)
