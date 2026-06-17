# CLAUDE.md — notes for AI assistants working in this repo

## What this is
A **teaching demo** for software-development students: four levels of agentic
loop design (agent → verification → event-driven → hill climbing), based on
Sydney Runkle's "The Art of Loop Engineering" (source PDF is in the repo root).

## The prime directive: the code IS the lesson
This is not production code optimized for brevity. It is optimized for a student
reading it top to bottom. When editing:
- **Keep the heavy comments.** Explain *why* (the loop concept), not Python syntax.
- **Keep each level file self-contained.** A student should understand
  `level2_verification.py` without first reading levels 1, 3, or 4.
- Use the print prefixes consistently: `[AGENT]`, `[TOOL]`, `[GRADER]`,
  `[EVENT]`, `[META]`.
- No bare `except`, no `type: ignore`, no unexplained magic numbers.

## Architecture
- `llm.py` — the ONLY place that calls the model and the ONLY place `MODEL` is
  defined. It also contains **mock mode**: if there's no `ANTHROPIC_API_KEY` (or
  `--mock`), it returns fake responses shaped exactly like the real SDK so the
  level code is identical in both modes. If you change how a level calls the
  model, update the matching `_mock_*` function in `llm.py` or mock runs break.
- `prompts.py` — all system prompts. Level 4 reads `RESEARCH_AGENT_SYSTEM_PROMPT`
  and proposes a rewrite. The mock dispatcher in `llm.py` routes on each prompt's
  **opening "You are a ..." line** ("You are a quality grader", "You are a prompt
  engineer", else the research agent). Keep those opening lines intact if you edit
  the prompts, or update the dispatcher to match.
- `tools.py` — simulated `search()` (offline, keyword-keyed) + tool schemas.
- Trace schema is defined once in `level1_agent.write_trace()`:
  `{topic, messages, iterations, grader_result}`. Level 4 depends on that shape.

## Testing without a key
`python run_demo.py --mock -y` runs all four levels offline and deterministically.
The mock is designed so Level 2 FAILS the first attempt (vague summary) and PASSES
the retry — that's intentional, it's how students see the verification loop work.

## Environment
Developed on Windows (PowerShell). Paths use `os.path.join`; file watching and the
demo file-drop are Windows-safe. Keep it cross-platform.
