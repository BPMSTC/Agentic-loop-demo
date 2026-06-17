# Testing & Command Reference

Every command for running and verifying the demo, in one place. Commands work in
both PowerShell and Bash unless noted. Run them from the project root.

> **Mock vs. live.** With **no API key** the demo runs in **mock mode** (canned,
> free, offline, deterministic). With a key in `.env` it runs in **live mode**
> (real Anthropic API). A loud `[MOCK MODE]` / `[LIVE MODE]` banner shows which.
> Some behaviors only appear in one mode — noted per command below.

---

## 0. One-time setup

```bash
pip install -r requirements.txt          # anthropic, watchdog, python-dotenv
```

Optional (only for live mode — real model calls):

```bash
# macOS/Linux
cp .env.example .env
# Windows (PowerShell)
Copy-Item .env.example .env
```

Then edit `.env` and set `ANTHROPIC_API_KEY=sk-ant-...` (get one at
https://console.anthropic.com/). **Put the key in `.env`, never in
`.env.example`** — `.env` is git-ignored; `.env.example` is a tracked template.

### Verify your environment

```bash
python --version                                  # expect 3.10+
python -c "import anthropic, watchdog, dotenv; print('deps OK')"
python -c "import llm; print(llm.mode_banner())"  # shows MOCK or LIVE
```

### Live smoke test (one cheap API call — confirms key + model)

```bash
python -c "import llm; m=llm.create_message(system='Reply with: OK', messages=[{'role':'user','content':'Say OK'}], max_tokens=16); print(''.join(b.text for b in m.content if b.type=='text'))"
```
Expect `OK`. An auth error here means the key in `.env` is wrong or missing.

---

## 1. The full demo (all four levels)

```bash
python run_demo.py                # live if key present, else mock; pauses between levels
python run_demo.py -y             # don't pause for Enter between levels
python run_demo.py --mock         # force offline mock mode (free, deterministic)
python run_demo.py --mock -y      # offline + no pauses (fastest hands-off run)
python run_demo.py --strict       # raise the grader bar so L2/L3 visibly fail then retry
python run_demo.py --strict -y    # ...and don't pause
```

Flags combine. `--mock` and `--strict` are independent of each other.

After a run, look at what it produced:

```bash
ls traces/                        # one trace_*.json per run
ls improved_prompts/              # the Level 4 suggested prompt
cat watch_inbox/*.summary.txt     # the Level 3 answer file
```

---

## 2. Running each level on its own

```bash
# Level 1 — the agent loop
python level1_agent.py
python level1_agent.py "What is prompt caching?"     # custom topic

# Level 2 — the verification loop
python level2_verification.py
python level2_verification.py "What is hill climbing?"
python level2_verification.py --strict "What is an agentic loop?"   # force a visible retry

# Level 4 — hill climbing (needs traces to exist first; see below)
python level4_hill_climbing.py
```

Level 3 has its own section (it watches a folder) — see next.

---

## 3. Level 3 — the event-driven watcher

Level 3 watches `watch_inbox/` and fires the verified agent when a `.txt` file
appears. Run the watcher in one terminal, drop a file from another.

**Terminal 1 — start the watcher** (Ctrl+C to stop):

```bash
python level3_event.py
python level3_event.py --strict        # stricter grader (visible retry)
```

**Terminal 2 — drop a topic file** (its contents = the research topic):

```bash
# Bash
echo "What is an agentic loop?" > watch_inbox/q.txt
# PowerShell
"What is an agentic loop?" | Set-Content watch_inbox/q.txt
```

The watcher prints an `EVENT RECEIVED` banner, runs the agent, and writes
`watch_inbox/q.summary.txt`. Drop more files to trigger more runs.

> `run_demo.py` exercises Level 3 automatically — it starts the watcher and
> drops a file for you — so you don't need two terminals just to see it work.

---

## 4. Closing the hill-climbing loop (Level 4 payoff)

Level 4 only *suggests* a better prompt. There are two ways to see whether the
suggestion actually helps. **Both need live mode** — in mock mode the canned
"model" ignores the prompt, so the prompt change has no effect.

### Option A — the A/B script (automatic, measurable)

```bash
# 1. Generate traces + a suggestion (run the demo, or just level 4 after some runs)
python run_demo.py -y

# 2. A/B test the suggestion vs. the current prompt (averages iteration counts)
python hill_climb_experiment.py
python hill_climb_experiment.py --runs 6 --topic "What is an agentic loop?"
```

It runs the agent N times with each prompt and reports the average iterations —
fewer iterations after = the climb worked. Small samples are noisy; raise
`--runs` for a firmer signal.

### Option B — the manual exercise (what students do)

1. Run `python run_demo.py` to generate `improved_prompts/prompt_*.txt`.
2. Open that file and `prompts.py` side by side.
3. Paste the good parts into `RESEARCH_AGENT_SYSTEM_PROMPT` in `prompts.py`.
4. Re-run `python run_demo.py` and compare iteration counts / grader verdicts.
5. Decide whether to keep the change (human-in-the-loop — the point of Level 4).

---

## 5. Cleaning up generated artifacts

Runtime files are git-ignored, but to reset to a pristine state:

```bash
# Bash
rm -f traces/*.json improved_prompts/*.txt watch_inbox/*.txt watch_inbox/*.summary.txt
# PowerShell
Remove-Item traces/*.json, improved_prompts/*.txt, watch_inbox/*.txt, watch_inbox/*.summary.txt -ErrorAction SilentlyContinue
```

---

## 6. Sanity checks for maintainers

```bash
python -m py_compile *.py                 # all files compile
git check-ignore .env                     # expect ".env" (your key is ignored)
git ls-files | grep -i env                # expect ONLY .env.example (never .env)
git grep -i "sk-ant-" $(git rev-parse HEAD) -- . || echo "no key in HEAD (good)"
```

---

## What only shows up in which mode

| Behavior | Mock | Live |
|---|------|------|
| All four loops run end to end | ✅ | ✅ |
| L2 fails attempt 1 then passes | ✅ always (scripted) | only with `--strict` |
| L4 suggestion changes later runs | ❌ (prompt-insensitive) | ✅ |
| Real model wording / query choices | ❌ canned | ✅ |
| Cost | free | small (Haiku, short prompts) |

If you need the L2 retry visible in **live** mode, use `--strict`. If you need it
guaranteed with **no key/cost**, use `--mock`.
