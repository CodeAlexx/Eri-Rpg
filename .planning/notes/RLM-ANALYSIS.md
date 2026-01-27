# RLM (Recursive Language Models) Analysis

**Repository**: https://github.com/alexzhang13/rlm
**Source**: MIT OASYS Lab
**Analyzed**: 2026-01-26

## Overview

RLM is an inference library enabling LLMs to handle near-infinite context through recursive self-invocation. Models can programmatically examine, decompose, and recursively call themselves via a REPL environment.

## Architecture

```
rlm/
├── core/
│   ├── rlm.py          # Main RLM class - recursive completion loop
│   ├── lm_handler.py   # Multi-threaded TCP server wrapping LM clients
│   ├── types.py        # RLMIteration, CodeBlock, REPLResult
│   └── comms_utils.py  # Socket protocol (4-byte length prefix + JSON)
├── clients/
│   ├── base_lm.py      # Abstract BaseLM interface
│   ├── openai.py, anthropic.py, portkey.py, litellm.py, gemini.py
├── environments/
│   ├── base_env.py     # NonIsolatedEnv / IsolatedEnv base classes
│   ├── local_repl.py   # Local Python execution
│   ├── docker_repl.py  # Docker sandbox
│   ├── modal_repl.py   # Modal cloud (HTTP broker pattern)
│   └── prime_repl.py   # Prime Intellect sandbox
├── logger/             # Trajectory logging as .jsonl
└── visualizer/         # Node.js web UI for execution traces
```

## Core Loop (from rlm/core/rlm.py)

```python
for i in range(max_iterations):
    response = lm_handler.completion(prompt)
    code_blocks = find_code_blocks(response)

    for code in code_blocks:
        result = environment.execute_code(code)

    final_answer = find_final_answer(response)
    if final_answer:
        return RLMChatCompletion(...)

    message_history.extend(format_iteration(iteration))
```

## Concept Comparison: RLM vs EriRPG

### Already Similar

| RLM Concept | EriRPG Equivalent | Notes |
|-------------|-------------------|-------|
| `RLMIteration` loop | Step execution loop | Both iterate until completion |
| `message_history` | `RunState` | Accumulated execution context |
| `REPLResult` | `preflight()` + `verify_step()` | Execution feedback |
| `RLMLogger` | `Decision` + `RunSummary` | Execution tracing |
| `find_final_answer()` | `is_complete()` | Termination check |
| `max_iterations` limit | Spec step count | Bounded execution |

### RLM Has, EriRPG Doesn't

1. **Trajectory Visualizer**
   - Web UI for debugging execution paths
   - Could be valuable for complex multi-step runs
   - EriRPG only has CLI `format_run()` output

2. **Multi-Provider BaseLM Abstraction**
   - Clean interface for OpenAI/Anthropic/etc
   - EriRPG doesn't manage LLM calls (Claude Code does)

3. **True Sandboxed Environments**
   - Docker, Modal, Prime Intellect isolation
   - EriRPG uses Python hooks, not process isolation

4. **Socket Protocol for Sub-Calls**
   - `LMHandler` as TCP server
   - Enables code in sandbox to call LLM
   - Not needed for EriRPG's model

### Not Applicable to EriRPG

1. **Recursive Sub-Calls (`llm_query()`)**
   - RLM's core innovation
   - LLM spawns child LLM calls autonomously
   - EriRPG is human-in-the-loop, not autonomous

2. **REPL Arbitrary Code Execution**
   - RLM executes any code the LLM generates
   - EriRPG orchestrates structured file edits

3. **Depth-Based Recursion (`max_depth`)**
   - RLM can nest recursive calls
   - EriRPG has flat step execution

## Philosophical Difference

**RLM**: Replaces human reasoning with recursive LLM decomposition.
The LLM autonomously breaks down problems, executes code, and recurses.

**EriRPG**: Augments human reasoning with structured workflows.
Human provides goal, system generates spec, human verifies each step.

## Potential Borrowing

### Worth Considering

1. **Trajectory Visualizer Concept**
   - Web UI showing run history, decisions, file changes
   - Would help debug complex multi-step runs
   - Could integrate with existing RunSummary data

2. **Structured Logging Format**
   - RLM's `.jsonl` trajectory format is clean
   - EriRPG's RunSummary is similar but CLI-focused

### Not Worth It

1. **LMHandler / Socket Protocol**
   - Unnecessary complexity for EriRPG
   - Claude Code already handles LLM calls

2. **Environment Abstraction**
   - EriRPG doesn't need Docker/Modal isolation
   - Hooks provide sufficient guardrails

3. **Recursive Patterns**
   - Would fundamentally change EriRPG's model
   - Human-in-the-loop is the point

## Conclusion

EriRPG and RLM share iterative execution patterns (likely from similar design principles), but serve different purposes. RLM enables autonomous LLM reasoning; EriRPG enables structured human-AI collaboration.

The trajectory visualizer is the most portable concept - a web UI for viewing run history could improve debugging experience significantly.
