---
name: coder:map-codebase
description: Analyze existing codebase for brownfield projects
argument-hint: "[focus: tech|arch|quality|concerns|all]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - Task
---

## CLI Integration

**First, call the CLI to get codebase overview:**
```bash
erirpg coder-map-codebase --focus all
```

This returns JSON with:
- `project_type`: Detected type (node, rust, python, go, unknown)
- `file_count`: Number of source files found
- `focus`: Focus area (tech, arch, quality, concerns, all)
- `has_mapping`: Whether .planning/codebase/ already exists
- `existing_files`: Existing mapping files if any
- `directories`: Top-level directories in project

Use this data to determine mapping scope and strategy.

---

<command-name>coder:map-codebase</command-name>

<objective>
Analyze an EXISTING codebase (brownfield) to understand it before applying eri-coder workflow.
Creates .planning/codebase/ documentation for informed planning.

Essential for:
- Adding features to existing projects
- Understanding inherited codebases
- Preparing for major refactors
- Onboarding to a new project

Use case flow:
```
cd ~/some-existing-project
/coder:map-codebase
# Analyzes everything, produces codebase/*.md files
/coder:new-project my-feature "add authentication"
# Uses codebase context to plan feature that fits existing architecture
```
</objective>

<context>
Focus: $ARGUMENTS (default: all)

| Focus | What Gets Analyzed | Output Files |
|-------|-------------------|--------------|
| tech | Languages, frameworks, dependencies, build tools | STACK.md, INTEGRATIONS.md |
| arch | Architecture patterns, modules, data flow | ARCHITECTURE.md, STRUCTURE.md |
| quality | Coding conventions, tests, patterns | CONVENTIONS.md, TESTING.md |
| concerns | Tech debt, security, performance issues | CONCERNS.md |
| all | Everything above + synthesis | All + SUMMARY.md |

Output location: `.planning/codebase/`
</context>

<process>

## Step 1: Validate Environment

```bash
# Must be in a project root (has source code)
if [ ! -f "package.json" ] && [ ! -f "Cargo.toml" ] && [ ! -f "pyproject.toml" ] && [ ! -f "go.mod" ] && [ ! -f "setup.py" ] && [ ! -f "Makefile" ]; then
  echo "WARNING: No recognizable project files found. Are you in the project root?"
fi

# Create output directory
mkdir -p .planning/codebase

# Check for existing mapping
if [ -f ".planning/codebase/SUMMARY.md" ]; then
  echo "Previous mapping found. Will update."
fi
```

## Step 2: Initial Project Detection

Gather basic info for all focus areas:

```bash
# Detect project type
PROJECT_TYPE="unknown"
[ -f "package.json" ] && PROJECT_TYPE="node"
[ -f "Cargo.toml" ] && PROJECT_TYPE="rust"
[ -f "pyproject.toml" ] && PROJECT_TYPE="python"
[ -f "go.mod" ] && PROJECT_TYPE="go"

# Count files
find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.rs" -o -name "*.go" \) | grep -v node_modules | grep -v .venv | grep -v target | wc -l

# Get LOC estimate
wc -l $(find . -type f \( -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.rs" -o -name "*.go" \) | grep -v node_modules | grep -v .venv | head -100) 2>/dev/null | tail -1
```

## Step 3: Spawn Mapper Agents by Focus

Based on $ARGUMENTS, spawn eri-codebase-mapper agents.

### For focus=tech (or all):
Spawn Task agent with `subagent_type: eri-codebase-mapper`:
```
Focus: tech
Analyze: Languages, frameworks, dependencies, build tools, integrations
Output: .planning/codebase/STACK.md and .planning/codebase/INTEGRATIONS.md
```

### For focus=arch (or all):
Spawn Task agent with `subagent_type: eri-codebase-mapper`:
```
Focus: arch
Analyze: Architecture patterns, module structure, data flow, entry points
Output: .planning/codebase/ARCHITECTURE.md and .planning/codebase/STRUCTURE.md
```

### For focus=quality (or all):
Spawn Task agent with `subagent_type: eri-codebase-mapper`:
```
Focus: quality
Analyze: Coding conventions, test setup, patterns, error handling
Output: .planning/codebase/CONVENTIONS.md and .planning/codebase/TESTING.md
```

### For focus=concerns (or all):
Spawn Task agent with `subagent_type: eri-codebase-mapper`:
```
Focus: concerns
Analyze: Technical debt, security issues, performance problems, outdated deps
Output: .planning/codebase/CONCERNS.md
```

**Parallelization:** If focus=all, spawn all 4 agents in parallel using multiple Task tool calls in single message.

## Step 4: Synthesize Findings (if focus=all)

After all agents complete, create `.planning/codebase/SUMMARY.md`:

```markdown
# Codebase Analysis Summary

## Quick Facts
| Metric | Value |
|--------|-------|
| Language | {primary language} {version} |
| Framework | {framework} {version} |
| Size | {files} files, ~{loc} lines |
| Test Coverage | {percent}% (if determinable) |

## Architecture Style
{One paragraph describing how this codebase is organized}

## Key Strengths
- {strength 1 - something done well}
- {strength 2 - good patterns}
- {strength 3 - solid foundations}

## Key Concerns
| Concern | Severity | Location |
|---------|----------|----------|
| {concern} | {High/Med/Low} | `{path}` |

## Recommendations for New Development

### Do Follow
- {existing pattern to follow}
- {convention to maintain}

### Avoid
- {antipattern in codebase}
- {deprecated approach}

## Files to Understand First
To work on this codebase, read these files first:
1. `{path}` - {why important}
2. `{path}` - {why important}
3. `{path}` - {why important}

## Integration Points for New Features
| To Add | Integrate With | Example |
|--------|----------------|---------|
| New API endpoint | `{router file}` | See `{existing endpoint}` |
| New component | `{components dir}` | Follow `{example}` |
| New service | `{services dir}` | Follow `{pattern}` |
```

## Step 5: Index to Knowledge Graph (Optional)

If EriRPG is initialized:
```bash
# Check if eri-rpg is available
if command -v eri-rpg &> /dev/null; then
  # Index findings into knowledge graph
  eri-rpg index . --update
  echo "Codebase mapping indexed to knowledge graph"
fi
```

This makes codebase knowledge recallable via `/eri:recall codebase`, `/eri:recall stack`, etc.

## Step 6: Commit Documentation

```bash
git add .planning/codebase/
git commit -m "docs: map existing codebase

Focus: ${FOCUS:-all}
Files analyzed: $(find . -type f \( -name '*.py' -o -name '*.ts' -o -name '*.js' -o -name '*.rs' \) | grep -v node_modules | wc -l)

Generated:
$(ls .planning/codebase/)"
```

</process>

<agent-instructions>
When spawning eri-codebase-mapper agents:

1. Pass the focus area explicitly in the prompt
2. Include project path context
3. Wait for all agents to complete before synthesizing
4. Model: Use "sonnet" for mapping agents (good balance of speed and quality)

Example Task call:
```
Task(
  description="Map codebase tech stack",
  prompt="Focus: tech\nProject: {cwd}\nAnalyze the technology stack and integrations.\nWrite output to .planning/codebase/STACK.md and .planning/codebase/INTEGRATIONS.md",
  subagent_type="eri-codebase-mapper",
  model="sonnet"
)
```

For parallel execution with focus=all:
- Spawn all 4 focus agents in ONE message (multiple Task calls)
- Each agent works independently
- After all complete, YOU synthesize SUMMARY.md (don't spawn another agent)
</agent-instructions>

<completion>
## On Completion

### 1. Verify Committed

```bash
git status --short .planning/codebase/
```

### 2. Update STATE.md

```markdown
## Last Action
Completed map-codebase
- Focus: {focus}
- Files analyzed: {count}
- Documentation: .planning/codebase/

## Codebase Summary
- Type: {project_type}
- Size: {files} files, ~{loc} lines
- Key concerns: {count}

## Next Step
Run `/coder:add-feature` to add features that fit existing architecture
```

### 3. Update Global State

```bash
python3 -m erirpg.cli switch "$(pwd)" 2>/dev/null || true
```

### 4. Present Next Steps

```
╔════════════════════════════════════════════════════════════════╗
║  ✓ CODEBASE MAPPED                                             ║
╠════════════════════════════════════════════════════════════════╣
║  Type: {project_type}                                          ║
║  Size: {files} files, ~{loc} lines                             ║
║  Focus: {focus}                                                ║
║  Location: .planning/codebase/                                 ║
╚════════════════════════════════════════════════════════════════╝

## ▶ NEXT: Add features or explore

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Type:  /clear
2. Then:  /coder:init
3. Then:  /coder:add-feature "<feature-name>" "<description>"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Or view mapping: cat .planning/codebase/SUMMARY.md
```
</completion>

<integration>
This command integrates with:
- `/coder:new-project` - Reads .planning/codebase/* when brownfield detected
- `/coder:plan-phase` - Planner uses codebase context for informed decisions
- `/eri:recall` - Codebase knowledge indexed and recallable
- `/eri:learn` - Can manually add additional learnings about specific modules
</integration>
