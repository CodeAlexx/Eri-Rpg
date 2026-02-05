#!/bin/bash
# Detect research depth from phase goal
# Usage: detect-depth.sh "<phase goal>" [phase_dir]

GOAL="$1"
PHASE_DIR="$2"

if [ -z "$GOAL" ]; then
  echo "Usage: detect-depth.sh '<phase goal>' [phase_dir]"
  exit 1
fi

# Override if RESEARCH.md already exists
if [ -n "$PHASE_DIR" ] && [ -f "${PHASE_DIR}/RESEARCH.md" ]; then
  echo "0"
  echo "RESEARCH.md already exists"
  exit 0
fi

# Level 3 indicators (architectural decisions)
if echo "$GOAL" | grep -qiE "architect|design|system|security|auth|database|schema|model"; then
  echo "3"
  echo "Level 3: Deep Dive - architectural/security/data modeling indicators"
  exit 0
fi

# Level 2 indicators (external integrations)
if echo "$GOAL" | grep -qiE "integrat|api|external|library|choose|select|evaluat|implement.*new"; then
  echo "2"
  echo "Level 2: Standard - external integration/library selection indicators"
  exit 0
fi

# Level 1 indicators (modifications)
if echo "$GOAL" | grep -qiE "add|extend|update|modify"; then
  echo "1"
  echo "Level 1: Quick Verify - modification indicators"
  exit 0
fi

# Level 0 (pure internal)
echo "0"
echo "Level 0: Skip - no external dependencies detected"
