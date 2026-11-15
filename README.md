# Simulazione Ford Scorpion

Conversione in Python del notebook `ford-scorpion-process-simulation.ipynb`.
Richiede Python 3.10 o successivo; non richiede Jupyter o Kaggle.

## Avvio

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python ford_scorpion_process_simulation.py --hours 24 --seed 42
```

Su Windows attivare l'ambiente con `.venv\Scripts\activate`.
Senza `--hours` la simulazione dura 8736 ore (52 settimane), come nel notebook.
I risultati vengono scritti in `results/`: `machines.csv`, `buffers.csv` e cinque
immagini PNG. Usare `--output-dir percorso` per cambiare cartella oppure
`--no-plots` per esportare soltanto i CSV. I grafici vengono salvati anche su
sistemi senza interfaccia grafica. Una simulazione annuale registra ogni ciclo
e ogni movimento dei buffer e può richiedere memoria e spazio considerevoli.

## Modello e conversione

Sono conservati le 12 macchine, i 6 buffer, i tempi ciclo, le capacità e i
parametri MTBF/MTTR della linea originale. I tempi interni sono in ore;
`adjust_cycle_time` converte i minuti secondo la formula del notebook.

Il notebook mescolava due versioni incompatibili: la configurazione e i grafici
usavano MTBF/MTTR, mentre la classe attiva richiedeva dizionari di probabilità e
fermi per categoria. Lo script usa `Machine`, recuperata dalla versione
MTBF/MTTR commentata nel notebook, per eseguire la configurazione esistente.
`CategoryMachine` conserva il modello alternativo per utilizzi futuri; non è
collegata alla linea e richiede parametri e analisi specifici per categoria.
Non sono state inventate probabilità per convertire i parametri MTBF.

È stato corretto il calcolo del ciclo residuo dopo guasti ripetuti nello
stesso ciclo: il tempo trascorso si misura dall'ultima ripresa.
Sono rimossi il setup Kaggle, gli import inutilizzati e l'installazione pip
all'interno del codice. L'importazione del modulo non avvia simulazioni.

I CSV e i grafici mantengono la semantica dello storico originale: i tempi
accumulati registrano cicli/riparazioni completati e non includono la frazione
ancora in corso al termine della simulazione. TTF e TTR sono campioni dello
storico per ciclo, inclusi i valori iniziali, non un registro di soli guasti.
I livelli dei buffer sono campionati ai movimenti, non pesati per durata.

## Uso come modulo

```python
from ford_scorpion_process_simulation import run_simulation

machines, buffers = run_simulation(hours=24, seed=42)
```

## Verifica

```bash
python -m unittest -v
```

I controlli coprono riproducibilità, flusso dei pezzi, capacità dei buffer,
guasti ripetuti nello stesso ciclo, modello per categorie e durata non valida.
