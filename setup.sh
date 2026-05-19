#!/usr/bin/env bash
# Setup Claude Code global config on a new machine
# Usage: ./setup.sh

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

echo "Setting up Claude Code config..."
echo "  Source: $DOTFILES_DIR"
echo "  Target: $CLAUDE_DIR"
echo ""

mkdir -p "$CLAUDE_DIR"

# Copy config directories
for dir in agents commands rules skills hooks; do
  if [ -d "$DOTFILES_DIR/$dir" ]; then
    rm -rf "$CLAUDE_DIR/$dir"
    cp -r "$DOTFILES_DIR/$dir" "$CLAUDE_DIR/$dir"
    echo "  copied $dir/"
  fi
done

# Generate settings.json from template
if [ -f "$DOTFILES_DIR/settings.json.template" ]; then
  sed "s|__HOME__|$HOME|g" "$DOTFILES_DIR/settings.json.template" > "$CLAUDE_DIR/settings.json"
  echo "  generated settings.json"
fi

# Merge mcpServers into ~/.claude.json
if [ -f "$DOTFILES_DIR/mcp.json" ]; then
  python3 - "$DOTFILES_DIR/mcp.json" "$HOME/.claude.json" <<'PYEOF'
import json, sys, os

mcp_path = sys.argv[1]
claude_path = sys.argv[2]

with open(mcp_path) as f:
    mcp = json.load(f)

claude = {}
if os.path.exists(claude_path):
    with open(claude_path) as f:
        claude = json.load(f)

claude["mcpServers"] = mcp.get("mcpServers", {})

with open(claude_path, "w") as f:
    json.dump(claude, f, indent=2)
    f.write("\n")

print("  merged mcpServers into ~/.claude.json")
PYEOF
fi

echo ""
echo "Done. Claude Code config installed to $CLAUDE_DIR"
