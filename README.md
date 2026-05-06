# GitWise

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![GitWise Demo](media/demo.gif)


Automatically generates commit messages in **Conventional Commits** format using a local AI model via [Ollama](https://ollama.ai/).

No data leaves your computer. Everything runs locally.

---

## Features

- Generates commit messages by analyzing `git diff --cached`
- [Conventional Commits](https://www.conventionalcommits.org/) format (`feat:`, `fix:`, `refactor:`, etc.)
- Multi-language support (🇬🇧 EN, 🇮🇹 IT, 🇪🇸 ES, 🇫🇷 FR, 🇩🇪 DE)
- Smart truncation of large diffs (summary + detail)
- Automatic output sanitization (removes code blocks, prefixes, etc.)
- Flexible configuration (`.commit-ai.conf` file + environment variables)
- Easy skip with `SKIP_COMMIT_AI=1`
- Silent fallback if Ollama is not active

---

## Prerequisites

- **Python 3.6+**
- **Git**
- **[Ollama](https://ollama.ai/)** installed and running

---

## Installation

### Quick Install (recommended)

From the root of your git repository, run:

```bash
curl -sSL https://raw.githubusercontent.com/ThetaLogN/GitWise/main/install.sh | bash
```

### Manual Installation

If you prefer to review the files before installing:

```bash
# 1. Clone the repository
git clone https://github.com/ThetaLogN/GitWise.git ~/GitWise

# 2. Go to the root of your git repository
cd /path/to/your/repo

# 3. Run the local installer
~/GitWise/install.sh
```

The script will:
1. Verify that `git`, `python3`, and `ollama` are installed
2. Download the `qwen2.5-coder:7b` model (if not present)
3. Install the `prepare-commit-msg` hook in the `.git/hooks/` folder

---

## Usage

### Commit with AI (interactive mode)
```bash
git add .
git commit
# → GitWise generates the message and shows it in the terminal
# → Choose: [Y] Accept  [r] Regenerate  [e] Edit in editor  [q] Abort
```

### Commit with manual message (`-m`)
```bash
git commit -m "my message"
# → GitWise remains inactive, the message is used as is
```

### Commit without AI (one-time skip)
```bash
SKIP_COMMIT_AI=1 git commit
```

### Commit with a different model (one-time)
```bash
COMMIT_AI_MODEL=llama3:8b git commit
```

---

## Configuration

Create a `.commit-ai.conf` file in the **root of your repository** to customize behavior:

```ini
# .commit-ai.conf
MODEL=qwen2.5-coder:1.5b
OLLAMA_URL=http://localhost:11434/api/generate
MAX_DIFF_LENGTH=3000
LANGUAGE=en
TIMEOUT=120
```

An example file is available in `.commit-ai.conf.example`.

### Options

| Key | Default | Env Override | Description |
|-----|---------|--------------|-------------|
| `MODEL` | `qwen2.5-coder:7b` | `COMMIT_AI_MODEL` | Ollama model |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | `COMMIT_AI_URL` | API Endpoint |
| `MAX_DIFF_LENGTH` | `3000` | `COMMIT_AI_MAX_DIFF` | Max diff characters |
| `LANGUAGE` | `en` | `COMMIT_AI_LANGUAGE` | Message language |
| `TIMEOUT` | `120` | `COMMIT_AI_TIMEOUT` | Timeout in seconds |

**Priority**: Environment variable → `.commit-ai.conf` → Default

---

## Uninstallation

```bash
cd /path/to/your/repo
~/GitWise/install.sh --uninstall
```

This removes the `commit_ai.py` and `prepare-commit-msg` files from the `.git/hooks/` folder.

---

## Troubleshooting

### Commit hangs / nothing happens
- Ensure Ollama is running (`ollama serve` or the desktop app)
- Check the log: `cat ~/.commit-ai/commit_ai.log`

### Generated message is poor quality
- Try a larger model: `COMMIT_AI_MODEL=qwen2.5-coder:7b git commit`
- Increase the diff budget: set `MAX_DIFF_LENGTH=5000` in the config

### I want to generate commits in Italian
- Add `LANGUAGE=it` to the `.commit-ai.conf` file
- Or: `COMMIT_AI_LANGUAGE=it git commit`

---

## Project Structure

```
GitWise/
├── commit_ai.py              # Main Python script
├── prepare-commit-msg        # Git hook (bash)
├── install.sh                # Installer / Uninstaller
├── .commit-ai.conf.example   # Example configuration
├── .gitignore
└── README.md
```

---

## License

MIT
