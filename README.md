# Simulazione Ford Scorpion

Simulazione Python/SimPy con un unico modello `ProductionMachine`, configurato
tramite Markdown o JSON. Le precedenti classi `Machine` e `CategoryMachine` sono rimosse.
Richiede Python 3.10 o successivo.

## Avvio

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python process_simulation.py --config line_config.md --hours 24 --seed 42
python -m unittest -v
```

Su Windows: `.venv\Scripts\activate`. Senza `--config` si usa `line_config.md`
accanto allo script; senza `--hours` si simulano 8736 ore. Il seed usa un generatore
locale e non modifica lo stato casuale globale. `--output-dir` sceglie la cartella
di esportazione; `--no-plots` disattiva le immagini. Simulazioni lunghe possono
produrre storici voluminosi.

## Documento Markdown di input

Il formato predefinito è `line_config.md`; `example_config.md` contiene tutti i
tipi di fermo. I precedenti `.json` rimangono supportati con `--config`.
Il vecchio file principale è stato rinominato in `process_simulation.py`:
aggiornare eventuali import e comandi che usavano il nome precedente.

Il documento ha un titolo `# Nome progetto` e tre sezioni obbligatorie:

- `## Buffer`: tabella `name`, `init`, `capacity`. Per “taglio” si intende la
  capacità massima; `init` è la quantità iniziale. Sono ammesse tabelle senza
  righe per configurazioni prive di buffer.
- `## Machine`: una sottosezione `### Nome macchina` per ciascuna macchina.
  `#### Connections` contiene una tabella con colonne `inlet`, `outlet` e una
  sola riga. `-`, `null` o una cella vuota indicano collegamenti illimitati.
  `#### Parameters` contiene la tabella dei parametri probabilistici.
- `## Output`: tabella con colonne `parameter`, `value` per `output_dir`,
  `csv` e `plots`. I due flag usano `true`/`false`; i valori predefiniti sono
  `results`, `true`, `true`.

Nella tabella Parameters le colonne sono:
`name`, `parameter`, `type`, `distribution`, `mean`, `std`, `value`, `unit`,
`probability`, `every`. Usare `-` per i campi non applicabili. Le intestazioni
sono fisse, ma l'ordine delle colonne è libero.

La riga del ciclo usa `name=-`, `parameter=cycle_time`. Ogni fermo ha due righe
con lo stesso nome libero: `parameter=trigger` e `parameter=time_to_repair`.
`type` è compilato soltanto per il trigger; gli altri parametri seguono le
regole delle distribuzioni e dei trigger descritte sotto. Nessun contenuto
Markdown viene eseguito come codice. Il formato accetta titoli e tabelle;
testo libero, blocchi di codice e celle contenenti `|` non sono supportati.

La cartella di output relativa viene risolta rispetto alla directory da cui
si avvia il comando. `--output-dir` prevale sul documento e `--no-plots`
disattiva i grafici anche se il documento contiene `plots=true`. I file già
presenti nella cartella non vengono cancellati quando un output è disattivato.
Il titolo del progetto viene mostrato nel riepilogo a terminale.

## Configurazione

`line_config.json` descrive la linea completa: 12 macchine e 6 buffer originali.
Ogni buffer ha `name`, `capacity` e `init`; ogni macchina ha `name`, `cycle_time`,
`stops` e connessioni opzionali `inlet`/`outlet` riferite ai nomi dei buffer.
Un collegamento assente o `null` rappresenta rispettivamente alimentazione o
scarico illimitati. I nomi devono essere univoci nella rispettiva collezione.

`example_config.json` è un esempio autonomo con tutti i trigger, incluso
`special_tool_change`. Per eseguirlo:

```bash
python process_simulation.py --config example_config.md --hours 24 --seed 42
```

Le chiavi di `stops` sono nomi liberi; non esistono categorie obbligatorie.
Ogni fermo definisce `trigger` e `time_to_repair`:

```json
{
  "tool_change": {
    "trigger": {"type": "cycle_count", "every": 500},
    "time_to_repair": {"distribution": "fixed", "value": 5, "unit": "minutes"}
  },
  "special_tool_change": {
    "trigger": {"type": "cycle_count", "every": 2000},
    "time_to_repair": {"distribution": "normal", "mean": 15, "std": 2, "unit": "minutes"}
  }
}
```

| `trigger.type` | Parametri | Comportamento |
| --- | --- | --- |
| `operating_time` | `distribution`, parametri e `unit` | Scatta dopo l'intervallo campionato di lavorazione effettiva; può interrompere un ciclo. |
| `per_cycle` | `probability` tra 0 e 1 | Estrazione indipendente per categoria e ciclo, intervento in un punto uniforme del ciclo. |
| `cycle_count` | `every`, intero positivo | Scatta dopo ogni N pezzi completati e trasferiti all'uscita, prima del prossimo ciclo. |

I timer operativi e le posizioni dei fermi probabilistici avanzano solo durante
la lavorazione, mai durante attese o riparazioni. Un ciclo interrotto riprende
senza scarti né rilavorazioni. Ogni fermo temporale ricampiona solo il proprio
intervallo dopo il ripristino. I contatori di ciclo sono indipendenti per fermo.
Più fermi probabilistici possono avvenire nello stesso ciclo.

Gli eventi simultanei della fase di lavorazione sono serviti in ordine di
configurazione; anche un evento all'esatta fine della lavorazione viene servito
prima dell'uscita. I fermi `cycle_count` seguono il trasferimento del pezzo,
sempre in ordine di configurazione. Al pezzo 2000 `tool_change` e
`special_tool_change` vengono quindi eseguiti entrambi, in sequenza: il secondo
non sostituisce il primo. Le riparazioni non si sovrappongono.

## Distribuzioni

Valgono per `cycle_time`, `time_to_repair` e trigger `operating_time`:

| `distribution` | Parametri |
| --- | --- |
| `fixed` | `value` |
| `normal` | `mean`, `std` |
| `exponential` | `mean` |
| `lognormal` | `mean`, `std` della durata fisica, non dei logaritmi |

`unit` è obbligatoria: `seconds`, `minutes` oppure `hours`. Nei risultati tutti
i tempi sono in ore. Parametri non finiti, negativi, probabilità fuori [0, 1],
trigger sconosciuti e riferimenti a buffer mancanti vengono rifiutati.
Cicli e intervalli operativi richiedono media positiva; campioni normali non
positivi vengono ricampionati (massimo 1000 tentativi). La normale è dunque
troncata a zero e i momenti effettivi possono differire dai parametri nominali.
Per il ripristino, un campione normale negativo è invece portato a zero.
Sono ammesse riparazioni nulle; cicli e intervalli operativi nulli sono vietati.

La configurazione della linea mantiene la formula originale di aggiustamento
dei tempi ciclo (media moltiplicata per 0,72 e deviazione `(1-0,72)*tempo/3`).
I vecchi MTBF sono intervalli esponenziali di tempo operativo. Il precedente
ripristino `lognormal(0, 0.5) * mttr` è convertito nei corrispondenti momenti
fisici: media `mttr*exp(0.125)` e deviazione
`media*sqrt(exp(0.25)-1)`. Non si assume che il vecchio `mttr` fosse già la media.
I risultati differiscono dalla prima versione perché gli intervalli ora
misurano solo il tempo operativo e il motore casuale è stato sostituito.

## Risultati

- `machines.csv`: storico degli stati, pezzi completati, tempi di lavorazione,
  attesa e fermo; colonne `stop_count:<nome>` e `downtime:<nome>` per ogni ragione.
  Il conteggio dei fermi aumenta all'inizio dell'intervento.
- `buffers.csv`: livelli e capacità, registrati ai movimenti e agli estremi
  temporali. Non sono campioni uniformi nel tempo.
- `stops.csv`: un record per intervento con nome della macchina, ragione,
  trigger, inizio, fine, durata prevista, durata trascorsa e completamento.
  Una riparazione ancora in corso ha `completed=false` e `end` vuoto.
- Cinque PNG: tempo operativo, downtime, numero dei fermi, tempi ciclo e livelli
  dei buffer. Il boxplot dei tempi ciclo usa campioni ai cambi di stato e non
  rappresenta una distribuzione pesata una volta per pezzo.

La fotografia finale comprende anche la frazione di lavoro, attesa o riparazione
in corso. SimPy interrompe prima degli eventi esattamente all'orizzonte richiesto:
un ciclo o ripristino che termina proprio lì sarà ancora nello stato precedente,
con il tempo trascorso contabilizzato.

```python
from process_simulation import load_config, run_simulation

machines, buffers, stops = run_simulation(
    hours=24, seed=42, config=load_config('example_config.md'), return_events=True
)
```

Senza `return_events=True` la funzione restituisce soltanto `machines, buffers`.
I test verificano timer, ripristini parziali, fermi simultanei, cicli, probabilità,
nomi liberi, unità, parametri lognormali, attese dei buffer e riproducibilità.
