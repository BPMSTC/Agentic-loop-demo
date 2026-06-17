"""
hill_climb_experiment.py — Did Level 4's suggestion actually help?

Level 4 (hill climbing) writes a *suggested* better prompt to improved_prompts/
but never applies it — a human decides. This script closes that loop as a
measurable A/B test: it runs the agent on the same topic many times with the
CURRENT prompt, then again with the LATEST improved prompt, and compares the
average number of loop iterations.

Why iterations? The original research prompt says "keep searching until you have
enough," which makes the agent over-search the (identical) demo search results.
Level 4 reliably notices this in the traces and proposes a prompt that caps
searches. Fewer iterations on the same task = the climb worked.

This is the programmatic version of the student exercise (paste the suggestion
into prompts.py and re-run). It uses run_agent's `system_prompt` override so it
can compare both prompts in one run WITHOUT editing prompts.py.

Usage (needs a real API key — the mock ignores the prompt, so the A/B is flat):
    python hill_climb_experiment.py
    python hill_climb_experiment.py --runs 5 --topic "What is an agentic loop?"
"""

import argparse
import contextlib
import glob
import io
import os

from level1_agent import run_agent
from prompts import RESEARCH_AGENT_SYSTEM_PROMPT

IMPROVED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "improved_prompts")

# A topic whose (identical) search results tempt the agent to over-search, so the
# search-capping improvement has room to show an effect.
DEFAULT_TOPIC = "What is an event-driven agent loop?"


def latest_improved_prompt():
    """Return the text of the most recent improved_prompts/*.txt, or None."""
    files = sorted(glob.glob(os.path.join(IMPROVED_DIR, "prompt_*.txt")))
    if not files:
        return None
    with open(files[-1], "r", encoding="utf-8") as f:
        return f.read().strip(), os.path.relpath(files[-1])


def iterations_for(topic, system_prompt=None):
    """
    Run one agent loop and return just its iteration count, swallowing the
    agent's verbose per-step logging so the comparison output stays readable.
    """
    with contextlib.redirect_stdout(io.StringIO()):
        return run_agent(topic, system_prompt=system_prompt).iterations


def main():
    parser = argparse.ArgumentParser(description="A/B test the Level 4 improved prompt.")
    parser.add_argument("--topic", default=DEFAULT_TOPIC, help="Topic to test on.")
    parser.add_argument("--runs", type=int, default=4, help="Runs per prompt (default 4).")
    args = parser.parse_args()

    improved = latest_improved_prompt()
    if improved is None:
        print("No improved prompt found in improved_prompts/.")
        print("Generate one first:  python level4_hill_climbing.py")
        print("(after running the demo so there are traces to analyze).")
        return
    improved_text, improved_path = improved

    print("=" * 70)
    print("HILL-CLIMBING A/B TEST")
    print(f"Topic     : {args.topic}")
    print(f"Runs each : {args.runs}")
    print(f"Improved  : {improved_path}")
    print("=" * 70)
    print("Running... (each run is a full agent loop against the real API)\n")

    before = [iterations_for(args.topic) for _ in range(args.runs)]
    after = [iterations_for(args.topic, system_prompt=improved_text) for _ in range(args.runs)]

    before_avg = sum(before) / len(before)
    after_avg = sum(after) / len(after)

    print(f"BEFORE  (current prompt) : {before}  ->  avg {before_avg:.2f} iterations")
    print(f"AFTER   (L4 improved)    : {after}  ->  avg {after_avg:.2f} iterations")
    print("-" * 70)
    delta = before_avg - after_avg
    if delta > 0:
        pct = 100 * delta / before_avg
        print(f"RESULT: the improved prompt cut iterations by {delta:.2f} "
              f"({pct:.0f}% fewer) on average. The climb worked.")
    elif delta < 0:
        print(f"RESULT: the improved prompt used {-delta:.2f} MORE iterations on "
              f"average — not every suggestion is better. (That's why a human reviews.)")
    else:
        print("RESULT: no change in average iterations on this sample.")
    print("=" * 70)
    print("Note: small samples are noisy — raise --runs for a firmer signal.")


if __name__ == "__main__":
    main()
