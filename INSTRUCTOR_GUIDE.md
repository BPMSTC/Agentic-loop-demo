# Instructor Guide

How to teach the four agentic loops with this repo. Pairs with Sydney Runkle's
*"The Art of Loop Engineering"* (PDF in the repo root). Plan for **45–60 minutes**.

---

## Before class

- `pip install -r requirements.txt`
- Decide your mode:
  - **Mock mode** (no key): `python run_demo.py --mock` — free, offline,
    deterministic, identical every time. Best for a guaranteed live walkthrough.
  - **Live mode** (real key in `.env`): real model calls. Best for showing that
    the loops are genuine, and *required* for the hill-climbing exercise to
    actually change behavior (see the mock caveat in the README).
- Do one dry run yourself first so the output scroll holds no surprises.

## Suggested classroom flow

1. **Frame the thesis (5 min).** "An agent is just an LLM in a loop. The art is
   in the loops you *stack* on top." Put the four-loop ladder on the board:
   `Agent → Verification → Event-driven → Hill climbing`.
2. **Run it (25–30 min).** `python run_demo.py` (drop `--mock`/`-y` to pause
   between levels and talk). The narration prints transitions for you; expand on
   each with the talking points below.
3. **Discuss (10–15 min).** Use the hard questions at the bottom.
4. **Exercise (homework or live).** Close the hill-climbing loop yourself
   (below).

---

## Per-level talking points

### Level 1 — the agent loop
- Open [`level1_agent.py`](level1_agent.py). The whole idea is `while True`: ask
  the model, run any tools it asked for, feed results back, repeat.
- **The stop condition is the lesson:** the loop ends when the model returns text
  with *no tool call*. The **model** decides it's done — not a counter, not us.
- Point at `MAX_ITERATIONS`: the only thing *we* control is a safety cap so a
  misbehaving agent can't loop (and bill) forever.
- Note the marked **human-in-the-loop** spot before tool execution.

### Level 2 — the verification loop
- "Level 1 always *finishes*. Finishing isn't the same as being *correct*."
- Show the grade/retry cycle: attempt 1 fails, feedback goes back in, attempt 2
  passes. That outer loop is the whole point.
- **Live mode caveat:** the real model usually passes on the *first* try, so the
  loop won't visibly retry. Run with **`--strict`** (`python run_demo.py --strict`)
  to raise the bar (plain prose, no markdown, explicit tradeoff) so the first
  draft reliably fails and the class watches attempt 2 pass. Good teaching beat:
  ask *why* a capable model still benefits from a loop it usually passes.
- **Deterministic vs. agentic graders** (see the module docstring): we use an
  LLM-as-judge; the article's strongest example is deterministic (run tests).
  Ask: *when would you prefer each?*
- Name the **tradeoff**: every check is another model call — latency and cost.

### Level 3 — the event-driven loop
- "The agent stops being a script you run and becomes a service that runs."
- The dropped file is an **event**. Emphasize it's a stand-in for a webhook, a
  cron tick, a queue message — the trigger is the *system*, not a person.
- Show that it keeps watching: drop a second file (`echo "your topic" >
  watch_inbox/q.txt`) and watch it fire again.

### Level 4 — the hill-climbing loop
- "The first three loops automate *work*. The fourth automates *improvement*."
- Show the trace digest feeding the meta-agent, and the before/after prompt.
- **The key move:** the improvement targets the *inner* loop's config (the
  prompt). The prompt is just the easiest knob — tools, the grader, memory, even
  RL fine-tuning are all fair game.
- **Why it doesn't auto-apply:** human-in-the-loop. A person decides if the
  suggestion is actually better. That's a feature, not a missing piece.

---

## Exercise: close the hill-climbing loop (the real "climb")

The demo *suggests* a better prompt but stops there. Have students finish it
(requires **live mode** — the mock ignores prompt content):

1. Run `python run_demo.py` once to generate traces and a suggestion in
   `improved_prompts/`.
2. Read the suggestion. Decide what's actually an improvement.
3. Paste the good parts into `RESEARCH_AGENT_SYSTEM_PROMPT` in
   [`prompts.py`](prompts.py).
4. Re-run. Compare: does the agent pass on the first try now? Fewer iterations?
5. Discuss: *who* should be allowed to approve a prompt change in a real system,
   and what could go wrong if this were fully automated?

---

## Discussion questions (these are the hard ones)

1. Our grader is a model judging a model. When is that circular and unreliable,
   and when is a **deterministic** grader (tests, link-checks) the better call?
2. Level 4 writes a suggestion but never re-runs with it. Is that hill
   *climbing*, or hill *observing*? What would it take to safely close the loop
   automatically?
3. The article says the real value is in loops 3 and 4. Our versions are small
   (a file-watcher, a single-shot analysis). What does each look like at
   production scale?
4. Human oversight is called a "first-class primitive." Find all four places in
   this codebase where a human checkpoint belongs. Which would you actually wire
   up first, and why?
5. In mock mode the outcomes are scripted (fail-then-pass). How would you prove
   to a skeptic that the loops genuinely work — what would you run, and what
   would you measure?

---

## What's real vs. simulated (be upfront about this)

| Piece | Real | Simulated |
|-------|------|-----------|
| The agent loop / tool-calling protocol | ✅ real Anthropic SDK shape | — |
| Model responses | ✅ in live mode | scripted in mock mode |
| `search()` tool | — | ✅ canned, offline |
| File-watch trigger (L3) | ✅ real `watchdog` | (file-drop stands in for webhooks/cron) |
| Trace logging + analysis (L4) | ✅ real files, real analysis in live mode | scripted suggestion in mock mode |

See the README's "What we intentionally simplified" and "Mock-mode caveat"
sections for the full honest accounting.
