#!/bin/bash
# Find phases with verification gaps
# Usage: find-verification-gaps.sh
# Output: phase_num:status for each gap

for phase_dir in .planning/phases/*/; do
  [ ! -d "$phase_dir" ] && continue

  phase_num=$(basename "$phase_dir" | cut -d- -f1)

  # Only check phases that have been executed (have SUMMARY.md files)
  summary_count=$(ls -1 "${phase_dir}"*-SUMMARY.md 2>/dev/null | wc -l)
  [ "$summary_count" -eq 0 ] && continue

  # Check verification status
  if [ ! -f "${phase_dir}VERIFICATION.md" ]; then
    echo "$phase_num:missing"
  else
    status=$(grep "^status:" "${phase_dir}VERIFICATION.md" 2>/dev/null | cut -d: -f2 | tr -d ' ')
    [ "$status" = "gaps_found" ] && echo "$phase_num:gaps_found"
  fi
done
