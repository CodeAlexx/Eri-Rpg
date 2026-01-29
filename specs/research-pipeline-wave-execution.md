# EriRPG: Research Pipeline + Wave Execution

## Objective

Add research phase and wave execution to EriRPG. Research prevents reinventing wheels. Waves enable parallel execution.

---

## Phase 1: Enhanced Step Dataclass

### Data: AvoidPattern
```python
@dataclass
class AvoidPattern:
    pattern: str   # "Don't use raw SQL"
    reason: str    # "Use repository for testability"
    source: str    # "RESEARCH.md" | "previous_failure"
```

### Data: Step (add fields)
```python
# ADD to existing Step dataclass:
action: str = ""                    # Specific instruction
avoid: List[AvoidPattern] = field(default_factory=list)
done_criteria: str = ""             # Human-observable acceptance
checkpoint_type: Optional[str] = None  # "human-verify" | "decision"
wave: int = 0                       # Set by compute_waves()
```

### Algorithm: compute_waves
```
fn(steps: List[Step]) -> Dict[int, List[Step]]

Input: steps with depends_on field
Output: {wave_num: [steps]}

Logic:
  step_to_wave = {}
  visited = set()        # For circular dep detection

  def get_wave(step_id):
    if step_id in visited and step_id not in step_to_wave:
      raise CircularDependencyError(step_id)
    visited.add(step_id)

    step = steps_by_id[step_id]
    if no depends_on:
      return 1
    else:
      return max(get_wave(dep) for dep in depends_on) + 1

  for step in steps:
    step_to_wave[step.id] = get_wave(step.id)
    step.wave = step_to_wave[step.id]

  Group by wave number, return dict
```

### Data: CircularDependencyError
```python
class CircularDependencyError(Exception):
    def __init__(self, step_id: str):
        self.step_id = step_id
        super().__init__(f"Circular dependency detected at step: {step_id}")
```

### Success Criteria
- [ ] AvoidPattern dataclass exists
- [ ] Step has action, avoid, done_criteria, checkpoint_type, wave
- [ ] compute_waves() returns correct grouping
- [ ] Test: 5 steps with deps → 3 waves
- [ ] Test: circular deps → raises CircularDependencyError

---

## Phase 2: Discovery Level Detection

### Data: Constants
```python
ARCH_KEYWORDS = {"architecture", "redesign", "migrate", "infrastructure", "rewrite"}
INTEGRATION_KEYWORDS = {"oauth", "database", "redis", "docker", "kubernetes", "aws"}
SKIP_KEYWORDS = {"fix bug", "typo", "rename", "format", "lint"}

# Regex for extracting dependencies from goal text
DEP_PATTERN = re.compile(
    r'\b(fastapi|flask|django|sqlalchemy|redis|postgres|postgresql|mysql|'
    r'pytest|docker|aws|oauth|celery|rabbitmq|kafka|mongodb|elasticsearch|'
    r'graphql|grpc|websocket|jwt|stripe|twilio|sendgrid)\b',
    re.IGNORECASE
)
```

### Algorithm: detect_discovery_level
```
fn(goal: str, known_deps: Set[str] = None) -> Tuple[int, str]

Returns: (level, reason)
  0 = skip (internal work)
  1 = quick (single lib lookup)
  2 = standard (choosing options)
  3 = deep (architectural)

Logic:
  goal_lower = goal.lower()
  known_deps = known_deps or set()

  if any(kw in goal_lower for kw in SKIP_KEYWORDS):
    return (0, "skip keyword")

  if any(kw in goal_lower for kw in ARCH_KEYWORDS):
    return (3, "architectural")

  new_deps = extract_deps(goal) - known_deps

  if any(kw in goal_lower for kw in INTEGRATION_KEYWORDS):
    return (2 if new_deps else 1, "integration")

  if len(new_deps) > 2: return (2, "multiple new deps")
  if len(new_deps) == 1: return (1, "single new dep")

  return (0, "no indicators")
```

### Algorithm: extract_deps
```
fn(text: str) -> Set[str]

Logic:
  matches = DEP_PATTERN.findall(text)
  return {m.lower() for m in matches}
```

### Algorithm: is_discretion_answer
```
fn(answer: str) -> bool

DISCRETION_PHRASES = [
    "you decide", "your call", "whatever", "up to you",
    "doesn't matter", "don't care", "either", "any is fine"
]

Logic:
  answer_lower = answer.lower()
  return any(phrase in answer_lower for phrase in DISCRETION_PHRASES)
```

### File: erirpg/discovery.py

### Success Criteria
- [ ] detect_discovery_level("add oauth login") → (2, ...)
- [ ] detect_discovery_level("fix typo") → (0, ...)
- [ ] detect_discovery_level("redesign auth system") → (3, ...)
- [ ] extract_deps("use fastapi and redis") → {"fastapi", "redis"}

---

## Phase 3: Discussion Context Output

### Data: DiscussionContext
```python
@dataclass
class DiscussionContext:
    phase_id: str
    goal: str
    phase_boundary: str           # What this delivers
    decisions: Dict[str, List[str]]  # Category → decisions
    claudes_discretion: List[str]    # "you decide" items
    deferred_ideas: List[str]
    discovery_level: int
    discovery_reason: str
```

### Method: to_markdown
```
Output format:

# Context: {goal}

## Phase Boundary
{phase_boundary}

## Decisions
### {category}
- {decision}

### Claude's Discretion
- {item}

## Deferred
- {idea}

## Research Recommendation
Level: {level} ({reason})
```

### Integration
- Call `build_discussion_context()` at end of discuss
- Save to `.eri-rpg/phases/{id}/CONTEXT.md`
- Also save `context.json` for programmatic access

### Success Criteria
- [ ] CONTEXT.md generated after discuss
- [ ] Discretion answers detected and categorized
- [ ] Discovery level included

---

## Phase 4: Research Pipeline

### Data: LibraryChoice
```python
@dataclass
class LibraryChoice:
    name: str
    version: str
    role: str        # "API framework", "ORM"
    why: str
    alternatives: List[str]
```

### Data: Pitfall
```python
@dataclass
class Pitfall:
    name: str
    why_happens: str
    how_to_avoid: str
```

### Data: ResearchFindings
```python
@dataclass
class ResearchFindings:
    goal: str
    discovery_level: int
    summary: str                    # One sentence
    confidence: str                 # HIGH|MEDIUM|LOW
    stack: List[LibraryChoice]
    pitfalls: List[Pitfall]
    anti_patterns: List[str]
    dont_hand_roll: List[Tuple[str, str]]  # (problem, solution)
    code_examples: List[Tuple[str, str]]   # (title, code)
    sources: List[str]
```

### Method: to_markdown
```
Output RESEARCH.md format:

# Research: {goal}

## Summary
{summary}
**Confidence:** {confidence}

## Stack
| Role | Choice | Why | Rejected |
|------|--------|-----|----------|
| {role} | {name} {version} | {why} | {alternatives} |

## Don't Hand-Roll
| Problem | Use Instead |
|---------|-------------|
| {problem} | {solution} |

## Pitfalls
| Pitfall | Why | Avoidance |
|---------|-----|-----------|
| {name} | {why} | {how} |

## Anti-Patterns
- {pattern}

## Code Examples
### {title}
\`\`\`python
{code}
\`\`\`
```

### Method: to_avoid_patterns
```
fn() -> List[AvoidPattern]

Convert findings to step-injectable patterns:
- anti_patterns → AvoidPattern(pattern, "anti-pattern", "RESEARCH.md")
- dont_hand_roll → AvoidPattern("Don't implement {problem}", "Use {solution}", "RESEARCH.md")
- pitfalls → AvoidPattern(name, how_to_avoid, "RESEARCH.md")
```

### Class: ResearchPhase
```python
class ResearchPhase:
    def __init__(self, project_path: str, goal: str, level: int)

    def execute(self) -> Optional[ResearchFindings]:
        if level == 0: return None
        cached = check_cache()
        if cached: return cached
        findings = do_research()  # CC fills this via tools
        save_cache(findings)
        return findings
```

### Caching
```
Location: .eri-rpg/research_cache.json
Key: md5(goal)[:12]
Structure:
{
  "abc123": {
    "goal": "...",
    "findings": {...},
    "cached_at": "ISO timestamp"
  }
}
```

### CLI: eri-rpg research
```
eri-rpg research <project> [--goal "..."] [--level N]

- Load goal from state if not provided
- Detect level if not forced
- Execute research
- Save to .eri-rpg/phases/{id}/RESEARCH.md
```

### Success Criteria
- [ ] RESEARCH.md generated for level > 0
- [ ] Cached results reused
- [ ] to_avoid_patterns() returns injectable list

---

## Phase 5: Wave Execution

### Data: StepResult
```python
@dataclass
class StepResult:
    step_id: str
    success: bool
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)  # Files created/modified
    duration_ms: int = 0
```

### Data: WaveResult
```python
@dataclass
class WaveResult:
    wave_num: int
    steps: List[str]  # step IDs
    results: List[StepResult]
    success: bool     # All steps succeeded

    @property
    def errors(self) -> List[str]:
        return [r.error for r in self.results if r.error]
```

### Data: WaveCheckpoint
```python
@dataclass
class WaveCheckpoint:
    plan_id: str
    completed_waves: List[int]
    current_wave: int
    step_results: Dict[str, StepResult]  # step_id → result
    started_at: str   # ISO timestamp
    updated_at: str
```

### Algorithm: execute_step
```
fn(step: Step, context: ExecutionContext) -> StepResult

Logic:
  start = time.now()
  try:
    # Show avoid patterns before execution
    for avoid in step.avoid:
      log(f"⚠ Avoid: {avoid.pattern} ({avoid.reason})")

    # Execute the step action
    artifacts = run_action(step.action, context)

    # Verify done criteria
    if not verify_done(step.done_criteria):
      return StepResult(step.id, False, "Done criteria not met", artifacts)

    return StepResult(step.id, True, None, artifacts, elapsed(start))
  except Exception as e:
    return StepResult(step.id, False, str(e), [], elapsed(start))
```

### Class: WaveExecutor
```python
class WaveExecutor:
    checkpoint_file: Path  # .eri-rpg/wave_checkpoint.json

    def __init__(self, plan: Plan, project_path: str):
        self.plan = plan
        self.project_path = Path(project_path)
        self.checkpoint_file = self.project_path / ".eri-rpg" / "wave_checkpoint.json"

    async def execute(self, resume: bool = True) -> ExecutionResult:
        waves = self.plan.waves
        checkpoint = self.load_checkpoint() if resume else None
        start_wave = checkpoint.current_wave if checkpoint else 1

        for wave_num in sorted(waves.keys()):
            if wave_num < start_wave:
                continue  # Already completed

            result = await self.execute_wave(wave_num, waves[wave_num])
            self.save_checkpoint(wave_num, result)

            if not result.success:
                return ExecutionResult(False, f"Wave {wave_num} failed", results)

        self.clear_checkpoint()
        return ExecutionResult(True, "All waves complete", results)

    async def execute_wave(self, num: int, steps: List[Step]) -> WaveResult:
        results = []

        if len(steps) == 1:
            results.append(await self.execute_step(steps[0]))
        elif all(s.parallelizable for s in steps):
            results = await asyncio.gather(*[self.execute_step(s) for s in steps])
        else:
            for s in steps:
                results.append(await self.execute_step(s))

        return WaveResult(num, [s.id for s in steps], results, all(r.success for r in results))

    def save_checkpoint(self, wave_num: int, result: WaveResult):
        checkpoint = WaveCheckpoint(
            plan_id=self.plan.id,
            completed_waves=[w for w in range(1, wave_num + 1) if result.success],
            current_wave=wave_num if not result.success else wave_num + 1,
            step_results={r.step_id: r for r in result.results},
            started_at=self.started_at,
            updated_at=datetime.utcnow().isoformat()
        )
        self.checkpoint_file.write_text(json.dumps(asdict(checkpoint), indent=2))

    def load_checkpoint(self) -> Optional[WaveCheckpoint]:
        if not self.checkpoint_file.exists():
            return None
        data = json.loads(self.checkpoint_file.read_text())
        if data.get("plan_id") != self.plan.id:
            return None  # Different plan, ignore checkpoint
        return WaveCheckpoint(**data)

    def clear_checkpoint(self):
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
```

### Execution Output
```
=== Wave 1/3 ===
Steps: [setup, config]
  [setup] Initialize project structure
    ⚠ Avoid: Don't hand-roll config parsing (use pydantic)
    ✓ Done when: pyproject.toml exists
  [config] Create configuration

Wave 1 complete ✓
Checkpoint saved.

=== Wave 2/3 ===
...
```

### CLI: eri-rpg execute
```
eri-rpg execute <project> [--plan-id ID] [--wave N] [--no-resume]

- Load plan
- Show wave structure
- Execute with parallel support
- Report per-wave results
- Save checkpoint after each wave
```

### Success Criteria
- [ ] Waves execute in order
- [ ] Steps within wave run parallel if parallelizable
- [ ] Failure in wave stops execution
- [ ] Avoid patterns shown before each step
- [ ] Checkpoint saved after each wave
- [ ] Resume from checkpoint works
- [ ] Test: interrupt mid-execution, resume completes remaining waves

---

## Phase 6: Must-Haves Validation

### Data: MustHaves
```python
@dataclass
class MustHaves:
    goal: str
    observable_truths: List[str]   # User sees when done
    required_artifacts: List[str]  # Files that must exist
    required_wiring: List[str]     # Critical connections
    key_links: List[str]           # Fragile parts
```

### Algorithm: validate_plan
```
fn(plan: Plan, must_haves: MustHaves) -> List[str]

Returns list of gaps (empty = valid)

Check:
- All required_artifacts touched by some step
- All observable_truths have matching done_criteria
- All key_links mentioned in step goals/descriptions
```

### Integration
- Derive must_haves after discuss (CC generates from goal)
- Validate plan before execution
- Warn if gaps found

### Success Criteria
- [ ] Gaps detected for incomplete plans
- [ ] No false positives for complete plans

---

## Phase 7: Full Flow Integration

### CLI: eri-rpg work
```
eri-rpg work <project> "goal" [--skip-research] [--skip-validation]

Flow:
1. discuss → CONTEXT.md + discovery_level
2. research → RESEARCH.md (if level > 0)
3. derive must_haves
4. plan → inject avoid patterns from research
5. validate plan against must_haves
6. execute in waves
```

### State Flow
```
.eri-rpg/phases/{id}/
  CONTEXT.md      # From discuss
  context.json
  RESEARCH.md     # From research
  research.json
  PLAN.md         # Human readable
  spec.json       # Machine readable
  SUMMARY.md      # After execution
```

### Success Criteria
- [ ] Full flow runs end-to-end
- [ ] Each phase reads previous phase output
- [ ] Research findings propagate to step.avoid

---

## File Structure

```
erirpg/
  discovery.py      # NEW: detect_discovery_level, is_discretion_answer
  research.py       # NEW: ResearchPhase, ResearchFindings
  must_haves.py     # NEW: MustHaves, validate_plan
  agent/
    plan.py         # EDIT: add AvoidPattern, enhance Step, compute_waves
    run.py          # EDIT: add WaveExecutor, StepResult, WaveResult, WaveCheckpoint
  modes/
    discuss.py      # EDIT: add DiscussionContext, to_markdown
  cli.py            # EDIT: add research, execute, work commands
```

---

## Testing

```bash
# Discovery detection
python3 -c "
from erirpg.discovery import detect_discovery_level, extract_deps
assert detect_discovery_level('add oauth')[0] == 2
assert detect_discovery_level('fix typo')[0] == 0
assert detect_discovery_level('redesign auth')[0] == 3
assert extract_deps('use fastapi and redis') == {'fastapi', 'redis'}
print('✓ discovery')
"

# Wave computation
python3 -c "
from erirpg.agent.plan import Step, compute_waves, CircularDependencyError
steps = [
    Step(id='1', goal='a', description='', depends_on=[]),
    Step(id='2', goal='b', description='', depends_on=[]),
    Step(id='3', goal='c', description='', depends_on=['1']),
    Step(id='4', goal='d', description='', depends_on=['1','2']),
    Step(id='5', goal='e', description='', depends_on=['3','4']),
]
w = compute_waves(steps)
assert list(w.keys()) == [1,2,3]
assert len(w[1]) == 2
print('✓ waves')

# Circular dep detection
circular = [
    Step(id='a', goal='x', description='', depends_on=['b']),
    Step(id='b', goal='y', description='', depends_on=['a']),
]
try:
    compute_waves(circular)
    assert False, 'Should have raised'
except CircularDependencyError:
    pass
print('✓ circular detection')
"

# CLI
eri-rpg research my-proj --goal "add oauth"
eri-rpg work my-proj "implement dashboard"
```

---

## Commit

```bash
git add -A
git commit -m "feat: research pipeline + wave execution

- discovery.py: detect_discovery_level (0-3), extract_deps, is_discretion_answer
- research.py: ResearchFindings, ResearchPhase, RESEARCH.md output
- must_haves.py: MustHaves, validate_plan
- agent/plan.py: AvoidPattern, enhanced Step, compute_waves, CircularDependencyError
- agent/run.py: WaveExecutor, StepResult, WaveResult, WaveCheckpoint
- modes/discuss.py: DiscussionContext, CONTEXT.md output
- cli.py: research, execute, work commands

Features:
- Wave-based parallel execution with checkpoints
- Resumable execution from interruption
- Research caching by goal hash
- Avoid patterns injected into steps from research

Flow: discuss → research → plan (with avoid) → execute (waves)"
```
