# drone-coverage-optimization
Modello Gurobi per l'ottimizzazione della copertura di droni

```markdown
# 🚁 UAV Sweep Coverage Optimization

Questo repository contiene il codice sorgente per la generazione e la risoluzione di un problema di **Ottimizzazione di Copertura con Droni (UAV)** tramite programmazione matematica (MILP). Il progetto è stato sviluppato per dimostrare come bilanciare il consumo energetico di un drone (movimento vs. sensori) garantendo la copertura di target con scadenze temporali.

## 📁 Struttura del Progetto

Il progetto si divide in due componenti principali:

1. **`generatore.py` (Instance Generator):** Crea scenari operativi su una griglia 10x10 km. Posiziona nodi e target, calcola le distanze, genera il grafo di connessione e dimensiona dinamicamente la batteria e le scadenze dei target in base alla difficoltà scelta (Facile/Difficile). Salva i dati in un file `instance.json`.
2. **`modello_matematico.py` (MILP Solver):** Legge l'istanza JSON, costruisce il modello matematico su **Gurobi Optimizer** e trova la rotta e la schedulazione dei sensori ottimali per minimizzare le penalità di mancata copertura. Include un modulo di visualizzazione avanzato (grafici statici e animazioni).

## ⚙️ Requisiti e Installazione

Per far funzionare il progetto sul tuo computer, devi avere **Python 3.8+** installato e le seguenti librerie. 

Puoi installare le librerie necessarie tramite il file `requirements.txt` o lanciando:
```bash
pip install gurobipy matplotlib

```

> **⚠️ NOTA IMPORTANTE SU GUROBI:**
> Il risolutore Gurobi richiede una licenza valida per funzionare. Gli studenti e i ricercatori universitari possono richiedere una **licenza accademica gratuita** sul [sito ufficiale di Gurobi](https://www.gurobi.com/).

## 🚀 Come usare il codice

Il flusso di lavoro prevede due passaggi sequenziali:

### 1. Generare un'istanza

Lancia il generatore dal terminale:

```bash
python generatore.py

```

* Segui le istruzioni a schermo per scegliere la difficoltà (1 = Facile, 2 = Difficile).
* Puoi personalizzare il numero di nodi, target e la densità del grafo, oppure premere `INVIO` per usare i valori calcolati automaticamente.
* Il programma salverà i dati in `instance.json` e mostrerà un'anteprima grafica della mappa operativa.

### 2. Risolvere il modello

Una volta generato il file `.json`, lancia il risolutore matematico:

```bash
python modello_matematico.py

```

* Gurobi prenderà in carico il modello e mostrerà i log di ottimizzazione.
* A soluzione trovata, verrà stampato a terminale un **Report Energetico** dettagliato e un **Diario di Missione** step-by-step.
* Infine, un menu interattivo ti permetterà di scegliere come visualizzare i risultati:
* `1` - **Grafico Statico:** Mappa completa con percorso e cronologia testuale.
* `2` - **Animazione Dinamica:** Riproduzione passo-passo del volo del drone e dell'attivazione dei sensori (con cerchi di copertura colorati in base alla potenza).



## 📊 Caratteristiche del Modello Matematico

* **Dimensionamento Dinamico:** Il budget energetico e le scadenze non sono costanti, ma scalano proporzionalmente alla dimensione del grafo ($T_{cycle}$ stimato).
* **Vincoli Spazio-Temporali:** Previene spostamenti fisicamente impossibili (anti-teletrasporto).
* **Sensori Multi-Livello:** Il drone può scegliere tra 3 livelli di potenza del sensore, bilanciando raggio d'azione e consumo istantaneo.

```

```
