# Agentic Loop Demo

A hands-on teaching demo that builds up an AI agent in **four stages**, one loop
at a time, based on Sydney Runkle's *"The Art of Loop Engineering."* You run it
from the terminal and watch each loop execute with clear, narrated output.

**The code is the lesson.** Every file is heavily commented to explain *why*, not
just *what*. Each level is self-contained — open one file and you can understand
that loop without reading the others.

> **Teaching from this repo?** See [`INSTRUCTOR_GUIDE.md`](INSTRUCTOR_GUIDE.md)
> for a classroom flow, per-level talking points, discussion questions, and a
> hands-on exercise that closes the hill-climbing loop.
>
> **Just want the commands?** [`TESTING.md`](TESTING.md) is the full command
> reference — setup, every run mode, the file-watcher, and the hill-climbing A/B test.

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

### Want to *see* the verification loop actually loop? Use `--strict`.

In live mode the model is usually good enough to pass the grader on the first
try, so Level 2 doesn't visibly retry. The `--strict` flag raises the grader's
bar (plain prose, no markdown, plus an explicit tradeoff) so the first draft
reliably fails and you watch attempt 2 pass — the loop, made visible:

```bash
python run_demo.py --strict          # live, with the visible fail->retry
python level2_verification.py --strict "your topic"
```

It's off by default so normal runs stay realistic. (In mock mode the retry is
always shown regardless.)

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

hill_climb_experiment.py ..... A/B test: does the L4 suggestion actually help?
                               (averages iteration counts, current vs improved)

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

## How this maps to *"The Art of Loop Engineering"*

The article describes each loop with a LangChain primitive. This demo
re-implements the same idea with the raw Anthropic SDK so the mechanics are
visible. Same concepts, no framework:

| Loop | Article's primitive | What it does | Our implementation |
|------|---------------------|--------------|--------------------|
| 1 Agent | `create_agent` | Model calls tools until the task is complete | [`level1_agent.py`](level1_agent.py) `run_agent()` |
| 2 Verification | `RubricMiddleware` | Output scored against a rubric, retried with feedback | [`level2_verification.py`](level2_verification.py) `run_verified_agent()` |
| 3 Event | LangSmith Deployment / Fleet channels | A system event triggers the agent | [`level3_event.py`](level3_event.py) `watchdog` on `watch_inbox/` |
| 4 Hill climbing | LangSmith Engine | Traces feed an analysis agent that improves the harness | [`level4_hill_climbing.py`](level4_hill_climbing.py) `run_hill_climbing()` |

## Human oversight (a first-class concern at *every* loop)

The article stresses that automation doesn't remove humans — each loop has a
natural place for human judgment. The code calls these out where they belong:

1. **Agent loop** — require human approval before a *sensitive* tool call (send
   money, delete data, open a PR). See the note in `level1_agent.run_agent()`.
   Our tools are read-only, so there's nothing to gate — but the spot is marked.
2. **Verification loop** — a human can *be* the grader, or sign off on the
   model's verdict, for sensitive work. See `level2_verification.grade_summary()`.
3. **Event / application loop** — a human can approve output before it's returned
   to a user or a live system. See `level3_event.handle_topic_file()`.
4. **Hill-climbing loop** — harness changes flow through human review before
   deploy. Level 4 *never* edits `prompts.py` for you; it writes a suggestion and
   stops. Applying it is your call.

## What we intentionally simplified (so you can be honest with students)

This is a teaching model, not a production system. The differences from the
article's real-world docs agent are deliberate:

- **Tools are read-only** (`search`, `read_file`). The article's docs agent also
  *writes* (clones repos, opens PRs). We avoid write-tools so the demo is safe to
  run anywhere; the one real side effect is Level 3 writing a `.summary.txt`.
- **Search is simulated** — canned, offline, deterministic. One marked line in
  `tools.py` is where a real Brave/Tavily/SerpAPI call would go.
- **The grader is agentic (LLM-as-judge).** The article's strongest grader is
  *deterministic* (run tests, check links). Both are valid; we show the agentic
  one because it's the idea unique to LLMs. (See the note in `level2`.)
- **Hill climbing improves only the prompt**, single-shot. Real hill climbing
  runs continuously over many traces and can also tweak tools, the grader,
  memory, or even feed RL fine-tuning.
- **Level 3 uses a local file-watcher** as a stand-in for webhooks/cron/queues.

### Mock-mode caveat (important for honesty)

With no API key the demo runs in **mock mode**: responses are *scripted to
illustrate the control flow*, not generated. In particular:

- The verification loop is rigged so attempt 1 fails (vague draft) and attempt 2
  passes — that's to *show* the retry cycle, not a real quality judgment.
- The mock **ignores the system prompt's content**, so in mock mode Level 4's
  "improved prompt" will **not** change later runs. To actually see hill climbing
  work, use a real API key and apply the suggestion by hand.

A loud `[MOCK MODE]` / `[LIVE MODE]` banner always tells you which you're in.

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
