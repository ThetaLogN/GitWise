#!/bin/bash

echo "Iniziando l'installazione di Local-Commit-AI..."

if ! command -v git &> /dev/null; then
    echo "Errore: git non è installato."
    exit 1
fi

if [ ! -d ".git" ]; then
    echo "Errore: questa directory non è la root di un repository git."
    echo "Esegui questo script dalla root del tuo repository (dove si trova la cartella .git)."
    exit 1
fi

if ! command -v ollama &> /dev/null; then
    echo "Errore: ollama non è installato o non è nel PATH."
    echo "Installa ollama da https://ollama.ai/ prima di continuare."
    exit 1
fi

MODEL_NAME="qwen2.5-coder:1.5b"
echo "Verifica del modello Ollama '$MODEL_NAME'..."
ollama pull $MODEL_NAME

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HOOKS_DIR=".git/hooks"

echo "Copia degli script nella directory $HOOKS_DIR..."
cp "$DIR/commit_ai.py" "$HOOKS_DIR/commit_ai.py"
cp "$DIR/prepare-commit-msg" "$HOOKS_DIR/prepare-commit-msg"

chmod +x "$HOOKS_DIR/commit_ai.py"
chmod +x "$HOOKS_DIR/prepare-commit-msg"

echo "Installazione completata con successo!"
echo "Ora quando esegui 'git commit', il messaggio verrà generato in automatico tramite Ollama."
