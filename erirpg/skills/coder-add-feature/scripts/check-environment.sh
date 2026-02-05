#!/bin/bash
# Check environment for add-feature
# Usage: check-environment.sh

echo "## Environment Check"

# Check project root
if [ -f "package.json" ]; then
  echo "  ✅ Project type: Node.js (package.json)"
elif [ -f "Cargo.toml" ]; then
  echo "  ✅ Project type: Rust (Cargo.toml)"
elif [ -f "pyproject.toml" ]; then
  echo "  ✅ Project type: Python (pyproject.toml)"
elif [ -f "go.mod" ]; then
  echo "  ✅ Project type: Go (go.mod)"
else
  echo "  ❌ Not in a project root"
  echo "     cd to your project first"
  exit 1
fi

# Check codebase mapping
if [ -d ".planning/codebase" ]; then
  FILE_COUNT=$(ls .planning/codebase/*.md 2>/dev/null | wc -l)
  echo "  ✅ Codebase mapped ($FILE_COUNT files)"
else
  echo "  ⚠️ Codebase not mapped"
  echo "     Run /coder:map-codebase first"
fi

# Check existing features
if [ -d ".planning/features" ]; then
  FEATURE_COUNT=$(ls -d .planning/features/*/ 2>/dev/null | wc -l)
  echo "  ℹ️ Existing features: $FEATURE_COUNT"
else
  echo "  ℹ️ No existing features"
fi

echo ""
echo "Ready for /coder:add-feature"
