"""
run_demo.py — Run all four loops back to back, with narration.

This is the classroom entry point. One command walks students up the ladder:

    Level 1  the agent loop          (it finishes)
    Level 2  + verification          (it finishes *and* it's good)
    Level 3  + an event trigger      (it runs without you)
    Level 4  + hill climbing         (it improves itself)

Usage:
    python run_demo.py            # uses your API key if present, else mock mode
    python run_demo.py --mock     # force offline mock mode (free, deterministic)

Each level is also runnable on its own (python level1_agent.py, etc.).
"""

import argparse
import os
import time

import llm  # imported first so we can flip on --mock before anything else runs


def banner(title):
    """Print a big section header so each level is easy to spot in the scroll."""
    print("\n\n" + "#" * 70)
    print("#  " + title)
    print("#" * 70)


def transition(text):
    """Print the instructor's voice-over between levels."""
    print("\n" + "-" * 70)
    print(">> " + text)
    print("-" * 70)


def wait_for_user(auto):
    """Pause between levels so an instructor can talk. --mock/-y skips the pause."""
    if auto:
        time.sleep(1)
        return
    try:
        input("\n(Press Enter to continue to the next level...)")
    except EOFError:
        # No interactive terminal (e.g. piped) — just keep going.
        pass


def main():
    parser = argparse.ArgumentParser(description="Run the 4-level agentic loop demo.")
    parser.add_argument(
        "--mock", action="store_true",
        help="Force offline mock mode (no API key, free, deterministic).",
    )
    parser.add_argument(
        "-y", "--yes", action="store_true",
        help="Don't pause for Enter between levels (good for a hands-off run).",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Stricter grader so L2/L3 usually fail once and retry (visible loop).",
    )
    args = parser.parse_args()

    if args.mock:
        llm.set_mock(True)
    # Auto-advance (no Enter prompts) whenever we're in mock mode or -y was given.
    auto = args.yes or llm.is_mock_mode()

    # ---- Title ------------------------------------------------------------
    print("=" * 70)
    print("  THE ART OF LOOP ENGINEERING — A 4-LEVEL AGENTIC LOOP DEMO")
    print("  Based on Sydney Runkle's 'The Art of Loop Engineering'")
    print("=" * 70)
    print("  We'll build up an agent in four stages, each adding one loop:")
    print("    L1 Agent loop  ->  L2 Verification  ->  L3 Event-driven  ->  L4 Hill climbing")
    print()
    print("  " + llm.mode_banner())
    if args.strict:
        print("  [STRICT] Grader requires plain prose (no markdown) AND a stated tradeoff —")
        print("           expect L2/L3 to fail once and retry (the loop, made visible).")
    print("=" * 70)

    # We import the levels AFTER setting mock mode so everything sees the choice.
    from level1_agent import run_agent, write_trace
    import level2_verification
    from level2_verification import run_verified_agent
    import level3_event
    from level4_hill_climbing import run_hill_climbing

    # Strict grading (if requested) applies to both L2 and L3, since L3 grades
    # through the same verification function.
    if args.strict:
        level2_verification.set_strict(True)

    # ===================================================================
    # LEVEL 1 — the agent loop
    # ===================================================================
    banner("LEVEL 1 — THE AGENT LOOP")
    print("An LLM calls tools in a loop until IT decides the task is done.\n")
    topic1 = "What is an agentic loop?"
    print(f"Topic: {topic1}")
    result1 = run_agent(topic1)
    write_trace(topic1, result1.messages, result1.iterations, grader_result=None)

    transition(
        "That was Level 1. The agent completed — but we never checked whether the "
        "answer was any GOOD. 'Done' isn't 'correct.' Let's add a verification loop."
    )
    wait_for_user(auto)

    # ===================================================================
    # LEVEL 2 — verification loop
    # ===================================================================
    banner("LEVEL 2 — THE VERIFICATION LOOP")
    print("Wrap the agent in a grader. If the output fails the rubric, send it back.\n")
    topic2 = "What is a verification loop?"
    print(f"Topic: {topic2}")
    run_verified_agent(topic2)

    transition(
        "Level 2 adds a quality gate: the agent gets sent back until it passes. "
        "But we still had to run it by hand. Now let's make it EVENT-DRIVEN."
    )
    wait_for_user(auto)

    # ===================================================================
    # LEVEL 3 — event-driven loop
    # ===================================================================
    banner("LEVEL 3 — THE EVENT-DRIVEN LOOP")
    print("Watch a folder. Dropping a file in fires the whole verified agent.")
    print("(The file-drop is a stand-in for a webhook, a cron tick, or a queue —")
    print(" any system event that should trigger the agent without a human.)\n")

    observer = level3_event.start_observer()
    print(f"[EVENT] Watching {os.path.relpath(level3_event.WATCH_INBOX)} ...")
    time.sleep(1)

    # Instead of asking a human to drop a file, the demo drops one for you to
    # show the trigger firing. In real life this file would arrive from a user,
    # an upload, a webhook, etc.
    drop_topic = "What is an event-driven agent loop?"
    drop_path = os.path.join(level3_event.WATCH_INBOX, "demo_topic.txt")
    summary_path = os.path.splitext(drop_path)[0] + ".summary.txt"
    print(f"[EVENT] (demo) Dropping a file into the inbox to simulate the event...")
    with open(drop_path, "w", encoding="utf-8") as f:
        f.write(drop_topic + "\n")

    # Wait for the handler (running on the observer's thread) to finish, which we
    # detect by its output file appearing. Poll instead of guessing a sleep time.
    deadline = time.time() + 30
    while time.time() < deadline and not os.path.exists(summary_path):
        time.sleep(0.5)
    time.sleep(0.5)  # let the final write flush

    observer.stop()
    observer.join()

    transition(
        "Level 3 ran with no human pressing 'go' — the system triggered it. "
        "Finally, let's close the loop on the loops and let the agent IMPROVE itself."
    )
    wait_for_user(auto)

    # ===================================================================
    # LEVEL 4 — hill climbing loop
    # ===================================================================
    banner("LEVEL 4 — THE HILL CLIMBING LOOP")
    print("A meta-agent reads the traces we just generated and proposes a better prompt.\n")
    run_hill_climbing()

    # ---- Wrap up ----------------------------------------------------------
    print("\n\n" + "=" * 70)
    print("  DEMO COMPLETE — you just watched four loops stack:")
    print("    L1 automates work")
    print("    L2 ensures quality")
    print("    L3 runs on events, at scale")
    print("    L4 improves the system over time")
    print()
    print("  The article's punchline: the real leverage is in loops 3 and 4, where")
    print("  value COMPOUNDS — agents embedded in your systems that keep getting")
    print("  better from their own traces. Loops 1-2 are table stakes.")
    print()
    print("  Look in traces/ and improved_prompts/ to see what the run produced.")
    print("  Next: review the L4 suggestion, apply it to prompts.py, and re-run to")
    print("  close the hill-climbing loop yourself. (See INSTRUCTOR_GUIDE.md.)")
    print("=" * 70)


if __name__ == "__main__":
    main()
