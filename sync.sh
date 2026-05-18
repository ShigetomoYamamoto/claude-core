#!/usr/bin/env bash
# Sync changes from ~/.claude/ back to this dotfiles repo
# Run this after editing files in ~/.claude/ on this machine
# Usage: ./sync.sh

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "Syncing Claude Code config to dotfiles repo..."
echo "  Source: $CLAUDE_DIR"
echo "  Target: $DOTFILES_DIR"
echo ""

for dir in agents commands rules skills hooks; do
  if [ -d "$CLAUDE_DIR/$dir" ]; then
    rm -rf "$DOTFILES_DIR/$dir"
    cp -r "$CLAUDE_DIR/$dir" "$DOTFILES_DIR/$dir"
    echo "  synced $dir/"
  fi
done

# Update settings.json.template
if [ -f "$CLAUDE_DIR/settings.json" ]; then
  sed "s|$HOME|__HOME__|g" "$CLAUDE_DIR/settings.json" > "$DOTFILES_DIR/settings.json.template"
  echo "  updated settings.json.template"
fi

echo ""
echo "Done. Run 'git diff' to review changes, then commit."
