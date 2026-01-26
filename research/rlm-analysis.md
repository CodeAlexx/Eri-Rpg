# RLM Analysis

Analysis of [Recursive Language Models](https://github.com/alexzhang13/rlm) for EriRPG design.

## Core Concept

**Key Insight:** Context is a VARIABLE, not prompt stuffing.

Traditional approach:
```python
llm.completion(prompt + entire_codebase)  # 500K tokens crammed in
```

RLM approach:
```python
rlm.completion(prompt)  # Context available as `context` variable
# LLM can programmatically access, chunk, query sub-LLMs
```

## How It Works

### REPL Environment

Code executes in a sandboxed Python environment with:
- `context` variable - the data being analyzed
- `llm_query(prompt)` - recursive sub-LLM calls
- `llm_query_batched(prompts)` - parallel sub-LLM calls
- `print()` - see intermediate results

### Execution Flow

```python
rlm = RLM(backend="openai", max_iterations=30)

# Context loaded as variable, not prompt
result = rlm.completion("Summarize the key decisions in this codebase")

# Internally:
# 1. Context loaded into REPL as `context` variable
# 2. LLM generates code to analyze context
# 3. Code runs, may call sub-LLMs
# 4. Results printed, LLM continues reasoning
# 5. Loop until FINAL() or max iterations
```

### Code Structure

```
rlm/
├── core/
│   ├── rlm.py          # Main RLM class, completion loop
│   ├── lm_handler.py   # Socket server for sub-LLM calls
│   └── types.py        # RLMIteration, REPLResult, etc.
├── environments/
│   ├── base_env.py     # Abstract environment interface
│   ├── local_repl.py   # exec() in sandboxed namespace
│   ├── docker_repl.py  # Docker container execution
│   └── modal_repl.py   # Cloud sandbox execution
├── clients/
│   ├── openai.py       # OpenAI client
│   ├── anthropic.py    # Anthropic client
│   └── litellm.py      # LiteLLM router
└── utils/
    ├── prompts.py      # System prompts
    └── parsing.py      # Extract code blocks, final answers
```

### System Prompt (Condensed)

```
You have access to:
1. `context` - extremely important information
2. `llm_query(prompt)` - query sub-LLM (~500K context)
3. `llm_query_batched(prompts)` - parallel queries

Strategies:
- Chunk context, query per chunk
- Use buffers to accumulate answers
- Query batched for parallel processing

When done, use FINAL(answer) or FINAL_VAR(variable_name)
```

## Chunking Strategies

### 1. Sequential Chunking
```python
for i, section in enumerate(context):
    buffer = llm_query(f"Analyze section {i}: {section}")
    print(buffer)
final = llm_query(f"Synthesize: {buffers}")
```

### 2. Parallel Chunking
```python
chunks = [context[i:i+chunk_size] for i in range(0, len(context), chunk_size)]
prompts = [f"Analyze: {chunk}" for chunk in chunks]
answers = llm_query_batched(prompts)  # Concurrent!
```

### 3. Structure-Aware Chunking
```python
sections = re.split(r'### (.+)', context)
for header, content in zip(sections[::2], sections[1::2]):
    summary = llm_query(f"Summarize {header}: {content}")
```

## Useful for EriRPG

### Yes - Adopt These Ideas

1. **Context as variable**
   - Don't stuff entire codebase in prompt
   - Load as structured data
   - Query programmatically

2. **Recursive sub-calls**
   - Chunk and query pattern
   - Accumulate in buffers
   - Synthesize at end

3. **Batched queries**
   - Parallel processing for independent chunks
   - Much faster than sequential

4. **Structured final answer**
   - FINAL() and FINAL_VAR()
   - Clear termination

### No - Don't Need These

1. **General REPL execution**
   - Too open-ended for our use case
   - We have specific operations (index, find, extract)

2. **Sandbox environments**
   - Docker/Modal overkill
   - We're reading local files, not running untrusted code

3. **LLM-based chunking decisions**
   - Expensive - LLM decides how to chunk
   - We can use deterministic chunking (AST-based)

## Key Takeaway

RLM's insight: **Don't load everything, load what you need programmatically**

For EriRPG:
- Index produces a graph (summaries, not full code)
- Find queries the graph (small token cost)
- Extract loads specific modules (only what's needed)
- Context generation is <5K tokens, not 50K

We get the benefit (token efficiency) without the complexity (LLM-driven chunking, recursive sub-calls).
