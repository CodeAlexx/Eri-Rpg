#!/bin/bash
# Check clone-behavior progress
# Usage: check-progress.sh

if [ -f clone-state.json ]; then
  echo "## Clone Progress"
  python3 -c "
import json
with open('clone-state.json') as f:
    state = json.load(f)

phase = state.get('current_phase', 'unknown')
print(f'Current phase: {phase}')

if 'progress' in state:
    for p, data in state['progress'].items():
        status = data.get('status', 'unknown')
        print(f'  {p}: {status}')
        if 'modules' in data:
            for m in data['modules']:
                mstatus = '✅' if m['status'] == 'pass' else '❌'
                print(f'    {mstatus} {m[\"name\"]}: {m[\"passed\"]}/{m[\"checks\"]} checks')
"
else
  echo "No clone-state.json found"
  echo "Run /coder:clone-behavior to start"
fi
