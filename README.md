# simpy_markov

Biblioteca Python per simulare processi produttivi con SimPy: buffer, macchine,
fermi configurabili e CSV incrementali per simulazioni lunghe. Versione 0.2.0;
richiede Python 3.10 o successivo. Il nome per pip e il comando sono
`simpy-markov`, il nome da importare è `simpy_markov`.

## Installazione

Da GitHub, in qualsiasi ambiente Python compatibile:

```bash
python -m pip install git+https://github.com/luishpinto/simpy_markov.git
```

Git deve essere disponibile per l'installazione da repository. In alternativa,
dalla copia locale o da un archivio del progetto estratto:

```bash
python -m pip install .
```

Per lavorare sul codice dal repository:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -t . -v
```

Su Windows: `.venv\Scripts\activate`. Il pacchetto sarà importabile da ogni
cartella usando il Python dell'ambiente in cui è stato installato. Non richiede
modifiche a `sys.path` o `PYTHONPATH`. Non è pubblicato su PyPI.
`pyproject.toml` è la fonte dei metadati e delle dipendenze; `requirements.txt`
installa lo stesso progetto.

## Uso come biblioteca

```python
from simpy_markov import load_config, run_simulation

config = load_config("progetto.md")
machines, buffers, stops = run_simulation(
    hours=52 * 168,
    config=config,
    seed=42,
    return_events=True,
    csv_dir="results",
)
```

`load_config()` senza percorso carica la linea Ford Scorpion inclusa nel
pacchetto; anche `run_simulation()` senza `config` usa questa linea. L'API
pubblica esporta `load_config`, `validate_line`, `validate_machine`,
`run_simulation`, `save_plots`, `ProductionMachine` e `Buffer`.
L'importazione non avvia simulazioni e non scrive file. I grafici vengono
caricati solo quando si chiama `save_plots`.

## Avvio da terminale

Da qualsiasi cartella, usando la linea inclusa nel pacchetto:

```bash
simpy-markov --weeks 52 --seed 42
simpy-markov --version
```

Per una propria configurazione Markdown:

```bash
simpy-markov --config progetto.md --weeks 52 --seed 42
python -m simpy_markov --config progetto.md --hours 24 --seed 42
```

Senza durata si simulano 8736 ore. Gli output relativi alla directory corrente
vanno in `results/`, salvo configurazione diversa; `--output-dir` sceglie la
cartella e `--no-plots` disattiva le immagini. Nel repository gli input
modificabili si trovano in `examples/`:

```bash
simpy-markov --config examples/line_config.md --hours 24 --seed 42
```

Il precedente `python process_simulation.py ...` resta disponibile dalla copia
del repository dopo l'installazione. Per gli import usare `simpy_markov`.
Il seed usa un generatore locale senza modificare lo stato casuale globale.
I CSV lunghi possono occupare molto spazio su disco; gli storici in RAM hanno
un limite indipendente dalla durata della simulazione.

## Struttura del progetto

```text
pyproject.toml
src/simpy_markov/
    __init__.py       API pubblica
    __main__.py       python -m simpy_markov
    simulation.py    motore della linea
    machine.py       macchina configurabile
    buffer.py        buffer
    config.py        caricamento e validazione
    markdown_config.py
    distributions.py
    history.py       memoria limitata e CSV incrementali
    plotting.py
    cli.py
    data/            configurazioni incluse nell'installazione
examples/            configurazioni modificabili
tests/              test automatici
```

## Simulazioni lunghe e memoria

Il messaggio di sistema `Ucciso` può indicare la terminazione per memoria
esaurita. La versione precedente accumulava in RAM ogni cambiamento di stato
e movimento dei buffer, poi ricostruiva gli stessi dati in grandi DataFrame.
Ora i CSV sono scritti progressivamente durante la simulazione; non vengono
riletti o ricostruiti in memoria al termine.

```bash
simpy-markov --config examples/line_config.md --weeks 52 --seed 42
```

`--weeks` usa settimane da 168 ore ed è alternativo a `--hours`. Si possono
simulare anche più anni; la durata richiesta incide sul tempo di calcolo e
sullo spazio occupato dai CSV, non sul numero massimo di record in RAM.
L'avanzamento viene mostrato ogni 5%; `--quiet` lo nasconde.

Per impostazione predefinita restano al massimo 2000 campioni per macchina,
2000 per buffer e 2000 fermi per macchina. `--history-limit 1000` riduce
ulteriormente il limite. Gli storici vengono diradati progressivamente lungo
tutta l'esecuzione, mantenendo il primo e l'ultimo record. Il campionamento
non usa il generatore casuale del modello e non cambia i risultati produttivi.

- I CSV contengono **tutti** i record, anche quando gli storici in RAM sono
  campionati. `stops.csv` viene scritto al completamento della riparazione;
  al termine vengono aggiunti i fermi ancora in corso. L'ordine è quindi di
  registrazione/completamento, non necessariamente di inizio del fermo.
- Contatori produttivi, numero dei fermi, tempi accumulati e fotografia finale
  sono completi. I grafici temporali e i boxplot usano campioni e possono
  omettere dettagli intermedi. Le barre dei totali finali restano complete.
- Con `csv=false` non vengono salvati gli storici completi; il limite di
  memoria resta attivo anche con `plots=false` o `--no-plots`.
- Il fabbisogno di memoria cresce con il numero di macchine, buffer e categorie,
  oltre che con il limite scelto. Il limite non rappresenta un tetto in byte
  per l'intero processo.

Per l'uso come modulo, `run_simulation(..., csv_dir='results')` abilita gli
stessi CSV incrementali. `history_limit=2000` è il limite predefinito; i
DataFrame restituiti diventano campionati oltre tale limite per serie e
riportano gli attributi `history_sampled` e `total_records`.
`history_limit=None` conserva tutto in RAM ed è riservato a prove brevi.
Il parametro `csv_dir` è esplicito: senza di esso l'API non scrive file.

Verifica eseguita sulla linea inclusa, seed 42: **52 settimane completate**, circa
8,79 milioni di record CSV (894 MiB su disco), cinque grafici e picco di RAM
misurato di circa 117 MiB nell'ambiente di prova. Tempo circa 95 secondi;
i valori dipendono dalla macchina e dalla configurazione.

## Documento Markdown di input

Il formato predefinito è `line_config.md`; `example_config.md` contiene tutti i
tipi di fermo. Il lettore accetta anche `.json`, ma gli esempi del repository usano soltanto Markdown.
Il codice principale è nel pacchetto `simpy_markov`;
`process_simulation.py` è un avvio compatibile dalla copia del repository.

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
`probability`, `every`, `blocks_machine`. Usare `-` per i campi non applicabili. Le intestazioni
sono fisse, ma l'ordine delle colonne è libero. I vecchi documenti senza
`blocks_machine` restano validi: il comportamento predefinito è bloccante.

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

## Eventi bloccanti e paralleli

La colonna `blocks_machine` si compila soltanto nella riga `trigger`, con
`true` oppure `false`. Nelle righe `cycle_time` e `time_to_repair` usare `-`.
I nomi degli eventi restano completamente liberi.

| name | parameter | type | distribution | mean | std | value | unit | probability | every | blocks_machine |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| - | cycle_time | - | fixed | - | - | 18 | minutes | - | - | - |
| maintenance | trigger | operating_time | fixed | - | - | 12 | minutes | - | - | true |
| maintenance | time_to_repair | - | fixed | - | - | 10 | minutes | - | - | - |
| tool_change | trigger | cycle_count | - | - | - | - | - | - | 250 | false |
| tool_change | time_to_repair | - | fixed | - | - | 5 | minutes | - | - | - |

`true` sospende la macchina e poi riprende la lavorazione residua. `false`
avvia un'attività in parallelo: la produzione continua e il ripristino avanza
anche mentre la macchina attende un buffer o è ferma per un altro motivo.
Attività parallele di categorie diverse possono sovrapporsi. Non viene
ipotizzata una risorsa operatore condivisa.

Una stessa categoria non può avere più interventi attivi: gli scatti per
ciclo/conteggio mentre quell'attività è in corso vengono ignorati, senza code.
Il prossimo intervallo `operating_time` della categoria viene campionato
soltanto alla fine dell'intervento. I timer delle altre categorie avanzano
normalmente quando la macchina lavora, anche se ci sono attività parallele.

Negli esempi inclusi e in `perkins_compact_x.md` la manutenzione è impostata
bloccante; `tool_change`, `special_tool_change` e i controlli qualità degli
esempi sono paralleli. È una scelta esplicita dei documenti di esempio:
il programma non assegna alcun comportamento in base al nome.

I risultati distinguono, sempre in ore:

- `takt`: tempo campionato per il ciclo corrente, mantenuto per compatibilità.
- `processing_time`: tempo di sola lavorazione dell'ultimo ciclo lavorato.
- `actual_cycle_time`: durata dell'ultimo ciclo lavorato, dall'inizio della
  lavorazione alla sua fine, inclusi gli interventi bloccanti al suo interno.
  Le attese dei buffer e gli interventi tra due cicli sono esclusi.
- `time_between_completions`: intervallo tra gli ultimi due pezzi trasferiti
  all'uscita; include anche attese dei buffer e interventi tra i pezzi.
  Per il primo pezzo rimane vuoto.

I campi dell'ultimo ciclo restano vuoti finché nessun ciclo è stato lavorato
interamente, poi mantengono l'ultimo valore anche mentre il successivo è in
corso. Un ciclo può essere già lavorato ma ancora in attesa del buffer di
uscita. Nell'esempio sopra il primo ciclo ha 18 minuti di `processing_time`
e 28 minuti di `actual_cycle_time`. Il grafico `cycle_time.png` usa il tempo
effettivo e mostra anche medie e valori estremi, per rendere visibili i fermi.

`downtime:<nome>` e `failed_time` misurano solo il tempo in cui la macchina è
ferma per eventi bloccanti. `event_time:<nome>` misura la durata trascorsa
dell'intervento, anche parallelo. Le durate parallele possono sovrapporsi e
non vanno sommate per ricavare il tempo perso dalla macchina. `stops.csv`
include `blocks_machine`, oltre alle durate previste/trascorse, anche per le
attività ancora in corso all'orizzonte della simulazione.

## Configurazione

`line_config.md` descrive la linea completa: 12 macchine e 6 buffer originali.
Ogni buffer ha `name`, `capacity` e `init`; ogni macchina ha `name`, `cycle_time`,
`stops` e connessioni opzionali `inlet`/`outlet` riferite ai nomi dei buffer.
Un collegamento assente o `null` rappresenta rispettivamente alimentazione o
scarico illimitati. I nomi devono essere univoci nella rispettiva collezione.

`example_config.md` è un esempio autonomo con tutti i trigger, incluso
`special_tool_change`. Per eseguirlo:

```bash
simpy-markov --config examples/example_config.md --hours 24 --seed 42
```

Le chiavi di `stops` sono nomi liberi; non esistono categorie obbligatorie.
Ogni fermo definisce `trigger` e `time_to_repair`:

```json
{
  "tool_change": {
    "trigger": {"type": "cycle_count", "every": 500, "blocks_machine": false},
    "time_to_repair": {"distribution": "fixed", "value": 5, "unit": "minutes"}
  },
  "special_tool_change": {
    "trigger": {"type": "cycle_count", "every": 2000, "blocks_machine": false},
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
la lavorazione, mai durante attese o riparazioni bloccanti. Un ciclo interrotto riprende
senza scarti né rilavorazioni. Ogni fermo temporale ricampiona solo il proprio
intervallo dopo il ripristino. I contatori di ciclo sono indipendenti per fermo.
Più fermi probabilistici possono avvenire nello stesso ciclo.

Gli eventi simultanei della fase di lavorazione sono serviti in ordine di
configurazione; anche un evento all'esatta fine della lavorazione viene servito
prima dell'uscita. I fermi `cycle_count` seguono il trasferimento del pezzo,
sempre in ordine di configurazione. Al pezzo 2000 `tool_change` e
`special_tool_change` vengono quindi avviati entrambi: il secondo
non sostituisce il primo. Gli interventi bloccanti sono sequenziali; le attività
con `blocks_machine=false` possono invece sovrapporsi.

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

- `machines.csv`: storico completo degli stati, scritto durante la simulazione, con pezzi completati e tempi di lavorazione,
  attesa e fermo; colonne `stop_count:<nome>`, `downtime:<nome>` e
  `event_time:<nome>` per ogni ragione.
  Il conteggio dei fermi aumenta all'inizio dell'intervento.
- `buffers.csv`: livelli e capacità, registrati ai movimenti e agli estremi
  temporali. Non sono campioni uniformi nel tempo.
- `stops.csv`: un record per intervento con nome della macchina, ragione,
  trigger, `blocks_machine`, inizio, fine, durata prevista, durata trascorsa e completamento.
  Una riparazione ancora in corso ha `completed=false` e `end` vuoto.
- Cinque PNG: tempo operativo, downtime, numero dei fermi, tempi ciclo e livelli
  dei buffer. Il boxplot dei tempi ciclo effettivi usa gli ultimi valori completati
  campionati ai cambi di stato e non
  rappresenta una distribuzione pesata una volta per pezzo.

La fotografia finale comprende anche la frazione di lavoro, attesa o riparazione
in corso. SimPy interrompe prima degli eventi esattamente all'orizzonte richiesto:
un ciclo o ripristino che termina proprio lì sarà ancora nello stato precedente,
con il tempo trascorso contabilizzato.

```python
from simpy_markov import load_config, run_simulation

machines, buffers, stops = run_simulation(
    hours=24, seed=42, config=load_config('examples/example_config.md'), return_events=True
)
```

Senza `return_events=True` la funzione restituisce soltanto `machines, buffers`.
I test verificano timer, ripristini parziali, fermi simultanei, cicli, probabilità,
nomi liberi, unità, parametri lognormali, attese dei buffer e riproducibilità.
