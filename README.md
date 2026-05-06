# GitWise

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Genera automaticamente messaggi di commit in formato **Conventional Commits** utilizzando un modello AI locale tramite [Ollama](https://ollama.ai/).

Nessun dato lascia il tuo computer. Tutto gira in locale.

---

## Funzionalità

- Genera commit message analizzando il `git diff --cached`
- Formato [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `refactor:`, ecc.)
- Supporto multilingua (🇬🇧 EN, 🇮🇹 IT, 🇪🇸 ES, 🇫🇷 FR, 🇩🇪 DE)
- Troncamento intelligente dei diff grandi (sommario + dettaglio)
- Sanitizzazione automatica dell'output (rimuove code blocks, prefissi, ecc.)
- Configurazione flessibile (file `.commit-ai.conf` + variabili d'ambiente)
- Skip facile con `SKIP_COMMIT_AI=1`
- Fallback silenzioso se Ollama non è attivo

---

## Prerequisiti

- **Python 3.6+**
- **Git**
- **[Ollama](https://ollama.ai/)** installato e funzionante

---

## Installazione

### Installazione Rapida (consigliata)

Dalla root del tuo repository git, esegui:

```bash
curl -sSL https://raw.githubusercontent.com/ThetaLogN/GitWise/main/install.sh | bash
```

### Installazione Manuale

Se preferisci controllare i file prima di installarli:

```bash
# 1. Clona il repository
git clone https://github.com/ThetaLogN/GitWise.git ~/GitWise

# 2. Vai nella root del tuo repository git
cd /path/to/your/repo

# 3. Esegui l'installer locale
~/GitWise/install.sh
```

Lo script:
1. Verifica che `git`, `python3` e `ollama` siano installati
2. Scarica il modello `qwen2.5-coder:7b` (se non presente)
3. Installa l'hook `prepare-commit-msg` nella cartella `.git/hooks/`

---

## Uso

### Commit con AI (modalità interattiva)
```bash
git add .
git commit
# → GitWise genera il messaggio e te lo mostra nel terminale
# → Scegli: [Y] Accetta  [r] Rigenera  [n] Scrivi manualmente
```

### Commit con messaggio manuale (`-m`)
```bash
git commit -m "il mio messaggio"
# → GitWise non si attiva, il messaggio viene usato così com'è
```

### Commit senza AI (skip una tantum)
```bash
SKIP_COMMIT_AI=1 git commit
```

### Commit con modello diverso (una tantum)
```bash
COMMIT_AI_MODEL=llama3:8b git commit
```

---

## Configurazione

Crea un file `.commit-ai.conf` nella **root del tuo repository** per personalizzare il comportamento:

```ini
# .commit-ai.conf
MODEL=qwen2.5-coder:1.5b
OLLAMA_URL=http://localhost:11434/api/generate
MAX_DIFF_LENGTH=3000
LANGUAGE=it
TIMEOUT=120
```

Un file di esempio è disponibile in `.commit-ai.conf.example`.

### Opzioni

| Chiave | Default | Env Override | Descrizione |
|--------|---------|--------------|-------------|
| `MODEL` | `qwen2.5-coder:1.5b` | `COMMIT_AI_MODEL` | Modello Ollama |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | `COMMIT_AI_URL` | Endpoint API |
| `MAX_DIFF_LENGTH` | `3000` | `COMMIT_AI_MAX_DIFF` | Max caratteri del diff |
| `LANGUAGE` | `en` | `COMMIT_AI_LANGUAGE` | Lingua del messaggio |
| `TIMEOUT` | `120` | `COMMIT_AI_TIMEOUT` | Timeout in secondi |

**Priorità**: Variabile d'ambiente → `.commit-ai.conf` → Default

---

## Disinstallazione

```bash
cd /path/to/your/repo
~/commit/install.sh --uninstall
```

Rimuove i file `commit_ai.py` e `prepare-commit-msg` dalla cartella `.git/hooks/`.

---

## Troubleshooting

### Il commit si blocca / non succede niente
- Assicurati che Ollama sia avviato (`ollama serve` o l'app desktop)
- Controlla il log: `cat ~/.commit-ai/commit_ai.log`

### Il messaggio generato è di scarsa qualità
- Prova un modello più grande: `COMMIT_AI_MODEL=qwen2.5-coder:7b git commit`
- Aumenta il budget del diff: imposta `MAX_DIFF_LENGTH=5000` nel config

### Voglio generare commit in italiano
- Aggiungi `LANGUAGE=it` nel file `.commit-ai.conf`
- Oppure: `COMMIT_AI_LANGUAGE=it git commit`

---

## Struttura del Progetto

```
commit/
├── commit_ai.py              # Script Python principale
├── prepare-commit-msg        # Git hook (bash)
├── install.sh                # Installer / Uninstaller
├── .commit-ai.conf.example   # Configurazione di esempio
├── .gitignore
└── README.md
```

---

## Licenza

MIT
