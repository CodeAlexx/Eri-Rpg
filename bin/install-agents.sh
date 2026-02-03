#!/bin/bash
# Install ERI agent specifications to Claude Code
# Creates symlinks from ~/.claude/agents/ to project agents

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
AGENTS_SRC="$PROJECT_ROOT/erirpg/agents"
AGENTS_DST="$HOME/.claude/agents"

# Ensure destination exists
mkdir -p "$AGENTS_DST"

# Create symlinks for all eri-*.md files
for f in "$AGENTS_SRC"/eri-*.md; do
  [ -f "$f" ] || continue
  name=$(basename "$f")
  target="$AGENTS_DST/$name"

  # Remove existing (file or symlink)
  rm -f "$target"

  # Create symlink
  ln -s "$f" "$target"
  echo "Linked: $name"
done

echo ""
echo "Agent specifications installed to $AGENTS_DST"
echo "Changes to project files are now automatically reflected."
