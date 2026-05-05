# Local-Commit-AI

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

```bash
# Clona il repository (o copia i file)
git clone <url-del-repo> ~/commit

# Vai nella root del repository dove vuoi usare l'hook
cd /path/to/your/repo

# Lancia l'installer
~/commit/install.sh
```

Lo script:
1. Verifica che `git`, `python3` e `ollama` siano installati
2. Scarica il modello `qwen2.5-coder:1.5b`
3. Installa l'hook `prepare-commit-msg` nella cartella `.git/hooks/`

---

## Uso

### Commit con AI
```bash
git add .
git commit
# → L'editor si apre con il messaggio già generato dall'AI
```

### Commit senza AI (skip una tantum)
```bash
SKIP_COMMIT_AI=1 git commit -m "messaggio manuale"
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
