# Agentic Loop Demo

A hands-on teaching demo that builds up an AI agent in **four stages**, one loop
at a time, based on Sydney Runkle's *"The Art of Loop Engineering."* You run it
from the terminal and watch each loop execute with clear, narrated output.

**The code is the lesson.** Every file is heavily commented to explain *why*, not
just *what*. Each level is self-contained — open one file and you can understand
that loop without reading the others. It's built on the **raw Anthropic SDK** (no
agent framework) on purpose, so the loop mechanics stay visible.

> **Companion docs**
> - [`INSTRUCTOR_GUIDE.md`](INSTRUCTOR_GUIDE.md) — classroom flow, per-level talking points, discussion questions, the close-the-loop exercise.
> - [`TESTING.md`](TESTING.md) — the complete command reference (every run mode, the file-watcher, the A/B test, cleanup, sanity checks).
> - [`CLAUDE.md`](CLAUDE.md) — notes for AI assistants / maintainers working in this repo.

| Level | Loop | What it adds | File |
|------:|------|--------------|------|
| 1 | **Agent loop** | An LLM calls tools in a loop until it decides it's done | [`level1_agent.py`](level1_agent.py) |
| 2 | **Verification loop** | A grader scores the output and sends it back if it's weak | [`level2_verification.py`](level2_verification.py) |
| 3 | **Event-driven loop** | Dropping a file in a folder triggers the agent automatically | [`level3_event.py`](level3_event.py) |
| 4 | **Hill climbing loop** | A meta-agent reads past runs and proposes a better prompt | [`level4_hill_climbing.py`](level4_hill_climbing.py) |

---

## Quick start

Requires **Python 3.10+**.

```bash
# 1. Install dependencies (anthropic, watchdog, python-dotenv)
pip install -r requirements.txt

# 2. Run the full demo (no key needed — see "mock mode" below)
python run_demo.py --mock -y
```

That's it — `--mock -y` runs all four levels offline, free, and deterministically.
To run against the **real Anthropic API**, add a key (next section), then drop
`--mock`.

### Adding an API key (for live mode)

```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
# then edit .env and set:  ANTHROPIC_API_KEY=sk-ant-...
```

Get a key at <https://console.anthropic.com/>.

> ⚠️ **Put the key in `.env`, never in `.env.example`.** `.env` is git-ignored;
> `.env.example` is a tracked template. The code reads `.env`.

Confirm the key works with a one-call smoke test:

```bash
python -c "import llm; m=llm.create_message(system='Reply with: OK', messages=[{'role':'user','content':'Say OK'}], max_tokens=16); print(''.join(b.text for b in m.content if b.type=='text'))"
```

### No API key? It still runs (mock mode).

If there's no `ANTHROPIC_API_KEY`, the demo automatically switches to **mock
mode**: canned, deterministic responses, zero cost, fully offline. Perfect for a
classroom where not everyone has a key. A loud `[MOCK MODE]` / `[LIVE MODE]`
banner always tells you which one you're in. See the
[mock-mode caveat](#mock-mode-caveat-important-for-honesty) for what's scripted.

---

## Run modes & flags

`run_demo.py` accepts these flags (combine freely):

| Flag | Effect |
|------|--------|
| *(none)* | Live if a key is present, else mock. Pauses for Enter between levels. |
| `--mock` | Force offline mock mode (free, deterministic). |
| `-y`, `--yes` | Don't pause between levels (hands-off run). Implied by `--mock`. |
| `--strict` | Raise the grader's bar so L2/L3 **visibly fail once and retry** (see below). |

```bash
python run_demo.py                 # live (or mock), pauses between levels
python run_demo.py -y              # live, no pauses
python run_demo.py --mock -y       # offline, no pauses (fastest)
python run_demo.py --strict        # live, with the visible fail->retry
python run_demo.py --strict -y     # ...and no pauses
```

### `--strict`: make the verification loop actually loop

In **live** mode the model is usually good enough to pass the grader on the first
try, so Level 2 doesn't visibly retry. `--strict` raises the bar — the summary
must be **plain prose (no markdown)** *and* state an **explicit tradeoff** — so the
model's first (markdown-formatted) draft reliably **fails**, and you watch
**attempt 2 pass** after the feedback goes back in. It's off by default so normal
runs stay realistic. (In **mock** mode the retry is always shown regardless.)

```bash
python run_demo.py --strict
python level2_verification.py --strict "your topic"
python level3_event.py --strict           # the watcher, with strict grading
```

---

## Running the levels individually

Each level runs on its own so you can focus on one loop at a time.

```bash
# Level 1 — the agent loop
python level1_agent.py                       # default topic
python level1_agent.py "What is prompt caching?"

# Level 2 — the verification loop (agent + grader retry cycle)
python level2_verification.py
python level2_verification.py "What is hill climbing?"
python level2_verification.py --strict "What is an agentic loop?"

# Level 4 — hill climbing (needs traces first; run the demo or L1/L2/L3 once)
python level4_hill_climbing.py
```

### Level 3 — the event-driven watcher (two terminals)

Level 3 watches `watch_inbox/` and fires the full verified agent when a `.txt`
file appears. Run the watcher in one terminal, drop a file from another:

```bash
# Terminal 1 — start the watcher (Ctrl+C to stop)
python level3_event.py
python level3_event.py --strict              # optional: stricter grading

# Terminal 2 — drop a topic file (its contents = the research topic)
echo "What is an agentic loop?" > watch_inbox/q.txt          # Bash
"What is an agentic loop?" | Set-Content watch_inbox/q.txt   # PowerShell
```

The watcher prints an `EVENT RECEIVED` banner, runs the agent, and writes the
answer to `watch_inbox/q.summary.txt`. (`run_demo.py` does this automatically — it
starts the watcher and drops a file for you.)

---

## Closing the hill-climbing loop (Level 4's payoff)

Level 4 only *suggests* a better prompt — it never applies it. Two ways to see
whether the suggestion actually helps. **Both need live mode** (the mock ignores
prompt content, so the comparison is flat).

### Option A — the A/B harness (measured, automatic)

[`hill_climb_experiment.py`](hill_climb_experiment.py) runs the agent N times with
the current prompt, then N times with the latest suggested prompt, and compares
the **average loop iterations**:

```bash
python run_demo.py -y                 # 1. generate traces + a suggestion
python hill_climb_experiment.py       # 2. A/B the suggestion vs. current prompt
python hill_climb_experiment.py --runs 6 --topic "What is an agentic loop?"
```

In our live testing the improved prompt cut iterations **3.00 → 2.50 (~17% fewer)**
by curbing the agent's tendency to over-search the (identical) demo results. The
effect is real but small and noisy — which is exactly why a human reviews the
suggestion instead of auto-deploying it.

### Option B — the manual exercise (what students do)

1. `python run_demo.py` to generate `improved_prompts/prompt_*.txt`.
2. Read the suggestion; decide what's actually an improvement.
3. Paste the good parts into `RESEARCH_AGENT_SYSTEM_PROMPT` in
   [`prompts.py`](prompts.py).
4. Re-run and compare iteration counts / grader verdicts.
5. Decide whether to keep it — human-in-the-loop is the point of Level 4.

> The A/B harness uses `run_agent`'s optional `system_prompt` override to test the
> improved prompt **without** editing `prompts.py`, so the repo keeps its teachable
> initial state. Students still do the manual paste as the exercise.

---

## Project structure

```
agentic-loop-demo/
├── run_demo.py               # Entry point — runs all 4 levels with narration
├── level1_agent.py           # L1: the core agent loop  (run_agent)
├── level2_verification.py    # L2: verification loop     (run_verified_agent)
├── level3_event.py           # L3: file-watcher event loop
├── level4_hill_climbing.py   # L4: trace analysis -> improved prompt
├── hill_climb_experiment.py  # A/B test: does the L4 suggestion help?
│
├── llm.py                    # ONE model call for every level + the mock-mode brain
├── tools.py                  # simulated search() / read_file() + tool schemas
├── prompts.py                # all system prompts (L4 rewrites one)
│
├── requirements.txt          # anthropic, watchdog, python-dotenv
├── .env.example              # template — copy to .env and add your key
├── .gitignore                # ignores .env, artifacts, __pycache__
│
├── README.md                 # this file
├── TESTING.md                # full command reference
├── INSTRUCTOR_GUIDE.md       # classroom flow & talking points
├── CLAUDE.md                 # maintainer / AI-assistant notes
├── spec.md                   # original project spec
│
├── traces/                   # runtime: JSON log of each run (L4 reads these)
├── watch_inbox/              # runtime: drop .txt topics here (L3 watches it)
└── improved_prompts/         # runtime: L4 writes its suggested prompts here
```

### How the pieces fit together

```
run_demo.py          Orchestrates all four levels with narration.
  |
  +-- level1_agent.py ......... run_agent()           the core loop
  +-- level2_verification.py .. run_verified_agent()  wraps level 1 with a grader
  +-- level3_event.py ......... watches watch_inbox/, fires level 2 on new files
  +-- level4_hill_climbing.py . reads traces/, proposes a better prompt

Shared building blocks:
  llm.py ..... one model call for every level; defines MODEL; the mock-mode brain
  tools.py ... the simulated search() tool + its schema
  prompts.py . every system prompt, in one editable place (level 4 rewrites one)
```

### The data trail
Levels 1–3 each write a **trace** to `traces/` describing the run (topic, number
of iterations, grader verdict, feedback). Level 4 reads those traces, finds
patterns, and writes a suggested improved prompt to `improved_prompts/`. It does
**not** edit `prompts.py` for you — a human reviews the suggestion and applies it
by hand. Keeping a person in the loop before deploying a change is intentional.

The trace schema (`{topic, messages, iterations, grader_result}`) is defined once
in `level1_agent.write_trace()` so every level writes the same shape.

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
  "improved prompt" will **not** change later runs (and the A/B harness shows
  "no change"). To actually see hill climbing work, use a real API key.

### What only shows up in which mode

| Behavior | Mock | Live |
|---|------|------|
| All four loops run end to end | ✅ | ✅ |
| L2 fails attempt 1 then passes | ✅ always (scripted) | only with `--strict` |
| L4 suggestion changes later runs | ❌ (prompt-insensitive) | ✅ |
| Real model wording / query choices | ❌ canned | ✅ |
| Cost | free | small (Haiku, short prompts) |

---

## Configuration notes

- **Model:** set once in [`llm.py`](llm.py) as `MODEL` (`claude-haiku-4-5` — fast
  and cheap for a demo). Comments there show how to swap to Sonnet/Opus. Every
  level picks up the change automatically.
- **Real search:** [`tools.py`](tools.py) marks the single line you'd replace to
  call a real search API (Brave / Tavily / SerpAPI) instead of the simulated one.
- **Iteration cap / retries:** `MAX_ITERATIONS` (in `level1_agent.py`) and
  `MAX_RETRIES` (in `level2_verification.py`) are the safety rails that keep a
  misbehaving loop from running — and billing — forever.
- **Requirements:** `anthropic`, `watchdog`, `python-dotenv` (see
  [`requirements.txt`](requirements.txt)). Python 3.10+.

---

## Resetting / cleanup

Runtime files (`traces/*.json`, `improved_prompts/*.txt`, `watch_inbox/*.txt`,
`*.summary.txt`) are git-ignored. To wipe them and start fresh:

```bash
# Bash
rm -f traces/*.json improved_prompts/*.txt watch_inbox/*.txt watch_inbox/*.summary.txt
# PowerShell
Remove-Item traces/*.json, improved_prompts/*.txt, watch_inbox/*.txt, watch_inbox/*.summary.txt -ErrorAction SilentlyContinue
```

See [`TESTING.md`](TESTING.md) for maintainer sanity checks (compile, secret
hygiene).

---

## Credits

Concept from Sydney Runkle, *"The Art of Loop Engineering."* This demo
re-implements the four loops with the **raw Anthropic SDK** (no agent framework)
so the loop mechanics stay visible — that's the teaching goal.
