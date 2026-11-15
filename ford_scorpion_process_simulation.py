"""Simulazione della linea Ford Scorpion, convertita dal notebook originale.

Il modello predefinito usa MTBF/MTTR, come la configurazione della linea.
CategoryMachine conserva il modello alternativo con guasti per categoria.
Tutti i tempi interni sono espressi in ore.
"""

import argparse
import math
from pathlib import Path
import random

import numpy as np
import pandas as pd
import simpy

class Buffer:

  def __init__(self, env, name, capacity, init):

    self.env = env
    self.name = name
    self.capacity = capacity
    self.init = init

    self.buff = simpy.Container(self.env, capacity = self.capacity, init = self.init)

    self.stat = []

  def save(self):

    self.stat.append([self.name, self.env.now, self.buff.level, self.capacity])

class Machine:

  def __init__(self, env, name, tcy, mtbf, mttr, inlet, outlet):

    self.env = env
    self.name = name
    self.mu = tcy[0]
    self.sigma = tcy[1]
    self.takt = 0.0
    self.ttf = 0.0
    self.ttr = 0.0
    self.counter = 0
    self.mtbf = mtbf
    self.mttr = mttr

    if (inlet != None):
      self.inlet = inlet
    else:
      self.inlet = None

    if (outlet != None):
      self.outlet = outlet
    else:
      self.outlet = None

    self.status = 'running'
    self.failures = 0
    self.active = 0.0
    self.running = 0.0
    self.stat = []

    self.action = env.process(self.run())
    env.process(self.failure())

  def ftcy(self):

    return random.normalvariate(self.mu, self.sigma)

  def fttf(self):

    return random.expovariate(1 / self.mtbf)

  def fttr(self):

    return random.lognormvariate(0.0, 0.5) * self.mttr

  def save(self):

    self.stat.append([self.name, self.env.now, self.takt,
                      self.running, self.counter, self.ttf,
                      self. ttr, self.failures])

  def run(self):

    self.save()

    while True:

      self.takt = np.maximum(self.ftcy(), 0.0)
      tcy = self.takt

      if self.inlet:
        self.status = 'stand-by'
        yield self.inlet.buff.get(1)
        self.inlet.save()
        self.status = 'running'

      while tcy:
        try:
          ti = self.env.now
          yield self.env.timeout(tcy)
          self.running += self.takt
          tcy = 0.0
        except simpy.Interrupt:
          self.status = 'failure'
          tcy -= self.env.now - ti
          tcy = np.maximum(tcy, 0.0)
          self.ttr = self.fttr()
          yield self.env.timeout(self.ttr)
          self.failures += 1
          self.status = 'running'

      if self.outlet:
        self.status = 'stand-by'
        yield self.outlet.buff.put(1)
        self.outlet.save()
        self.status = 'running'

      self.counter += 1
      self.save()

  def failure(self):
    while True:
      self.ttf = self.fttf()
      yield self.env.timeout(self.ttf)
      if (self.status == 'running'):
        self.action.interrupt()

class CategoryMachine:

    def __init__(
        self,
        env,
        name,
        tcy,
        failures_pct,
        downtime,
        inlet=None,
        outlet=None
    ):
        """
        Parameters
        ----------
        env : simpy.Environment
            Ambiente della simulazione.

        name : str
            Nome della macchina.

        tcy : tuple
            Tempo ciclo:
            (media, deviazione_standard)

            Esempio:
            tcy=(60.0, 3.0)

        failures_pct : dict
            Probabilità percentuale di guasto per ciclo e relativa
            deviazione standard.

            Esempio:
            {
                "manutenzione": (2.0, 0.20),
                "produzione":   (1.5, 0.15),
                "qualita":      (0.8, 0.10),
                "utensile":     (1.2, 0.15),
                "ingegneria":   (0.5, 0.05)
            }

        downtime : dict
            Durata media e deviazione standard del fermo per categoria.

            Esempio:
            {
                "manutenzione": (30.0, 5.0),
                "produzione":   (10.0, 2.0),
                "qualita":      (15.0, 3.0),
                "utensile":     (20.0, 4.0),
                "ingegneria":   (25.0, 5.0)
            }

        inlet : object, optional
            Buffer di ingresso.

        outlet : object, optional
            Buffer di uscita.
        """

        self.env = env
        self.name = name

        # Tempo ciclo
        self.cycle_time_mean = tcy[0]
        self.cycle_time_std = tcy[1]

        # Probabilità di guasto per ciclo
        self.failures_pct = failures_pct

        # Durata del fermo per categoria
        self.downtime_parameters = downtime

        self.inlet = inlet
        self.outlet = outlet

        self.status = "running"
        self.failure_category = None

        self.takt = 0.0
        self.counter = 0

        # Tempi accumulati
        self.running = 0.0
        self.standby = 0.0
        self.failed_time = 0.0

        # Totale guasti
        self.failures = 0

        # Guasti per categoria
        self.failures_by_category = {
            category: 0
            for category in self.failures_pct
        }

        # Downtime per categoria
        self.downtime_by_category = {
            category: 0.0
            for category in self.failures_pct
        }

        # Storico della simulazione
        self.stat = []

        # Avvio della macchina
        self.action = env.process(self.run())

    def sample_cycle_time(self):
        """
        Genera il tempo ciclo applicando una distribuzione normale.
        Il valore non può essere negativo.
        """

        cycle_time = random.gauss(
            self.cycle_time_mean,
            self.cycle_time_std
        )

        return max(cycle_time, 0.0)

    def sample_failure_probabilities(self):
        """
        Applica variabilità alle percentuali nominali di guasto.

        Ogni percentuale viene campionata con una distribuzione normale
        e limitata tra 0% e 100%.

        La somma totale viene inoltre limitata al 100%.
        """

        probabilities = {}

        for category, parameters in self.failures_pct.items():

            mean_pct = parameters[0]
            std_pct = parameters[1]

            sampled_pct = random.gauss(
                mean_pct,
                std_pct
            )

            sampled_pct = max(0.0, min(sampled_pct, 100.0))

            probabilities[category] = sampled_pct

        total_probability = sum(probabilities.values())

        if total_probability > 100.0:

            correction_factor = 100.0 / total_probability

            probabilities = {
                category: probability * correction_factor
                for category, probability in probabilities.items()
            }

        return probabilities

    def select_failure_category(self):
        """
        Determina se si verifica un guasto durante il ciclo.

        Se avviene un guasto, restituisce la relativa categoria.
        Altrimenti restituisce None.
        """

        probabilities = self.sample_failure_probabilities()

        random_value = random.uniform(0.0, 100.0)

        cumulative_probability = 0.0

        for category, probability in probabilities.items():

            cumulative_probability += probability

            if random_value <= cumulative_probability:
                return category

        return None

    def sample_downtime(self, category):
        """
        Genera la durata del fermo per la categoria selezionata.
        """

        mean_time, std_time = self.downtime_parameters[category]

        sampled_time = random.gauss(
            mean_time,
            std_time
        )

        return max(sampled_time, 0.0)

    def save(self):
        """
        Salva lo stato corrente della macchina.
        """

        current_record = {
            "machine": self.name,
            "simulation_time": self.env.now,
            "status": self.status,
            "failure_category": self.failure_category,
            "cycle_time": self.takt,
            "running_time": self.running,
            "standby_time": self.standby,
            "failed_time": self.failed_time,
            "production_counter": self.counter,
            "total_failures": self.failures
        }

        for category in self.failures_by_category:

            current_record[
                f"failures_{category}"
            ] = self.failures_by_category[category]

            current_record[
                f"downtime_{category}"
            ] = self.downtime_by_category[category]

        self.stat.append(current_record)

    def wait_for_inlet(self):
        """
        Attende la disponibilità di materiale nel buffer di ingresso.
        """

        if self.inlet is None:
            return None

        return self.inlet.buff.get(1)

    def send_to_outlet(self):
        """
        Invia il pezzo completato al buffer di uscita.
        """

        if self.outlet is None:
            return None

        return self.outlet.buff.put(1)

    def run(self):

        self.save()

        while True:

            # Attende materiale nel buffer di ingresso
            if self.inlet is not None:

                self.status = "stand-by"
                standby_start = self.env.now

                yield self.wait_for_inlet()

                self.standby += self.env.now - standby_start

                self.inlet.save()

            self.status = "running"
            self.failure_category = None

            # Generazione del tempo ciclo
            self.takt = self.sample_cycle_time()

            # Selezione dell'eventuale guasto
            failure_category = self.select_failure_category()

            if failure_category is None:

                # Ciclo senza guasto
                yield self.env.timeout(self.takt)

                self.running += self.takt

            else:

                # Il guasto avviene in un punto casuale del ciclo
                time_before_failure = random.uniform(
                    0.0,
                    self.takt
                )

                remaining_cycle_time = (
                    self.takt - time_before_failure
                )

                # Produzione fino al guasto
                yield self.env.timeout(time_before_failure)

                self.running += time_before_failure

                # Registrazione del guasto
                self.status = "failure"
                self.failure_category = failure_category

                self.failures += 1

                self.failures_by_category[
                    failure_category
                ] += 1

                repair_time = self.sample_downtime(
                    failure_category
                )

                self.save()

                # Durata del fermo
                yield self.env.timeout(repair_time)

                self.failed_time += repair_time

                self.downtime_by_category[
                    failure_category
                ] += repair_time

                # Ripresa del ciclo
                self.status = "running"
                self.failure_category = None

                yield self.env.timeout(remaining_cycle_time)

                self.running += remaining_cycle_time

            # Invio del pezzo al buffer di uscita
            if self.outlet is not None:

                self.status = "stand-by"
                standby_start = self.env.now

                yield self.send_to_outlet()

                self.standby += self.env.now - standby_start

                self.outlet.save()

            # Pezzo completato
            self.counter += 1

            self.status = "running"
            self.save()

def adjust_cycle_time(tcy, eff):
  return((tcy * eff / 60.0, ((1 - eff) * tcy / 3.0) / 60.0))

def run_simulation(hours=8736.0, seed=None):
    """Esegue la linea originale per il numero di ore richiesto."""
    if not math.isfinite(hours) or hours <= 0:
        raise ValueError("La durata deve essere finita e maggiore di zero.")
    if seed is not None:
        random.seed(seed)
    env = simpy.Environment()

    buff = []

    buff.append(Buffer(env, 'buffer #1', capacity = 8, init = 0))
    buff.append(Buffer(env, 'buffer #2', capacity = 8, init = 0))
    buff.append(Buffer(env, 'buffer #3', capacity = 8, init = 0))
    buff.append(Buffer(env, 'buffer #4', capacity = 8, init = 0))
    buff.append(Buffer(env, 'buffer #5', capacity = 16, init = 0))
    buff.append(Buffer(env, 'buffer #6', capacity = 6, init = 0))

    cnc = []

    cnc.append(Machine(env, 'CU-115', adjust_cycle_time(5.78, 0.72), 200.0, 1.5, None, buff[0]))
    cnc.append(Machine(env, 'CU-075', adjust_cycle_time(5.97, 0.72), 336.0, 0.5, None, buff[0]))

    cnc.append(Machine(env, 'CU-201', adjust_cycle_time(5.48, 0.72), 200.0, 1.5, buff[0], buff[1]))
    cnc.append(Machine(env, 'CU-192', adjust_cycle_time(5.24, 0.72), 200.0, 1.5, buff[0], buff[1]))

    cnc.append(Machine(env, 'CU-133', adjust_cycle_time(5.93, 0.72), 200.0, 0.5, buff[1], buff[2]))
    cnc.append(Machine(env, 'CU-119', adjust_cycle_time(6.06, 0.72), 200.0, 0.5, buff[1], buff[2]))

    cnc.append(Machine(env, 'FR-160', adjust_cycle_time(2.50, 0.72), 224.0, 1.5, buff[2], buff[3]))

    cnc.append(Machine(env, 'CU-120', adjust_cycle_time(6.21, 0.72), 224.0, 1.25, buff[3], buff[4]))
    cnc.append(Machine(env, 'CU-121', adjust_cycle_time(6.04, 0.72), 200.0, 1.25, buff[3], buff[4]))

    cnc.append(Machine(env, 'CU-134', adjust_cycle_time(6.04, 0.72), 200.0, 1.50, buff[4], buff[5]))
    cnc.append(Machine(env, 'CU-135', adjust_cycle_time(6.28, 0.72), 200.0, 1.5, buff[4], buff[5]))

    cnc.append(Machine(env, 'FR-113', adjust_cycle_time(3.01, 0.72), 200.0, 0.5, buff[5], None))

    env.run(until=hours)
    machines = pd.DataFrame(
        [row for item in cnc for row in item.stat],
        columns=['name', 'time', 'takt', 'running', 'counter', 'ttf', 'ttr', 'failures'],
    )
    buffers = pd.DataFrame(
        [row for item in buff for row in item.stat],
        columns=['name', 'time', 'level', 'capacity'],
    )
    return machines, buffers


def save_plots(machines, buffers, output_dir):
    """Salva i cinque grafici del notebook senza richiedere Jupyter."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'mathtext.fontset': 'stix', 'font.family': 'sans-serif', 'font.size': 8})
    machine_groups = list(machines.groupby('name', sort=False))
    for column, factor, title, ylabel, filename in [
        ('takt', 60.0, 'Cycle Time', 'Cycle Time [ min ]', 'cycle_time.png'),
        ('ttf', 1.0, 'Time To Failure', 'TTF [ h ]', 'time_to_failure.png'),
        ('ttr', 1.0, 'Time To Repair', 'TTR [ h ]', 'time_to_repair.png'),
    ]:
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.boxplot([group[column].to_numpy() * factor for _, group in machine_groups],
                   showfliers=False, showmeans=True)
        ax.set_xticks(range(1, len(machine_groups) + 1), [name for name, _ in machine_groups])
        ax.set(title=title, ylabel=ylabel)
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3))
    running = [group.running.max() for _, group in machine_groups]
    labels = [name for name, _ in machine_groups]
    ax.bar(labels, running, color='white', edgecolor='black')
    ax.plot(labels, [max(running)] * len(labels), color='black', linewidth=0.75,
            linestyle='dashed', marker='o', markerfacecolor='white')
    ax.set(title='Running Time', ylabel='Running Time [ h ]')
    fig.tight_layout()
    fig.savefig(output_dir / 'running_time.png', dpi=150)
    plt.close(fig)

    if not buffers.empty:
        groups = list(buffers.groupby('name', sort=False))
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.boxplot([group.level.to_numpy() for _, group in groups],
                   showfliers=False, showmeans=True)
        positions = np.arange(1, len(groups) + 1)
        ax.set_xticks(positions, [name for name, _ in groups])
        ax.step(positions, [group.capacity.max() for _, group in groups], where='mid',
                color='black', linewidth=0.75, linestyle='dashed', marker='o',
                markerfacecolor='white')
        ax.set(title='Buffer Level', ylabel='Buffer Level [ unit ]')
        fig.tight_layout()
        fig.savefig(output_dir / 'buffer_level.png', dpi=150)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hours', type=float, default=8736.0,
                        help='Durata in ore (default: 52 settimane, 8736 ore).')
    parser.add_argument('--seed', type=int, default=None, help='Seed per risultati riproducibili.')
    parser.add_argument('--output-dir', type=Path, default=Path('results'))
    parser.add_argument('--no-plots', action='store_true', help='Esporta soltanto i CSV.')
    args = parser.parse_args()
    if not math.isfinite(args.hours) or args.hours <= 0:
        parser.error('--hours deve essere finito e maggiore di zero')
    machines, buffers = run_simulation(args.hours, args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    machines.to_csv(args.output_dir / 'machines.csv', index=False)
    buffers.to_csv(args.output_dir / 'buffers.csv', index=False)
    if not args.no_plots:
        save_plots(machines, buffers, args.output_dir)
    print(machines.groupby('name', sort=False)[['counter', 'failures', 'running']].last().to_string())
    print(f'Risultati salvati in {args.output_dir.resolve()}')


if __name__ == '__main__':
    main()
