#!/bin/bash

# ── Local-Commit-AI — Installer / Uninstaller ─────────────────────
# Uso:
#   ./install.sh              → Installa l'hook nel repository corrente
#   ./install.sh --uninstall  → Rimuove l'hook dal repository corrente

set -e

# ── Colori ─────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HOOKS_DIR=".git/hooks"

# ── Uninstall ──────────────────────────────────────────────────────
if [ "$1" = "--uninstall" ]; then
    echo -e "${CYAN}Disinstallazione di Local-Commit-AI...${NC}"

    if [ ! -d ".git" ]; then
        echo -e "${RED}Errore: questa directory non è la root di un repository git.${NC}"
        exit 1
    fi

    if [ -f "$HOOKS_DIR/commit_ai.py" ]; then
        rm "$HOOKS_DIR/commit_ai.py"
        echo -e "${GREEN}✓${NC} Rimosso $HOOKS_DIR/commit_ai.py"
    fi

    if [ -f "$HOOKS_DIR/prepare-commit-msg" ]; then
        rm "$HOOKS_DIR/prepare-commit-msg"
        echo -e "${GREEN}✓${NC} Rimosso $HOOKS_DIR/prepare-commit-msg"
    fi

    echo -e "${GREEN}Disinstallazione completata!${NC}"
    echo "L'hook AI non verrà più eseguito durante i commit."
    exit 0
fi

# ── Install ────────────────────────────────────────────────────────
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     Local-Commit-AI — Installazione   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

# Verifica git
if ! command -v git &> /dev/null; then
    echo -e "${RED}✗ git non è installato.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} git trovato"

# Verifica repository
if [ ! -d ".git" ]; then
    echo -e "${RED}✗ Questa directory non è la root di un repository git.${NC}"
    echo "  Esegui questo script dalla root del tuo repository."
    exit 1
fi
echo -e "${GREEN}✓${NC} Repository git rilevato"

# Verifica ollama
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}✗ ollama non è installato o non è nel PATH.${NC}"
    echo "  Installa ollama da https://ollama.ai/"
    exit 1
fi
echo -e "${GREEN}✓${NC} ollama trovato"

# Verifica python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ python3 non è installato o non è nel PATH.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} python3 trovato ($(python3 --version 2>&1))"

echo ""

# Pull del modello
MODEL_NAME="qwen2.5-coder:1.5b"
echo -e "${YELLOW}Scaricamento modello '$MODEL_NAME'...${NC}"
ollama pull $MODEL_NAME
echo -e "${GREEN}✓${NC} Modello pronto"

echo ""

# Backup hook esistente
if [ -f "$HOOKS_DIR/prepare-commit-msg" ]; then
    BACKUP="$HOOKS_DIR/prepare-commit-msg.backup.$(date +%s)"
    cp "$HOOKS_DIR/prepare-commit-msg" "$BACKUP"
    echo -e "${YELLOW}⚠ Hook esistente salvato in: $BACKUP${NC}"
fi

# Copia degli script
echo "Installazione hook..."
cp "$DIR/commit_ai.py" "$HOOKS_DIR/commit_ai.py"
cp "$DIR/prepare-commit-msg" "$HOOKS_DIR/prepare-commit-msg"

chmod +x "$HOOKS_DIR/commit_ai.py"
chmod +x "$HOOKS_DIR/prepare-commit-msg"

echo -e "${GREEN}✓${NC} Hook installato in $HOOKS_DIR/"

# Crea la directory di log
mkdir -p "$HOME/.commit-ai"
echo -e "${GREEN}✓${NC} Directory di log creata (~/.commit-ai/)"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      Installazione completata! ✅      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo "Comandi utili:"
echo "  git commit                          → commit con messaggio AI"
echo "  SKIP_COMMIT_AI=1 git commit         → commit senza AI"
echo "  ./install.sh --uninstall            → rimuovi l'hook"
echo ""
echo "Configurazione (opzionale):"
echo "  Crea un file .commit-ai.conf nella root del repository."
echo "  Vedi il README per i dettagli."
