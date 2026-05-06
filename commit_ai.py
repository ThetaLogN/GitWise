#!/usr/bin/env python3
"""
GitWise — Generate commit messages with Ollama.
Invoked by the prepare-commit-msg hook.
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
SUPPORTED_LANGUAGES = {"en", "it", "es", "fr", "de"}

# ── Configuration ─────────────────────────────────────────────────

def get_repo_root():
    """Returns the root of the current git repository."""
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
    Loads configuration with priority:
    Environment variable > .commit-ai.conf > hardcoded default.
    """
    config = {
        "OLLAMA_URL": DEFAULT_OLLAMA_URL,
        "MODEL": DEFAULT_MODEL,
        "MAX_DIFF_LENGTH": DEFAULT_MAX_DIFF,
        "LANGUAGE": DEFAULT_LANGUAGE,
        "TIMEOUT": DEFAULT_TIMEOUT,
    }

    # Look for .commit-ai.conf in repo root
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

    # Override with environment variables (COMMIT_AI_ prefix)
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

    # Cast numeric types
    config["MAX_DIFF_LENGTH"] = int(config["MAX_DIFF_LENGTH"])
    config["TIMEOUT"] = int(config["TIMEOUT"])

    # Validate language
    if config["LANGUAGE"] not in SUPPORTED_LANGUAGES:
        log(f"Warning: unsupported language '{config['LANGUAGE']}', falling back to 'en'")
        config["LANGUAGE"] = "en"

    return config

# ── Logging ─────────────────────────────────────────────────────────

def get_log_path():
    """Logs in the user's home directory under ~/.commit-ai/."""
    log_dir = os.path.expanduser("~/.commit-ai")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "commit_ai.log")


def log(msg):
    """Writes a message to the log file with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(get_log_path(), "a") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except OSError:
        pass  # Never block the commit due to a log error


# ── Terminal I/O ───────────────────────────────────────────────────

def tty_print(msg):
    """Prints a message to the terminal (via /dev/tty to work within hooks)."""
    try:
        with open('/dev/tty', 'w') as tty:
            tty.write(msg)
            tty.flush()
    except OSError:
        print(msg, flush=True)


def tty_input(prompt):
    """Reads input from the user via /dev/tty (necessary in git hooks)."""
    try:
        tty_print(prompt)
        with open('/dev/tty', 'r') as tty:
            return tty.readline().strip().lower()
    except OSError:
        return "y"  # If no terminal is available, accept automatically


# ── Git Diff ────────────────────────────────────────────────────────

def get_git_diff():
    """Returns the full diff of the staging area."""
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
    """Returns the statistical summary of the diff (files + lines changed)."""
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
    Smart diff truncation:
    1. Generates a summary with git diff --stat (always included)
    2. Fills remaining space with the actual diff, truncating by full lines
    """
    if len(diff) <= max_length:
        return diff

    stat = get_git_stat()
    header = f"=== File Summary ===\n{stat}\n=== Diff (truncated) ===\n"

    budget = max_length - len(header)
    if budget <= 0:
        return header

    # Truncate by full lines, not in the middle of a line
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


# ── Output Sanitization ──────────────────────────────────────────

# Pattern matching a valid conventional commit line
_CC_PATTERN = re.compile(
    r'^(feat|fix|refactor|docs|chore|style|test|perf|build|ci|revert)'
    r'(\([^)]*\))?:\s*.+',
    re.IGNORECASE
)


def sanitize_commit_message(msg):
    """
    Cleans the model's output:
    - Removes code blocks (```...```)
    - Removes common prefixes ("Here is...", "Commit message:", etc.)
    - If multiple conventional commit lines are detected, keeps only the first
    - Removes leading/trailing whitespace
    """
    # Remove code blocks
    msg = re.sub(r'```[\w]*\n?', '', msg)

    # Remove common prefixes
    prefixes = [
        r'^Here is.*?:\s*\n',
        r'^Here\'s.*?:\s*\n',
        r'^Commit message:\s*\n',
        r'^Suggested commit message:\s*\n',
        r'^The commit message.*?:\s*\n',
        r'^Ecco.*?:\s*\n',
        r'^Il messaggio.*?:\s*\n',
    ]
    for pattern in prefixes:
        msg = re.sub(pattern, '', msg, flags=re.IGNORECASE)

    # Clean whitespace
    msg = msg.strip()

    if not msg:
        return msg

    # If model generated multiple conventional commit lines, keep only the first
    lines = msg.split('\n')
    cc_lines = [l.strip() for l in lines if _CC_PATTERN.match(l.strip())]
    if len(cc_lines) > 1:
        msg = cc_lines[0]

    # Remove bullet points / numbered list markers
    msg = re.sub(r'^[\d]+[.)\-]\s*', '', msg)
    msg = re.sub(r'^[-*•]\s*', '', msg)

    return msg.strip()


# ── Prompt ──────────────────────────────────────────────────────────

def build_prompt(diff, language):
    """Builds the prompt for the model based on the chosen language."""

    prompts = {
        "it": {
            "intro": "Analizza le modifiche nel GIT DIFF fornito alla fine e scrivi UN SINGOLO messaggio di commit in formato Conventional Commits.",
            "rules_title": "REGOLE OBBLIGATORIE",
            "rules": [
                "RISPONDI CON UNA SOLA RIGA. Non generare liste, elenchi o messaggi multipli.",
                "Formato: <tipo>(<ambito>): <descrizione>",
                "Lingua: ITALIANO.",
                "Tipi ammessi: feat, fix, refactor, docs, chore, style, test, perf.",
                "L'ambito deve essere un modulo logico (es. config, auth, ui), NON un nome di file.",
                'NON scrivere introduzioni, spiegazioni o commenti aggiuntivi.',
                "Riassumi TUTTE le modifiche in un unico messaggio coerente.",
                "Max 72 caratteri per la descrizione.",
            ],
            "example_title": "ESEMPIO FORMATO (NON COPIARE)",
            "example": "tipo(ambito): descrizione breve della modifica",
        },
        "es": {
            "intro": "Analiza los cambios en el GIT DIFF proporcionado al final y escribe UN SOLO mensaje de commit en formato Conventional Commits.",
            "rules_title": "REGLAS OBLIGATORIAS",
            "rules": [
                "RESPONDE CON UNA SOLA LÍNEA. No generes listas ni mensajes múltiples.",
                "Formato: <tipo>(<ámbito>): <descripción>",
                "Idioma: ESPAÑOL.",
                "Tipos permitidos: feat, fix, refactor, docs, chore, style, test, perf.",
                "El ámbito debe ser un módulo lógico (ej. config, auth, ui), NO un nombre de archivo.",
                'NO incluyas introducciones, explicaciones ni comentarios adicionales.',
                "Resume TODOS los cambios en un único mensaje coherente.",
                "Máx 72 caracteres para la descripción.",
            ],
            "example_title": "EJEMPLO DE FORMATO (NO COPIAR)",
            "example": "tipo(ámbito): descripción breve del cambio",
        },
        "fr": {
            "intro": "Analyse les modifications dans le GIT DIFF fourni à la fin et rédige UN SEUL message de commit au format Conventional Commits.",
            "rules_title": "RÈGLES OBLIGATOIRES",
            "rules": [
                "RÉPONDS AVEC UNE SEULE LIGNE. Ne génère pas de listes ni de messages multiples.",
                "Format : <type>(<portée>): <description>",
                "Langue : FRANÇAIS.",
                "Types autorisés : feat, fix, refactor, docs, chore, style, test, perf.",
                "La portée doit être un module logique (ex. config, auth, ui), PAS un nom de fichier.",
                'N\'inclus PAS d\'introductions, d\'explications ni de commentaires supplémentaires.',
                "Résume TOUS les changements en un seul message cohérent.",
                "Max 72 caractères pour la description.",
            ],
            "example_title": "EXEMPLE DE FORMAT (NE PAS COPIER)",
            "example": "type(portée): description courte de la modification",
        },
        "de": {
            "intro": "Analysiere die Änderungen im bereitgestellten GIT DIFF am Ende und schreibe EINE EINZIGE Commit-Nachricht im Conventional Commits Format.",
            "rules_title": "VERPFLICHTENDE REGELN",
            "rules": [
                "ANTWORTE MIT NUR EINER ZEILE. Keine Listen oder mehrere Nachrichten generieren.",
                "Format: <Typ>(<Bereich>): <Beschreibung>",
                "Sprache: DEUTSCH.",
                "Erlaubte Typen: feat, fix, refactor, docs, chore, style, test, perf.",
                "Der Bereich muss ein logisches Modul sein (z.B. config, auth, ui), KEIN Dateiname.",
                'Keine Einleitungen, Erklärungen oder zusätzliche Kommentare.',
                "Fasse ALLE Änderungen in einer einzigen, kohärenten Nachricht zusammen.",
                "Max 72 Zeichen für die Beschreibung.",
            ],
            "example_title": "FORMATBEISPIEL (NICHT KOPIEREN)",
            "example": "Typ(Bereich): kurze Beschreibung der Änderung",
        },
    }

    # Default: English
    default = {
        "intro": "Analyze the changes in the provided GIT DIFF at the end and write a SINGLE commit message in Conventional Commits format.",
        "rules_title": "MANDATORY RULES",
        "rules": [
            "RESPOND WITH EXACTLY ONE LINE. Do NOT generate lists or multiple messages.",
            "Format: <type>(<scope>): <description>",
            "Language: ENGLISH.",
            "Allowed types: feat, fix, refactor, docs, chore, style, test, perf.",
            "The scope must be a logical module (e.g. config, auth, ui), NOT a filename.",
            'Do NOT include introductions, explanations, or additional comments.',
            "Summarize ALL changes into a single, coherent message.",
            "Max 72 characters for the description.",
        ],
        "example_title": "FORMAT EXAMPLE (DO NOT COPY)",
        "example": "type(scope): short description of the change",
    }

    p = prompts.get(language, default)
    rules = "\n".join(f"{i}. {r}" for i, r in enumerate(p["rules"], 1))

    return f"""{p["intro"]}

{p["rules_title"]}:
{rules}

{p["example_title"]}:
{p["example"]}

GIT DIFF:
{diff}
"""


# ── Ollama API ─────────────────────────────────────────────────────

def call_ollama(config, prompt):
    """Sends the prompt to Ollama and returns the generated (sanitized) message."""
    data = {
        "model": config["MODEL"],
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "num_predict": 100,
        }
    }

    req = urllib.request.Request(
        config["OLLAMA_URL"],
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    with urllib.request.urlopen(req, timeout=config["TIMEOUT"]) as response:
        log(f"Ollama response status: {response.status}")
        if response.status != 200:
            log(f"Ollama returned non-200 status: {response.status}")
            return ""
        response_data = json.loads(response.read().decode('utf-8'))
        commit_msg = response_data.get('response', '').strip()
        commit_msg = sanitize_commit_message(commit_msg)
        log(f"Generated commit_msg ({len(commit_msg)} chars): {commit_msg[:100]}...")
        return commit_msg


# ── Interactive Mode ───────────────────────────────────────────

def interactive_confirm(config, prompt, commit_msg):
    """
    Shows the generated message and asks for user confirmation.
    Returns (message, accepted) where accepted indicates if the message was confirmed.
    The message is always returned so it can be pre-filled in the editor.
    """
    while True:
        tty_print("\n┌─────────────────────────────────────────────┐\n")
        tty_print("│  GitWise — Generated Commit Message         │\n")
        tty_print("└─────────────────────────────────────────────┘\n\n")

        # Show message with indentation
        for line in commit_msg.split('\n'):
            tty_print(f"  {line}\n")

        tty_print("\n")
        choice = tty_input("  [y] Accept  [r] Regenerate  [e] Edit in editor  [q] Abort → ")

        if choice in ('', 'y', 'yes', 's', 'si', 'sì'):
            log("User accepted commit message")
            return commit_msg, True
        elif choice in ('r', 'rigenera', 'regenerate'):
            tty_print("\n Regenerating...\n")
            try:
                commit_msg = call_ollama(config, prompt)
                if not commit_msg:
                    tty_print("  Error: empty response from Ollama.\n")
                    return "", False
            except Exception as e:
                tty_print(f"  Error: {e}\n")
                log(f"Regeneration error: {e}")
                return "", False
        elif choice in ('e', 'edit', 'modifica'):
            log("User wants to edit in editor")
            tty_print("  Ok, the message will be pre-filled in the editor.\n")
            return commit_msg, False
        elif choice in ('q', 'quit', 'abort', 'n', 'no'):
            log("User rejected AI commit message - aborting commit")
            tty_print("  ❌ Commit aborted.\n")
            sys.exit(1)
        else:
            tty_print("  Invalid choice. Use: y (accept), r (regenerate), e (edit), q (abort)\n")


# ── Main ────────────────────────────────────────────────────────────

def main():
    log("commit_ai.py started")

    # Defensive skip check (mirrors prepare-commit-msg)
    if os.environ.get("SKIP_COMMIT_AI"):
        log("SKIP_COMMIT_AI is set, exiting")
        sys.exit(0)

    if len(sys.argv) < 2:
        log("No argv[1] provided")
        sys.exit(0)

    commit_msg_file = sys.argv[1]
    log(f"commit_msg_file: {commit_msg_file}")

    if not os.path.exists(commit_msg_file):
        log("commit_msg_file does not exist")
        sys.exit(0)

    # Load configuration
    config = load_config()
    log(f"Config: model={config['MODEL']}, lang={config['LANGUAGE']}, max_diff={config['MAX_DIFF_LENGTH']}")

    # Read the diff
    diff = get_git_diff()
    if not diff.strip():
        log("Empty diff")
        sys.exit(0)

    # Smart truncation
    diff = smart_truncate_diff(diff, config["MAX_DIFF_LENGTH"])

    # Build prompt
    prompt = build_prompt(diff, config["LANGUAGE"])

    log("Sending request to Ollama")

    tty_print("Generating commit message with GitWise...\n")

    try:
        commit_msg = call_ollama(config, prompt)

        if not commit_msg:
            with open(commit_msg_file, 'a') as f:
                f.write("\n# ⚠️  GitWise: Empty response from Ollama. Write the commit manually.\n")
            print("⚠️  Empty response from Ollama. Write the commit manually.", file=sys.stderr)
            sys.exit(0)

        # Interactive mode: show and ask for confirmation
        commit_msg, accepted = interactive_confirm(config, prompt, commit_msg)

        if commit_msg:
            with open(commit_msg_file, 'r') as f:
                original_content = f.read()

            with open(commit_msg_file, 'w') as f:
                f.write(f"{commit_msg}\n\n{original_content}")

            if accepted:
                tty_print("✅ Commit message applied!\n")
            else:
                tty_print("Message pre-filled. Edit it in your editor.\n")
            log("commit_msg written successfully")

    except Exception as e:
        log(f"GitWise error: {e}")
        # Determine if it's a connection error or something else
        error_type = "Ollama unreachable" if "urlopen" in str(e) or "refused" in str(e) else "Internal error"
        error_msg = f"\n# ⚠️  GitWise: {error_type} ({e})\n# Write the commit message manually.\n"
        
        try:
            with open(commit_msg_file, 'a') as f:
                f.write(error_msg)
        except Exception as file_err:
            log(f"Failed to write error comment to file: {file_err}")
        
        print(f"⚠️  GitWise: {error_type}. Write the commit manually.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
