#!/bin/bash
# Run all doctor health checks
# Usage: run-checks.sh

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  🩺 CODER DOCTOR                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Track overall status
ISSUES=()

# Check 1: Global State
echo "## Check 1: Global State"
if [ -f ~/.eri-rpg/state.json ]; then
  TARGET=$(python3 -c "import json; print(json.load(open('$HOME/.eri-rpg/state.json')).get('target_project_path', 'NONE'))" 2>/dev/null)
  if [ -d "$TARGET/.planning" ]; then
    echo "  ✅ Global state OK (target: $TARGET)"
    GLOBAL_STATUS="OK"
  else
    echo "  ⚠️ target_project_path invalid: $TARGET"
    ISSUES+=("WARN: Global state points to invalid path")
    GLOBAL_STATUS="WARN"
  fi
else
  echo "  ❌ ~/.eri-rpg/state.json missing"
  ISSUES+=("ERROR: Global state file missing")
  GLOBAL_STATUS="ERROR"
fi
echo ""

# Check 2: Project State
echo "## Check 2: Project State"
if [ -d .planning ]; then
  PROJECT_STATUS="OK"
  [ ! -f .planning/PROJECT.md ] && PROJECT_STATUS="WARN" && ISSUES+=("WARN: PROJECT.md missing")
  [ ! -f .planning/ROADMAP.md ] && PROJECT_STATUS="ERROR" && ISSUES+=("CRITICAL: ROADMAP.md missing")
  [ ! -f .planning/STATE.md ] && PROJECT_STATUS="WARN" && ISSUES+=("WARN: STATE.md missing")

  PHASE_COUNT=$(ls -d .planning/phases/*/ 2>/dev/null | wc -l)
  echo "  .planning/ exists with $PHASE_COUNT phases"
  echo "  Status: $PROJECT_STATUS"
else
  echo "  ❌ No .planning/ directory"
  ISSUES+=("ERROR: Not a coder project")
  PROJECT_STATUS="ERROR"
fi
echo ""

# Check 3: Execution State
echo "## Check 3: Execution State"
if [ -f .planning/EXECUTION_STATE.json ]; then
  PHASE=$(python3 -c "import json; print(json.load(open('.planning/EXECUTION_STATE.json')).get('phase', '?'))" 2>/dev/null)
  echo "  ACTIVE (phase $PHASE)"
  EXEC_STATUS="ACTIVE"
else
  echo "  IDLE (no active execution)"
  EXEC_STATUS="IDLE"
fi
echo ""

# Check 4: Phase Health
echo "## Check 4: Phase Health"
HEALTHY=0
TOTAL=0
for phase_dir in .planning/phases/*/; do
  [ ! -d "$phase_dir" ] && continue
  TOTAL=$((TOTAL + 1))
  phase_name=$(basename "$phase_dir")

  plan_count=$(ls -1 "${phase_dir}"*-PLAN.md 2>/dev/null | wc -l)
  summary_count=$(ls -1 "${phase_dir}"*-SUMMARY.md 2>/dev/null | wc -l)

  if [ -f "${phase_dir}VERIFICATION.md" ]; then
    verify=$(grep "^status:" "${phase_dir}VERIFICATION.md" 2>/dev/null | cut -d: -f2 | tr -d ' ')
  else
    verify="none"
  fi

  if [ "$verify" = "passed" ]; then
    HEALTHY=$((HEALTHY + 1))
    echo "  ✅ $phase_name: complete ($summary_count/$plan_count plans, verified)"
  elif [ "$summary_count" -gt 0 ]; then
    echo "  ⚠️ $phase_name: executed ($summary_count/$plan_count plans, verify: $verify)"
    [ "$verify" = "gaps_found" ] && ISSUES+=("HIGH: $phase_name has verification gaps")
  elif [ "$plan_count" -gt 0 ]; then
    echo "  ○ $phase_name: planned ($plan_count plans, not executed)"
  else
    echo "  ○ $phase_name: pending (no plans)"
  fi
done
echo ""

# Check 5: Research Gaps
echo "## Check 5: Research Gaps"
RESEARCH_GAPS=0
for phase_dir in .planning/phases/*/; do
  [ ! -d "$phase_dir" ] && continue
  phase_name=$(basename "$phase_dir")
  phase_num=$(echo "$phase_name" | cut -d- -f1)

  [ -f "${phase_dir}RESEARCH.md" ] && continue

  goal=$(grep -A 5 "Phase $phase_num" .planning/ROADMAP.md 2>/dev/null)

  if echo "$goal" | grep -qiE "architect|design|system|security|auth|database|schema|integrat|api|external|library"; then
    echo "  ⚠️ $phase_name: needs research (Level 2-3 indicators)"
    RESEARCH_GAPS=$((RESEARCH_GAPS + 1))
    ISSUES+=("MEDIUM: $phase_name missing RESEARCH.md")
  fi
done
[ "$RESEARCH_GAPS" -eq 0 ] && echo "  ✅ No research gaps"
echo ""

# Check 6: Verification Status
echo "## Check 6: Verification Status"
VERIFY_ISSUES=0
for phase_dir in .planning/phases/*/; do
  [ ! -d "$phase_dir" ] && continue

  if [ -f "${phase_dir}VERIFICATION.md" ]; then
    status=$(grep "^status:" "${phase_dir}VERIFICATION.md" 2>/dev/null | cut -d: -f2 | tr -d ' ')
    score=$(grep "^score:" "${phase_dir}VERIFICATION.md" 2>/dev/null | cut -d: -f2 | tr -d ' ')
    phase_name=$(basename "$phase_dir")

    case "$status" in
      passed) echo "  ✅ $phase_name: passed ($score)" ;;
      gaps_found) echo "  ⚠️ $phase_name: gaps_found ($score)"; VERIFY_ISSUES=$((VERIFY_ISSUES + 1)) ;;
      human_needed) echo "  ℹ️ $phase_name: human_needed ($score)"; VERIFY_ISSUES=$((VERIFY_ISSUES + 1)) ;;
    esac
  fi
done
[ "$VERIFY_ISSUES" -eq 0 ] && echo "  ✅ All verifications passed or pending"
echo ""

# Check 7: Hooks
echo "## Check 7: Hooks Installation"
HOOKS_STATUS="OK"
for hook in sessionstart pretooluse posttooluse; do
  if [ -f ~/.claude/hooks/${hook}.py ]; then
    if grep -q "erirpg" ~/.claude/hooks/${hook}.py 2>/dev/null; then
      echo "  ✅ ${hook}.py: installed"
    else
      echo "  ⚠️ ${hook}.py: exists but no erirpg"
      HOOKS_STATUS="WARN"
    fi
  else
    echo "  ❌ ${hook}.py: missing"
    HOOKS_STATUS="WARN"
    ISSUES+=("WARN: Hook ${hook}.py missing")
  fi
done
echo ""

# Check 8: Skills
echo "## Check 8: Skills Installation"
if [ -d ~/.claude/commands/coder ]; then
  SKILL_COUNT=$(ls -1 ~/.claude/commands/coder/*.md 2>/dev/null | wc -l)
  echo "  ✅ $SKILL_COUNT skills installed"
  SKILLS_STATUS="OK"
else
  echo "  ❌ Skills directory missing"
  SKILLS_STATUS="ERROR"
  ISSUES+=("ERROR: Skills not installed")
fi
echo ""

# Summary
echo "═══════════════════════════════════════════════════════════════"
echo "SUMMARY: Global=$GLOBAL_STATUS Project=$PROJECT_STATUS Exec=$EXEC_STATUS"
echo "         Phases=$HEALTHY/$TOTAL healthy, Research gaps=$RESEARCH_GAPS, Verify issues=$VERIFY_ISSUES"
echo "         Hooks=$HOOKS_STATUS Skills=$SKILLS_STATUS"
echo ""

if [ ${#ISSUES[@]} -gt 0 ]; then
  echo "ISSUES FOUND:"
  for issue in "${ISSUES[@]}"; do
    echo "  - $issue"
  done
fi
