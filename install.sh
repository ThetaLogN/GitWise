#!/bin/bash

# ── GitWise — Installer / Uninstaller ─────────────────────
# Usage:
#   ./install.sh              → Install the hook in the current repository
#   ./install.sh --uninstall  → Remove the hook from the current repository

set -e

# ── Colors ─────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HOOKS_DIR=".git/hooks"

# ── Uninstall ──────────────────────────────────────────────────────
if [ "$1" = "--uninstall" ]; then
    echo -e "${CYAN}Uninstalling GitWise...${NC}"

    if [ ! -d ".git" ]; then
        echo -e "${RED}Error: this directory is not a git repository root.${NC}"
        exit 1
    fi

    if [ -f "$HOOKS_DIR/commit_ai.py" ]; then
        rm "$HOOKS_DIR/commit_ai.py"
        echo -e "${GREEN}✓${NC} Removed $HOOKS_DIR/commit_ai.py"
    fi

    if [ -f "$HOOKS_DIR/prepare-commit-msg" ]; then
        rm "$HOOKS_DIR/prepare-commit-msg"
        echo -e "${GREEN}✓${NC} Removed $HOOKS_DIR/prepare-commit-msg"
    fi

    echo -e "${GREEN}Uninstallation complete!${NC}"
    echo "The AI hook will no longer run during commits."
    exit 0
fi

# ── Install ────────────────────────────────────────────────────────
echo -e "${CYAN}╔════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      GitWise — Installation      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
echo ""

# Check git
if ! command -v git &> /dev/null; then
    echo -e "${RED}✗ git is not installed.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} git found"

# Check repository
if [ ! -d ".git" ]; then
    echo -e "${RED}✗ This directory is not a git repository root.${NC}"
    echo "  Run this script from your repository root."
    exit 1
fi
echo -e "${GREEN}✓${NC} Git repository detected"

# Check ollama
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}✗ ollama is not installed or not in PATH.${NC}"
    echo "  Install ollama from https://ollama.ai/"
    exit 1
fi
echo -e "${GREEN}✓${NC} ollama found"

# Check python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ python3 is not installed or not in PATH.${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} python3 found ($(python3 --version 2>&1))"

echo ""

# Pull model
MODEL_NAME="qwen2.5-coder:7b"
echo -e "${YELLOW}Downloading model '$MODEL_NAME'...${NC}"
ollama pull $MODEL_NAME
echo -e "${GREEN}✓${NC} Model ready"

echo ""

# Backup existing hook
if [ -f "$HOOKS_DIR/prepare-commit-msg" ]; then
    BACKUP="$HOOKS_DIR/prepare-commit-msg.backup.$(date +%s)"
    cp "$HOOKS_DIR/prepare-commit-msg" "$BACKUP"
    echo -e "${YELLOW}⚠ Existing hook saved to: $BACKUP${NC}"
fi

REPO_RAW_URL="https://raw.githubusercontent.com/ThetaLogN/GitWise/main"

# Copy or download scripts
echo "Installing hook..."

if [ -f "$DIR/commit_ai.py" ]; then
    cp "$DIR/commit_ai.py" "$HOOKS_DIR/commit_ai.py"
else
    curl -sSL "$REPO_RAW_URL/commit_ai.py" -o "$HOOKS_DIR/commit_ai.py"
fi

if [ -f "$DIR/prepare-commit-msg" ]; then
    cp "$DIR/prepare-commit-msg" "$HOOKS_DIR/prepare-commit-msg"
else
    curl -sSL "$REPO_RAW_URL/prepare-commit-msg" -o "$HOOKS_DIR/prepare-commit-msg"
fi

chmod +x "$HOOKS_DIR/commit_ai.py"
chmod +x "$HOOKS_DIR/prepare-commit-msg"

echo -e "${GREEN}✓${NC} Hook installed in $HOOKS_DIR/"

# Create log directory
mkdir -p "$HOME/.commit-ai"
echo -e "${GREEN}✓${NC} Log directory created (~/.commit-ai/)"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║       Installation Complete! ✅       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo "Useful commands:"
echo "  git commit                          → commit with AI message"
echo "  SKIP_COMMIT_AI=1 git commit         → commit without AI"
echo "  ./install.sh --uninstall            → remove the hook"
echo ""
echo "Configuration (optional):"
echo "  Create a .commit-ai.conf file in the repository root."
echo "  See README for details."
