#!/bin/bash
# Validate phase is ready for execution
# Usage: validate-phase.sh <phase-number>

PHASE_NUM="$1"

if [ -z "$PHASE_NUM" ]; then
  echo "Usage: validate-phase.sh <phase-number>"
  exit 1
fi

# Find phase directory
PHASE_DIR=$(ls -d .planning/phases/${PHASE_NUM}-* 2>/dev/null | head -1)

if [ -z "$PHASE_DIR" ]; then
  echo "ERROR: Phase $PHASE_NUM not found"
  exit 1
fi

echo "Phase directory: $PHASE_DIR"

# Count plans
PLAN_COUNT=$(ls -1 "$PHASE_DIR"/*-PLAN.md 2>/dev/null | wc -l)
echo "Plans found: $PLAN_COUNT"

if [ "$PLAN_COUNT" -eq 0 ]; then
  echo "ERROR: No plans found. Run /coder:plan-phase $PHASE_NUM first."
  exit 1
fi

# Count completed plans
SUMMARY_COUNT=$(ls -1 "$PHASE_DIR"/*-SUMMARY.md 2>/dev/null | wc -l)
echo "Completed: $SUMMARY_COUNT"

# Check for EXECUTION_STATE.json
if [ -f ".planning/EXECUTION_STATE.json" ]; then
  echo "WARNING: EXECUTION_STATE.json exists (mid-execution or stale)"
fi

# List plans by wave
echo ""
echo "Plans by wave:"
for plan in "$PHASE_DIR"/*-PLAN.md; do
  wave=$(grep "^wave:" "$plan" 2>/dev/null | cut -d: -f2 | tr -d ' ')
  name=$(basename "$plan")
  summary="${plan/PLAN/SUMMARY}"
  if [ -f "$summary" ]; then
    status="✓"
  else
    status="○"
  fi
  echo "  $status Wave $wave: $name"
done

# Summary
REMAINING=$((PLAN_COUNT - SUMMARY_COUNT))
if [ "$REMAINING" -eq 0 ]; then
  echo ""
  echo "All plans complete. Ready for verification."
else
  echo ""
  echo "$REMAINING plans remaining to execute."
fi
