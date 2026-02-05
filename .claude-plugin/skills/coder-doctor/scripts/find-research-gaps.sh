#!/bin/bash
# Find phases missing research that likely need it
# Usage: find-research-gaps.sh
# Output: phase_num:phase_name for each gap

for phase_dir in .planning/phases/*/; do
  [ ! -d "$phase_dir" ] && continue

  phase_name=$(basename "$phase_dir")
  phase_num=$(echo "$phase_name" | cut -d- -f1)

  # Skip if RESEARCH.md already exists
  [ -f "${phase_dir}RESEARCH.md" ] && continue

  # Get phase goal from ROADMAP.md
  goal=$(grep -A 5 "Phase $phase_num" .planning/ROADMAP.md 2>/dev/null)

  # Check for Level 2-3 indicators that suggest research is needed
  if echo "$goal" | grep -qiE "architect|design|system|security|auth|database|schema|integrat|api|external|library|choose|select|evaluat"; then
    echo "$phase_num:$phase_name"
  fi
done
