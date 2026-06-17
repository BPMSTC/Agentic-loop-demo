"""
level4_hill_climbing.py — LOOP 4: THE HILL CLIMBING LOOP

    past run traces --> meta-agent analyzes them --> a better system prompt
                                                            |
                                              (human reviews, then applies)

Concept:
    The first three loops automate WORK. The fourth automates IMPROVEMENT. Every
    run leaves a trace (what topic, how many iterations, did it pass, what did
    the grader say). A meta-agent reads those traces, spots patterns in the
    failures and inefficiencies, and writes an improved system prompt for the
    research agent. The agent's own behavior becomes the training signal — each
    generation of runs can make the next one better.

    IMPORTANT: this does NOT overwrite prompts.py automatically. It writes the
    suggestion to improved_prompts/ and leaves the decision to a human. That
    "human in the loop" before deploying a change is the point, not an oversight.

Self-contained: run it after you've generated some traces (run Level 1/2/3, or
the full run_demo.py) and then:

    python level4_hill_climbing.py
"""

import glob
import json
import os
from datetime import datetime

import llm
from prompts import META_IMPROVER_SYSTEM_PROMPT, RESEARCH_AGENT_SYSTEM_PROMPT

TRACES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traces")
IMPROVED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "improved_prompts")

# How many recent runs to feed the meta-agent. We keep it small so the prompt
# stays cheap and focused on RECENT behavior (the article's traces digest idea).
RECENT_TRACES_TO_ANALYZE = 3


def load_traces():
    """
    Load every trace JSON from traces/, oldest first. Filenames are timestamped,
    so sorting by name sorts by time. Returns a list of trace dicts.
    """
    paths = sorted(glob.glob(os.path.join(TRACES_DIR, "trace_*.json")))
    traces = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            traces.append(json.load(f))
    return traces


def build_digest(traces):
    """
    Condense the most recent runs into a few readable lines for the meta-agent.
    We send a DIGEST, not the full message logs, to keep the token count (and
    cost) sane — the meta-agent only needs the signal, not every word.

    Produces lines like:
        Run 1: Topic="X", Iterations=4, Grader=FAIL, Feedback="too vague"
    """
    recent = traces[-RECENT_TRACES_TO_ANALYZE:]
    lines = []
    for i, trace in enumerate(recent, start=1):
        grade = trace.get("grader_result")
        if grade is None:
            verdict, feedback = "N/A", "(not graded)"
        else:
            verdict = "PASS" if grade["pass"] else "FAIL"
            feedback = grade["feedback"]
        lines.append(
            f'Run {i}: Topic="{trace["topic"]}", '
            f'Iterations={trace["iterations"]}, '
            f"Grader={verdict}, "
            f'Feedback="{feedback}"'
        )
    return "\n".join(lines)


def run_hill_climbing():
    """
    The meta-loop: read traces, ask the model to improve the agent's prompt,
    show the before/after, and save the suggestion for a human to review.

    Returns the path to the saved suggestion, or None if there were no traces.
    """
    print("[META]  Loading traces from", os.path.relpath(TRACES_DIR))
    traces = load_traces()

    if not traces:
        print("[META]  No traces found yet. Run Level 1/2/3 (or run_demo.py) first.")
        return None

    print(f"[META]  Found {len(traces)} trace(s); analyzing the most recent "
          f"{min(RECENT_TRACES_TO_ANALYZE, len(traces))}.")
    digest = build_digest(traces)
    print("[META]  Run digest fed to the meta-agent:")
    for line in digest.splitlines():
        print("          " + line)

    # The meta-agent's input: the CURRENT prompt plus the digest of recent runs.
    meta_input = (
        "Here is the research agent's CURRENT system prompt:\n"
        "-------------------------------------------------\n"
        f"{RESEARCH_AGENT_SYSTEM_PROMPT}\n"
        "-------------------------------------------------\n\n"
        "Here is a digest of its recent runs:\n"
        f"{digest}\n\n"
        "Analyze the patterns and write an improved system prompt."
    )

    print("\n[META]  Asking the meta-agent to propose a better prompt...")
    message = llm.create_message(
        system=META_IMPROVER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": meta_input}],
        max_tokens=1024,
    )
    improved_prompt = "\n".join(
        block.text for block in message.content if block.type == "text"
    ).strip()

    # Show the before/after so the change is obvious to a human reviewer.
    print("\n" + "=" * 70)
    print("--- CURRENT PROMPT ---")
    print("=" * 70)
    print(RESEARCH_AGENT_SYSTEM_PROMPT)
    print("\n" + "=" * 70)
    print("--- SUGGESTED IMPROVEMENT ---")
    print("=" * 70)
    print(improved_prompt)
    print("=" * 70)

    # Save it for review. We deliberately DON'T edit prompts.py — a human decides
    # whether this is actually better and applies it by hand.
    os.makedirs(IMPROVED_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(IMPROVED_DIR, f"prompt_{timestamp}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(improved_prompt + "\n")

    print(f"\n[META]  Saved suggestion -> {os.path.relpath(out_path)}")
    print("[META]  Review it, and if it's better, paste it into prompts.py yourself.")
    print("[META]  (Keeping a human in the loop before deploying is the point.)")
    return out_path


def main():
    """Run Level 4 on its own to analyze whatever traces exist."""
    print("=" * 70)
    print("LEVEL 4 — THE HILL CLIMBING LOOP")
    print("The agent analyzes its own past runs and proposes a better prompt.")
    print(llm.mode_banner())
    print("=" * 70 + "\n")

    run_hill_climbing()


if __name__ == "__main__":
    main()
