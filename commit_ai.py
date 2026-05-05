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
DEFAULT_MODEL = "qwen2.5-coder:7b"
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

# ── Terminal I/O ───────────────────────────────────────────────────

def tty_print(msg):
    """Stampa un messaggio sul terminale (via /dev/tty per funzionare negli hook)."""
    try:
        with open('/dev/tty', 'w') as tty:
            tty.write(msg)
            tty.flush()
    except OSError:
        print(msg, flush=True)


def tty_input(prompt):
    """Legge input dall'utente via /dev/tty (necessario negli hook git)."""
    try:
        tty_print(prompt)
        with open('/dev/tty', 'r') as tty:
            return tty.readline().strip().lower()
    except OSError:
        return "y"  # Se non c'è un terminale, accetta automaticamente

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
    
    if language == "it":
        return f"""Analizza le modifiche nel GIT DIFF fornito alla fine e scrivi un messaggio di commit professionale in formato Conventional Commits.

REGOLE DA SEGUIRE:
1. Genera UN SOLO messaggio.
2. Formato: <tipo>(<ambito>): <descrizione>
3. Lingua: ITALIANO.
4. Tipi ammessi: feat, fix, refactor, docs, chore, style, test, perf.
5. NON usare introduzioni (es. "Ecco il messaggio...") o spiegazioni.
6. NON copiare gli esempi qui sotto, usali solo per il FORMATO.

ESEMPIO FORMATO (NON COPIARE):
tipo(ambito): descrizione breve della modifica

GIT DIFF:
{diff}
"""

    # Default (English)
    return f"""Analyze the changes in the provided GIT DIFF at the end and write a professional commit message in Conventional Commits format.

STRICT RULES:
1. Output ONLY ONE message.
2. Format: <type>(<scope>): <description>
3. Language: ENGLISH.
4. Allowed types: feat, fix, refactor, docs, chore, style, test, perf.
5. Do NOT include introductions or explanations.
6. Do NOT copy the examples below, use them for FORMAT only.

FORMAT EXAMPLE (DO NOT COPY):
type(scope): short description of the change

GIT DIFF:
{diff}
"""

# ── Ollama API ─────────────────────────────────────────────────────

def call_ollama(config, prompt):
    """Invia il prompt a Ollama e restituisce il messaggio generato (già sanitizzato)."""
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

    with urllib.request.urlopen(req, timeout=config["TIMEOUT"]) as response:
        log(f"Ollama response status: {response.status}")
        if response.status == 200:
            response_data = json.loads(response.read().decode('utf-8'))
            commit_msg = response_data.get('response', '').strip()
            commit_msg = sanitize_commit_message(commit_msg)
            log(f"Generated commit_msg ({len(commit_msg)} chars): {commit_msg[:100]}...")
            return commit_msg
    return ""

# ── Modalità Interattiva ───────────────────────────────────────────

def interactive_confirm(config, prompt, commit_msg):
    """
    Mostra il messaggio generato e chiede conferma all'utente.
    Ritorna (messaggio, accettato) dove accettato indica se il messaggio è stato confermato.
    Il messaggio viene sempre restituito per poterlo pre-compilare nell'editor.
    """
    while True:
        tty_print("\n┌─────────────────────────────────────────────┐\n")
        tty_print("│  GitWise — Commit Message Generato          │\n")
        tty_print("└─────────────────────────────────────────────┘\n\n")

        # Mostra il messaggio con indentazione
        for line in commit_msg.split('\n'):
            tty_print(f"  {line}\n")

        tty_print("\n")
        choice = tty_input("  [y] Accetta  [r] Rigenera  [e] Modifica nell'editor  [q] Rifiuta → ")

        if choice in ('', 'y', 'yes', 's', 'si', 'sì'):
            log("User accepted commit message")
            return commit_msg, True
        elif choice in ('r', 'rigenera', 'regenerate'):
            tty_print("\n Rigenerando...\n")
            try:
                commit_msg = call_ollama(config, prompt)
                if not commit_msg:
                    tty_print("  Errore: risposta vuota da Ollama.\n")
                    return "", False
            except Exception as e:
                tty_print(f"  Errore: {e}\n")
                log(f"Regeneration error: {e}")
                return "", False
        elif choice in ('e', 'edit', 'modifica'):
            log("User wants to edit in editor")
            tty_print("  Ok, il messaggio sarà pre-compilato nell'editor.\n")
            return commit_msg, False
        elif choice in ('q', 'quit', 'rifiuta', 'n', 'no'):
            log("User rejected AI commit message - aborting commit")
            tty_print("  ❌ Commit annullato.\n")
            sys.exit(1)
        else:
            tty_print("  Scelta non valida. Usa: y (accetta), r (rigenera), e (modifica), q (rifiuta)\n")

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

    tty_print("Generating commit message with GitWise...\n")

    try:
        commit_msg = call_ollama(config, prompt)

        if not commit_msg:
            tty_print("⚠️  Risposta vuota da Ollama. Scrivi il commit manualmente.\n")
            sys.exit(0)

        # Modalità interattiva: mostra e chiedi conferma
        commit_msg, accepted = interactive_confirm(config, prompt, commit_msg)

        if commit_msg:
            with open(commit_msg_file, 'r') as f:
                original_content = f.read()

            with open(commit_msg_file, 'w') as f:
                f.write(f"{commit_msg}\n\n{original_content}")

            if accepted:
                tty_print("✅ Commit message applicato!\n")
            else:
                tty_print("Messaggio pre-compilato. Modificalo nell'editor.\n")
            log("commit_msg written successfully")

    except Exception as e:
        log(f"Error calling Ollama: {e}")
        tty_print(f"⚠️  Ollama non raggiungibile ({e}). Scrivi il commit manualmente.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
