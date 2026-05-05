#!/usr/bin/env python3
"""
GitWise — Genera messaggi di commit con Ollama.
Invocato dall'hook prepare-commit-msg.
"""
import sys
import subprocess
import urllib.request
import urllib.error
import json
import os
import re
from datetime import datetime

# ── Defaults ────────────────────────────────────────────────────────
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5-coder:1.5b"
DEFAULT_MAX_DIFF = 3000
DEFAULT_LANGUAGE = "en"
DEFAULT_TIMEOUT = 120

# ── Configurazione ─────────────────────────────────────────────────

def get_repo_root():
    """Restituisce la root del repository git corrente."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return os.getcwd()


def load_config():
    """
    Carica la configurazione con priorità:
    variabile d'ambiente > .commit-ai.conf > default hardcoded.
    """
    config = {
        "OLLAMA_URL": DEFAULT_OLLAMA_URL,
        "MODEL": DEFAULT_MODEL,
        "MAX_DIFF_LENGTH": DEFAULT_MAX_DIFF,
        "LANGUAGE": DEFAULT_LANGUAGE,
        "TIMEOUT": DEFAULT_TIMEOUT,
    }

    # Cerca .commit-ai.conf nella root del repo
    repo_root = get_repo_root()
    conf_path = os.path.join(repo_root, ".commit-ai.conf")
    if os.path.exists(conf_path):
        with open(conf_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key in config:
                        config[key] = value

    # Override con variabili d'ambiente (prefisso COMMIT_AI_)
    env_map = {
        "COMMIT_AI_URL": "OLLAMA_URL",
        "COMMIT_AI_MODEL": "MODEL",
        "COMMIT_AI_MAX_DIFF": "MAX_DIFF_LENGTH",
        "COMMIT_AI_LANGUAGE": "LANGUAGE",
        "COMMIT_AI_TIMEOUT": "TIMEOUT",
    }
    for env_key, conf_key in env_map.items():
        val = os.environ.get(env_key)
        if val:
            config[conf_key] = val

    # Cast dei tipi numerici
    config["MAX_DIFF_LENGTH"] = int(config["MAX_DIFF_LENGTH"])
    config["TIMEOUT"] = int(config["TIMEOUT"])

    return config

# ── Logging ─────────────────────────────────────────────────────────

def get_log_path():
    """Log nella home dell'utente sotto ~/.commit-ai/."""
    log_dir = os.path.expanduser("~/.commit-ai")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "commit_ai.log")


def log(msg):
    """Scrive un messaggio nel file di log con timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(get_log_path(), "a") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except OSError:
        pass  # Non bloccare mai il commit per un errore di log

# ── Git Diff ────────────────────────────────────────────────────────

def get_git_diff():
    """Restituisce il diff completo dell'area di staging."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached'],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        log(f"Git diff error: {e}")
        return ""


def get_git_stat():
    """Restituisce il sommario statistico del diff (file + righe modificate)."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--stat'],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def smart_truncate_diff(diff, max_length):
    """
    Troncamento intelligente del diff:
    1. Genera un sommario con git diff --stat (sempre incluso)
    2. Riempie lo spazio rimanente con il diff reale, troncando per righe complete
    """
    if len(diff) <= max_length:
        return diff

    stat = get_git_stat()
    header = f"=== File Summary ===\n{stat}\n=== Diff (truncated) ===\n"

    budget = max_length - len(header)
    if budget <= 0:
        return header

    # Tronca per righe complete, non a metà riga
    lines = diff.split('\n')
    truncated_lines = []
    current_length = 0
    for line in lines:
        if current_length + len(line) + 1 > budget:
            break
        truncated_lines.append(line)
        current_length += len(line) + 1

    truncated_diff = '\n'.join(truncated_lines)
    return f"{header}{truncated_diff}\n...[diff truncated]"

# ── Sanitizzazione Output ──────────────────────────────────────────

def sanitize_commit_message(msg):
    """
    Pulisce l'output del modello:
    - Rimuove code blocks (```...```)
    - Rimuove prefissi comuni ("Here is...", "Commit message:", ecc.)
    - Rimuove righe vuote iniziali/finali
    - Tronca la subject line a 72 caratteri
    """
    # Rimuovi code blocks
    msg = re.sub(r'```[\w]*\n?', '', msg)

    # Rimuovi prefissi comuni
    prefixes = [
        r'^Here is.*?:\s*\n',
        r'^Here\'s.*?:\s*\n',
        r'^Commit message:\s*\n',
        r'^Suggested commit message:\s*\n',
        r'^The commit message.*?:\s*\n',
    ]
    for pattern in prefixes:
        msg = re.sub(pattern, '', msg, flags=re.IGNORECASE)

    # Pulizia whitespace
    msg = msg.strip()

    if not msg:
        return msg

    # Tronca la subject line (prima riga) a 72 caratteri
    lines = msg.split('\n')
    if len(lines[0]) > 72:
        lines[0] = lines[0][:69] + '...'

    return '\n'.join(lines)

# ── Prompt ──────────────────────────────────────────────────────────

def build_prompt(diff, language):
    """Costruisce il prompt per il modello in base alla lingua scelta."""
    lang_instruction = {
        "en": "Write the commit message in English.",
        "it": "Scrivi il messaggio di commit in italiano.",
        "es": "Escribe el mensaje de commit en español.",
        "fr": "Écris le message de commit en français.",
        "de": "Schreibe die Commit-Nachricht auf Deutsch.",
    }

    lang_line = lang_instruction.get(language, lang_instruction["en"])

    return f"""Write a git commit message following the Conventional Commits specification based on the git diff provided below.
Rules:
- Format: <type>(<optional scope>): <description>
- Include a blank line and then a more detailed body if necessary.
- Do not wrap the message in code blocks or quotes.
- Only output the commit message, no introductions or explanations.
- Keep the subject line under 72 characters.
- {lang_line}

Git Diff:
{diff}
"""

# ── Main ────────────────────────────────────────────────────────────

def main():
    log("commit_ai.py started")

    if len(sys.argv) < 2:
        log("No argv[1] provided")
        sys.exit(0)

    commit_msg_file = sys.argv[1]
    log(f"commit_msg_file: {commit_msg_file}")

    if not os.path.exists(commit_msg_file):
        log("commit_msg_file does not exist")
        sys.exit(0)

    # Carica configurazione
    config = load_config()
    log(f"Config: model={config['MODEL']}, lang={config['LANGUAGE']}, max_diff={config['MAX_DIFF_LENGTH']}")

    # Leggi il diff
    diff = get_git_diff()
    if not diff.strip():
        log("Empty diff")
        sys.exit(0)

    # Troncamento intelligente
    diff = smart_truncate_diff(diff, config["MAX_DIFF_LENGTH"])

    # Costruisci il prompt
    prompt = build_prompt(diff, config["LANGUAGE"])

    log("Sending request to Ollama")

    data = {
        "model": config["MODEL"],
        "prompt": prompt,
        "stream": False
    }

    req = urllib.request.Request(
        config["OLLAMA_URL"],
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    print("⏳ Generating commit message with Ollama...")
    sys.stdout.flush()

    try:
        with urllib.request.urlopen(req, timeout=config["TIMEOUT"]) as response:
            log(f"Ollama response status: {response.status}")
            if response.status == 200:
                response_data = json.loads(response.read().decode('utf-8'))
                commit_msg = response_data.get('response', '').strip()

                # Sanitizza l'output
                commit_msg = sanitize_commit_message(commit_msg)
                log(f"Generated commit_msg ({len(commit_msg)} chars): {commit_msg[:100]}...")

                if commit_msg:
                    with open(commit_msg_file, 'r') as f:
                        original_content = f.read()

                    with open(commit_msg_file, 'w') as f:
                        f.write(f"{commit_msg}\n\n{original_content}")

                    print("✅ Commit message generated!")
                    sys.stdout.flush()
                    log("commit_msg written successfully")

    except Exception as e:
        log(f"Error calling Ollama: {e}")
        print(f"⚠️  Ollama non raggiungibile ({e}). Scrivi il commit manualmente.")
        sys.stdout.flush()
        sys.exit(0)


if __name__ == "__main__":
    main()
