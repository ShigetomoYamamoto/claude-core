#!/usr/bin/env bash
# Setup Claude Code global config on a new machine
# Usage: ./setup.sh

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"

TOTAL_STEPS=4
CURRENT_STEP=0

step() {
  CURRENT_STEP=$((CURRENT_STEP + 1))
  echo ""
  echo "[$CURRENT_STEP/$TOTAL_STEPS] $1"
}

ok()   { echo "  ✓ $1"; }
warn() { echo "  ⚠ $1"; }
fail() {
  echo "  ✗ $1" >&2
  echo "" >&2
  echo "Failed at step $CURRENT_STEP/$TOTAL_STEPS." >&2
  exit 1
}

# Compare two semver-ish versions: returns 0 if $1 >= $2
version_ge() {
  printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# ─────────────────────────────────────────────────────────────
# Step 1: Preflight check
# ─────────────────────────────────────────────────────────────
step "preflight check"

# bash >= 3.2
BASH_VER="$(bash --version | head -n1 | sed -E 's/.* version ([0-9]+\.[0-9]+).*/\1/')"
if version_ge "$BASH_VER" "3.2"; then
  ok "bash $BASH_VER (>= 3.2)"
else
  fail "bash $BASH_VER is too old (>= 3.2 required)"
fi

# python3 >= 3.8
if command -v python3 >/dev/null 2>&1; then
  PY_VER="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if version_ge "$PY_VER" "3.8"; then
    ok "python3 $PY_VER (>= 3.8)"
  else
    fail "python3 $PY_VER is too old (>= 3.8 required)"
  fi
else
  fail "python3 not found (>= 3.8 required). Install via 'brew install python3' or your package manager."
fi

# git >= 2.0
if command -v git >/dev/null 2>&1; then
  GIT_VER="$(git --version | sed -E 's/git version ([0-9]+\.[0-9]+).*/\1/')"
  if version_ge "$GIT_VER" "2.0"; then
    ok "git $GIT_VER (>= 2.0)"
  else
    fail "git $GIT_VER is too old (>= 2.0 required)"
  fi
else
  fail "git not found (>= 2.0 required)"
fi

# docker >= 20.0 (optional but recommended for GitHub MCP)
if command -v docker >/dev/null 2>&1; then
  DOCKER_VER="$(docker --version 2>/dev/null | sed -E 's/Docker version ([0-9]+\.[0-9]+).*/\1/' || echo "0")"
  if version_ge "$DOCKER_VER" "20.0"; then
    ok "docker $DOCKER_VER (>= 20.0)"
  else
    warn "docker $DOCKER_VER is older than 20.0 (GitHub MCP may not work properly)"
  fi
else
  warn "docker not found. GitHub MCP requires Docker. Install via 'brew install --cask docker' (macOS)."
fi

mkdir -p "$CLAUDE_DIR"

# ─────────────────────────────────────────────────────────────
# Step 2: Copy config directories
# ─────────────────────────────────────────────────────────────
step "copying config directories"

for dir in agents commands rules skills hooks workflows; do
  if [ -d "$DOTFILES_DIR/$dir" ]; then
    rm -rf "$CLAUDE_DIR/$dir"
    cp -r "$DOTFILES_DIR/$dir" "$CLAUDE_DIR/$dir"
    ok "$dir/"
  fi
done

# ─────────────────────────────────────────────────────────────
# Step 3: Generate settings.json from template
# ─────────────────────────────────────────────────────────────
step "generating settings.json"

if [ -f "$DOTFILES_DIR/settings.json.template" ]; then
  sed "s|__HOME__|$HOME|g" "$DOTFILES_DIR/settings.json.template" > "$CLAUDE_DIR/settings.json"
  ok "settings.json"
else
  fail "settings.json.template not found"
fi

# ─────────────────────────────────────────────────────────────
# Step 4: Merge mcp.json into ~/.claude.json
# ─────────────────────────────────────────────────────────────
step "merging mcpServers into ~/.claude.json"

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

existing = claude.get("mcpServers", {})
added = []
for key, value in mcp.get("mcpServers", {}).items():
    if key not in existing:
        existing[key] = value
        added.append(key)
claude["mcpServers"] = existing

with open(claude_path, "w") as f:
    json.dump(claude, f, indent=2)
    f.write("\n")

if added:
    print(f"  ✓ added: {', '.join(added)}")
else:
    print("  ✓ already up to date")
PYEOF
else
  warn "mcp.json not found, skipping"
fi

echo ""
echo "Done. Claude Code config installed to $CLAUDE_DIR"
