# Agentic Loop Demo

A hands-on teaching demo that builds up an AI agent in **four stages**, one loop
at a time, based on Sydney Runkle's *"The Art of Loop Engineering."* You run it
from the terminal and watch each loop execute with clear, narrated output.

**The code is the lesson.** Every file is heavily commented to explain *why*, not
just *what*. Each level is self-contained — open one file and you can understand
that loop without reading the others.

| Level | Loop | What it adds | File |
|------:|------|--------------|------|
| 1 | **Agent loop** | An LLM calls tools in a loop until it decides it's done | [`level1_agent.py`](level1_agent.py) |
| 2 | **Verification loop** | A grader scores the output and sends it back if it's weak | [`level2_verification.py`](level2_verification.py) |
| 3 | **Event-driven loop** | Dropping a file in a folder triggers the agent automatically | [`level3_event.py`](level3_event.py) |
| 4 | **Hill climbing loop** | A meta-agent reads past runs and proposes a better prompt | [`level4_hill_climbing.py`](level4_hill_climbing.py) |

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) add an API key for real model calls
cp .env.example .env        # Windows: copy .env.example .env
#   then paste your key from https://console.anthropic.com/ into .env

# 3. Run the full demo
python run_demo.py
```

### No API key? It still runs.

If there's no `ANTHROPIC_API_KEY`, the demo automatically switches to **mock
mode**: canned, deterministic responses, zero cost, fully offline. Perfect for a
classroom where not everyone has a key. You can also force it:

```bash
python run_demo.py --mock        # offline, free, deterministic
python run_demo.py --mock -y     # ...and don't pause between levels
```

A loud `[MOCK MODE]` / `[LIVE MODE]` banner always tells you which one you're in.

---

## Running the levels individually

Each level runs on its own so you can focus on one loop at a time:

```bash
python level1_agent.py                 # one agent loop
python level1_agent.py "your topic"    # ...on your own topic

python level2_verification.py          # agent + grader retry cycle

python level3_event.py                 # start the file watcher, then:
#   drop a .txt file into watch_inbox/  (its contents = the research topic)

python level4_hill_climbing.py         # analyze traces, suggest a better prompt
```

> Level 4 needs traces to analyze, so run Level 1/2/3 (or `run_demo.py`) first.

---

## How the pieces fit together

```
run_demo.py          Orchestrates all four levels with narration.
  |
  +-- level1_agent.py ......... run_agent()           the core loop
  +-- level2_verification.py .. run_verified_agent()  wraps level 1 with a grader
  +-- level3_event.py ......... watches watch_inbox/, fires level 2 on new files
  +-- level4_hill_climbing.py . reads traces/, proposes a better prompt

Shared building blocks:
  llm.py ..... one model call for every level; also the mock-mode brain
  tools.py ... the simulated search() tool + its schema
  prompts.py . every system prompt, in one editable place (level 4 rewrites one)

Generated at runtime:
  traces/ ............. JSON log of each run (level 4 reads these)
  watch_inbox/ ........ drop .txt topics here (level 3 watches it)
  improved_prompts/ ... level 4 writes its suggested prompts here
```

### The data trail
Levels 1–3 each write a **trace** to `traces/` describing the run (topic, number
of iterations, grader verdict, feedback). Level 4 reads those traces, finds
patterns, and writes a suggested improved prompt to `improved_prompts/`. It does
**not** edit `prompts.py` for you — a human reviews the suggestion and applies it
by hand. Keeping a person in the loop before deploying a change is intentional.

---

## Configuration notes

- **Model:** set once in [`llm.py`](llm.py) as `MODEL` (`claude-haiku-4-5` —
  fast and cheap for a demo). Comments there show how to swap to Sonnet/Opus.
- **Real search:** [`tools.py`](tools.py) marks the single line you'd replace to
  call a real search API (Brave / Tavily / SerpAPI) instead of the simulated one.
- **Requirements:** `anthropic`, `watchdog`, `python-dotenv` (see
  [`requirements.txt`](requirements.txt)).

---

## Credits

Concept from Sydney Runkle, *"The Art of Loop Engineering."* This demo
re-implements the four loops with the **raw Anthropic SDK** (no agent framework)
so the loop mechanics stay visible — that's the teaching goal.
