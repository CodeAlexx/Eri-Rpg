#!/bin/bash
# Basic auto-fix for safe repairs
# Usage: basic-fix.sh

echo "Running basic fixes..."

# Fix 1: Remove stale EXECUTION_STATE.json
if [ -f .planning/EXECUTION_STATE.json ]; then
  # Check if it's older than 1 hour
  if [ "$(find .planning/EXECUTION_STATE.json -mmin +60 2>/dev/null)" ]; then
    echo "  Removing stale EXECUTION_STATE.json (>1 hour old)"
    rm .planning/EXECUTION_STATE.json
  else
    echo "  EXECUTION_STATE.json exists but is recent - skipping"
  fi
else
  echo "  No EXECUTION_STATE.json to clean"
fi

# Fix 2: Update global state to current project
if [ -d .planning ]; then
  CWD=$(pwd)
  PROJECT_NAME=$(basename "$CWD")

  mkdir -p ~/.eri-rpg

  if [ -f ~/.eri-rpg/state.json ]; then
    # Update existing state
    CURRENT_TARGET=$(python3 -c "import json; print(json.load(open('$HOME/.eri-rpg/state.json')).get('target_project_path', ''))" 2>/dev/null)

    if [ "$CURRENT_TARGET" != "$CWD" ]; then
      echo "  Updating global state: $CURRENT_TARGET → $CWD"
      python3 -c "
import json
with open('$HOME/.eri-rpg/state.json', 'r') as f:
    state = json.load(f)
state['target_project_path'] = '$CWD'
state['target_project'] = '$PROJECT_NAME'
with open('$HOME/.eri-rpg/state.json', 'w') as f:
    json.dump(state, f, indent=2)
"
    else
      echo "  Global state already points to current directory"
    fi
  else
    # Create new state
    echo "  Creating new global state"
    echo "{\"target_project_path\": \"$CWD\", \"target_project\": \"$PROJECT_NAME\"}" > ~/.eri-rpg/state.json
  fi
else
  echo "  No .planning/ directory - cannot update global state"
fi

echo ""
echo "Basic fixes complete."
