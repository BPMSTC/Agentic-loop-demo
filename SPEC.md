# Agentic Loop Demo — Project Spec

## Purpose

A teaching demo for software development students showing all 4 levels of agentic loop design,
based on Sydney Runkle's "The Art of Loop Engineering." Students run it from the terminal and
watch each loop execute with clear, narrated output. The code is the lesson — every file is
heavily commented to explain *why*, not just what.

---

## Tech Stack

- **Language:** Python 3.10+
- **LLM API:** Anthropic Python SDK (`anthropic`) — raw API calls, no framework
- **File watching (L3):** `watchdog` library
- **Web search tool (L1):** Simulated via a local `search_tool` function that returns hardcoded
  or file-based results (no real API key required to run the demo). A comment in the code shows
  where a real Brave/Tavily/SerpAPI call would go.
- **Environment:** `.env` file loaded with `python-dotenv`
- **Dependencies:** `requirements.txt`

---

## Project Structure

```
agentic-loop-demo/
├── README.md
├── SPEC.md                   # This file
├── requirements.txt
├── .env.example
├── run_demo.py               # Entry point — runs all 4 levels in sequence with narration
├── level1_agent.py           # L1: Core agent loop
├── level2_verification.py    # L2: Verification loop (wraps L1)
├── level3_event.py           # L3: Event-driven loop (file watcher fires L2 agent)
├── level4_hill_climbing.py   # L4: Hill climbing (trace analysis + prompt improvement)
├── tools.py                  # Shared tool definitions (search, read_file)
├── prompts.py                # System prompts (editable — L4 writes back here)
├── traces/                   # L4 writes JSON trace logs here
│   └── .gitkeep
├── watch_inbox/              # L3 watches this folder for new .txt files
│   └── .gitkeep
└── improved_prompts/         # L4 writes generated prompt improvements here
    └── .gitkeep
```

---

## Level 1 — The Agent Loop (`level1_agent.py`)

**Concept:** The simplest possible agent. An LLM receives a task, calls tools in a loop, and
stops when it decides the task is complete.

**What it does:**
- Receives a research topic string (e.g., `"What is an agentic loop?"`)
- Sends it to Claude with a system prompt and a `search` tool definition
- Parses tool calls from the response, executes them via `tools.py`, feeds results back
- Loops until Claude returns a final text response (no tool call = done)
- Prints each loop iteration clearly so students can see the cycle

**Implementation notes:**
- Use the Messages API with `tools` parameter
- Tool: `search(query: str) -> str` — returns a short paragraph of fake search results
- Tool: `read_file(filename: str) -> str` — reads from `watch_inbox/` (used in L3)
- Stop condition: response has no `tool_use` blocks
- Log the full trace (messages list) to `traces/trace_<timestamp>.json` for L4 to consume
- Use a simple `while True` loop with a max iteration guard (e.g., 10) to prevent runaway loops
- Print a clear separator and iteration count on each loop so students can follow along

**Key teaching point (comment in code):**
> "At its core, an agent is just an LLM in a loop. The model decides when it's done —
> not the programmer."

---

## Level 2 — Verification Loop (`level2_verification.py`)

**Concept:** Wrap the agent loop with an outer grader that checks quality and sends the agent
back if output doesn't meet the bar.

**What it does:**
- Calls `run_agent()` from `level1_agent.py` to get a summary
- Makes a second Claude call — the **grader** — with a rubric prompt asking it to score the
  summary on: completeness, accuracy (relative to the search results used), and clarity
- Grader returns a structured response: `{"pass": true/false, "feedback": "..."}`
  - Use `tool_use` or ask Claude to respond in JSON (use `response_format` or prompt it
    explicitly — whichever is cleaner for students to read)
- If `pass: false`, feed the feedback back into the agent as a new user message and re-run
- Loop until `pass: true` or max retries (3) reached
- Print grader verdict and feedback on each cycle

**Implementation notes:**
- Keep the grader as a separate function `grade_summary(summary, search_results) -> dict`
- The rubric system prompt should be a readable string defined in `prompts.py`
- On each failed verification, show students exactly what feedback the grader gave
- Track total attempts and print a final verdict

**Key teaching point (comment in code):**
> "The agent loop alone will always complete — but 'complete' doesn't mean 'correct.'
> A verification layer separates finishing from quality."

---

## Level 3 — Event-Driven Loop (`level3_event.py`)

**Concept:** The agent doesn't run on-demand — it runs in response to events in your ecosystem.
Here, dropping a file into a folder is the event.

**What it does:**
- Uses the `watchdog` library to watch the `watch_inbox/` directory
- When a new `.txt` file appears, the event handler fires and runs the full L2 agent
  (agent loop + verification) using the file's content as the research topic
- Prints a clear "EVENT RECEIVED" banner when a file is detected
- Writes the final summary to a matching `.summary.txt` file next to the input
- Keeps watching after each run — subsequent file drops fire new runs

**Implementation notes:**
- Use `watchdog.observers.Observer` + a custom `FileCreatedHandler(FileSystemEventHandler)`
- Handler's `on_created` method: read the file, strip whitespace, call `run_verified_agent(topic)`
- Run the observer in the main thread with a `while True: time.sleep(1)` loop and a
  `KeyboardInterrupt` catch for clean shutdown
- Print instructions on startup: "Drop a .txt file into watch_inbox/ to trigger the agent"
- The `.txt` file should contain just the research topic string (one line is fine)
- Add a short debounce (0.5s sleep after detection) to avoid double-fires on some OS file systems

**Key teaching point (comment in code):**
> "Level 3 is where your agent stops being a script you run and starts being a service
> that runs. The trigger is the system, not the user."

---

## Level 4 — Hill Climbing Loop (`level4_hill_climbing.py`)

**Concept:** The agent improves itself. Traces from past runs are analyzed by a meta-agent
that identifies weaknesses in the system prompt and writes a better one.

**What it does:**
- Reads all JSON trace files from `traces/`
- Builds a meta-prompt that includes: the current system prompt (from `prompts.py`), and
  a condensed version of recent traces (last 3, showing the topic, number of loop iterations,
  grader pass/fail, and grader feedback)
- Sends this to Claude with instructions to analyze patterns and suggest an improved system
  prompt for the research agent
- Prints the suggested improvement to the terminal with clear before/after formatting
- Writes the suggested prompt to `improved_prompts/prompt_<timestamp>.txt`
- Does NOT automatically overwrite `prompts.py` — students must review and apply it manually
  (this is intentional: teaches human-in-the-loop oversight)

**Implementation notes:**
- Parse traces: each trace JSON contains `{"topic": str, "messages": [...], "iterations": int,
  "grader_result": {"pass": bool, "feedback": str}}`  — make sure L1/L2 write this format
- Condensed trace format fed to the meta-agent (to keep token count sane):
  ```
  Run 1: Topic="X", Iterations=4, Grader=FAIL, Feedback="Summary lacked specific examples"
  Run 2: Topic="Y", Iterations=2, Grader=PASS, Feedback="Clear and complete"
  ```
- Meta-prompt tells Claude: "Here is the current agent system prompt and recent run traces.
  Identify patterns in failures or inefficiencies. Write an improved system prompt."
- Print output with a clear `--- CURRENT PROMPT ---` / `--- SUGGESTED IMPROVEMENT ---` banner
- Save suggestion to `improved_prompts/` with a timestamp filename

**Key teaching point (comment in code):**
> "Level 4 closes the loop on the loops. The agent's own behavior becomes training signal.
> This is where automated systems start to compound — each generation of runs can make
> the next generation better."

---

## `run_demo.py` — Entry Point

Runs all 4 levels in sequence with printed narration between each, so an instructor can run
one command and walk students through the full progression.

```
$ python run_demo.py
```

Flow:
1. Print a title banner explaining the demo
2. **L1:** Run the agent on a hardcoded topic ("What is an agentic loop?"), show the loop
3. Print a transition explanation: "That was Level 1. The agent completed — but we didn't
   verify the quality. Let's add a verification loop."
4. **L2:** Run the verification loop on a second topic, show grader feedback cycle
5. Print transition: "Level 2 adds quality gates. Now let's make this event-driven."
6. **L3:** Start the file watcher, pause for 8 seconds, then programmatically drop a test
   `.txt` file into `watch_inbox/` to trigger the agent automatically, let it complete,
   then stop the watcher
7. Print transition: "Level 3 runs without a human trigger. Finally, let's improve the agent."
8. **L4:** Run the hill climbing analysis on whatever traces were just generated, print
   the suggested improvement and save it

---

## `prompts.py`

Holds all system prompts as named string constants. Example:

```python
RESEARCH_AGENT_SYSTEM_PROMPT = """
You are a research assistant. Your job is to answer a research question thoroughly.
Use the search tool to find relevant information. Keep searching until you have enough
to write a clear, specific, 3-5 sentence summary. Do not guess — only include
information you retrieved from search results.
"""

GRADER_SYSTEM_PROMPT = """
You are a quality grader for research summaries. You will receive a summary and the
search results that were available to the agent. Score the summary on:
- Completeness: Does it fully answer the question?
- Accuracy: Does it only reference information from the search results?
- Clarity: Is it specific and easy to understand (no vague language)?

Respond in JSON: {"pass": true/false, "feedback": "one sentence explanation"}
"""
```

---

## `tools.py`

```python
# Simulated search tool — swap the body for a real API call (Brave, Tavily, SerpAPI)
def search(query: str) -> str:
    # Returns fake but plausible results keyed to common demo topics
    ...

def read_file(filename: str) -> str:
    # Reads a file from watch_inbox/
    ...

# Tool definitions in Anthropic SDK format (passed to client.messages.create)
TOOL_DEFINITIONS = [
    {
        "name": "search",
        "description": "Search the web for information about a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"]
        }
    },
    ...
]
```

---

## `requirements.txt`

```
anthropic>=0.25.0
watchdog>=4.0.0
python-dotenv>=1.0.0
```

---

## `.env.example`

```
ANTHROPIC_API_KEY=your_key_here
```

---

## Code Style & Teaching Conventions

- **Every function has a docstring** explaining its role in the loop architecture
- **Every major step has a print statement** with a clear prefix:
  - `[AGENT]` for agent loop steps
  - `[TOOL]` for tool calls and results
  - `[GRADER]` for verification steps
  - `[EVENT]` for file watcher events
  - `[META]` for hill climbing analysis
- **Inline comments explain the loop logic**, not the Python syntax
- Keep each level file self-contained — a student should be able to open `level2_verification.py`
  alone and understand it without reading the others
- No type: ignore, no bare excepts, no magic numbers without a comment
- Model: use `claude-3-5-haiku-20241022` for speed/cost in the demo; leave a comment showing
  where to swap to Sonnet/Opus for better quality

---

## Running the Demo

```bash
# Setup
git clone <repo>
cd agentic-loop-demo
pip install -r requirements.txt
cp .env.example .env
# Add your Anthropic API key to .env

# Run the full demo (recommended for classroom)
python run_demo.py

# Or run individual levels
python level1_agent.py
python level2_verification.py
python level3_event.py   # then drop a .txt file into watch_inbox/
python level4_hill_climbing.py
```
