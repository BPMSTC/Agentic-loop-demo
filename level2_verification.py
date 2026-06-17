"""
level2_verification.py — LOOP 2: THE VERIFICATION LOOP

    request --> [ AGENT LOOP ] --> result --> grader(rubric)
                     ^                              |
                     |____ retry with feedback _____| (until pass or max retries)

Concept:
    The agent loop from Level 1 will ALWAYS finish — but "finished" doesn't mean
    "good." Level 2 wraps the agent in an outer loop with a grader: a second
    model call that scores the output against a rubric. If it fails, we hand the
    feedback back to the agent and let it try again. This separates *finishing*
    from *quality*.

    Two kinds of grader (the article names both):
      * DETERMINISTIC — plain code: run the tests, check the links resolve, check
        the diff is scoped. Cheap, fast, and not itself fallible. Prefer this
        whenever the quality bar can be expressed as a check.
      * AGENTIC ("LLM as a judge") — a second model call scores the output. Use
        it for fuzzy qualities (clarity, tone) that code can't easily measure.
        Caveat: a model grading a model can share the same blind spots, so keep
        the rubric strict and, for anything that matters, add a human (below).

    This demo uses the agentic kind because "LLM as a judge" is the idea worth
    teaching here. (Fun fact: in mock mode our grader is actually deterministic —
    it fails short/vague summaries by a simple rule — which is a perfect example
    of the first kind.)

    TRADEOFF: every verification pass is another model call, so it adds latency
    and cost. Worth it whenever quality matters more than speed — which, per the
    article, is most production use cases.

    HUMAN IN THE LOOP (oversight touch point #2): for sensitive workflows a human
    can BE the grader, or approve the agentic grader's verdict, instead of
    trusting the model. grade_summary() is exactly where that swap would happen.

Self-contained: run it directly to watch an agent get graded and (if needed)
sent back to improve:

    python level2_verification.py
"""

import argparse

import llm
from level1_agent import run_agent, write_trace
from prompts import GRADER_SYSTEM_PROMPT, STRICT_GRADER_SYSTEM_PROMPT

# How many times we'll send the agent back to improve before giving up. Like the
# agent loop's cap, this keeps a stubborn run from looping (and billing) forever.
MAX_RETRIES = 3

# Strict mode raises the grader's bar (see STRICT_GRADER_SYSTEM_PROMPT). It's off
# by default. We expose it as a module-level toggle so run_demo.py / the level
# files can flip it with --strict, and so BOTH Level 2 and Level 3 (which grades
# through this same function) pick it up. In live mode the model is usually good
# enough to pass on the first try; strict mode reliably forces a fail-then-retry
# so a classroom can watch the verification loop actually loop.
_STRICT = False


def set_strict(strict):
    """Turn the stricter grading rubric on or off (used by the --strict flag)."""
    global _STRICT
    _STRICT = strict


def _grader_system_prompt():
    """Pick the normal or strict rubric depending on the toggle above."""
    return STRICT_GRADER_SYSTEM_PROMPT if _STRICT else GRADER_SYSTEM_PROMPT

# The grader's tool. Forcing the model to answer THROUGH a tool (instead of
# free-form text we'd have to parse) guarantees we get clean, structured data:
# a real boolean and a string. This is the same tool-calling pattern as Level 1,
# reused for a different job — judging instead of researching.
GRADER_TOOL = {
    "name": "submit_grade",
    "description": "Submit the pass/fail verdict and feedback for a research summary.",
    "input_schema": {
        "type": "object",
        "properties": {
            "pass": {
                "type": "boolean",
                "description": "True if the summary meets the rubric, False otherwise.",
            },
            "feedback": {
                "type": "string",
                "description": "One sentence of specific, actionable feedback.",
            },
        },
        "required": ["pass", "feedback"],
    },
}


class VerifiedResult:
    """The outcome of a verification loop: the final summary and how it scored."""

    def __init__(self, summary, grader_result, attempts, passed):
        self.summary = summary                # final summary text
        self.grader_result = grader_result    # {"pass": bool, "feedback": str}
        self.attempts = attempts              # how many agent runs it took
        self.passed = passed                  # did it ultimately pass?


def _collect_search_results(messages):
    """
    Pull every search result out of an agent run so the grader can check the
    summary AGAINST the same facts the agent had. (Accuracy = "did it only use
    what it actually found?") Returns the results joined into one string.
    """
    results = []
    for message in messages:
        if message["role"] == "user" and isinstance(message["content"], list):
            for block in message["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    results.append(block["content"])
    return "\n\n".join(results) if results else "(no search results were recorded)"


def grade_summary(summary, search_results):
    """
    The grader. A separate model call that scores one summary against the rubric
    in GRADER_SYSTEM_PROMPT and returns a structured verdict.

    Args:
        summary: The text the agent produced.
        search_results: The facts the agent had available (for the accuracy check).

    Returns:
        {"pass": bool, "feedback": str}
    """
    grader_input = (
        "Grade this research summary.\n\n"
        f"SUMMARY TO GRADE:\n{summary}\n\n"
        f"SEARCH RESULTS THE AGENT HAD AVAILABLE:\n{search_results}"
    )

    message = llm.create_message(
        system=_grader_system_prompt(),
        messages=[{"role": "user", "content": grader_input}],
        tools=[GRADER_TOOL],
        # Force the model to use submit_grade so we always get structured output.
        tool_choice={"type": "tool", "name": "submit_grade"},
    )

    # The verdict is the input of the submit_grade tool call.
    for block in message.content:
        if block.type == "tool_use" and block.name == "submit_grade":
            return block.input

    # Defensive fallback (shouldn't happen because we forced the tool above).
    return {"pass": False, "feedback": "Grader did not return a verdict."}


def run_verified_agent(topic):
    """
    Run the agent, grade it, and retry with feedback until it passes (or we hit
    MAX_RETRIES). This is the whole Level 2 idea, and the unit that Level 3
    triggers on an event and Level 4 learns from.

    Args:
        topic: The research question.

    Returns:
        A VerifiedResult. Also writes ONE trace (with the grader verdict) for
        Level 4 to analyze.
    """
    feedback = None  # None on the first attempt; the grader's note on retries.
    grade = None

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n  ===== Verification attempt {attempt} of {MAX_RETRIES} =====")

        # Run the Level 1 agent loop (passing feedback in on retries).
        result = run_agent(topic, feedback=feedback)

        # Grade what it produced, against the facts it actually had.
        search_results = _collect_search_results(result.messages)
        print("[GRADER] Scoring the summary against the rubric...")
        grade = grade_summary(result.summary, search_results)

        verdict = "PASS" if grade["pass"] else "FAIL"
        print(f"[GRADER] Verdict: {verdict}")
        print(f"[GRADER] Feedback: {grade['feedback']}")

        if grade["pass"]:
            # Success — record the trace (with the verdict) and return.
            write_trace(topic, result.messages, result.iterations, grader_result=grade)
            print(f"[GRADER] Passed on attempt {attempt}.")
            return VerifiedResult(result.summary, grade, attempt, passed=True)

        # Failed: carry the feedback into the next attempt so the agent improves.
        print("[GRADER] Sending the agent back to try again with this feedback.")
        feedback = grade["feedback"]

    # Ran out of retries. Record the last attempt anyway — a FAIL trace is useful
    # signal for Level 4 (it's a pattern worth learning from).
    write_trace(topic, result.messages, result.iterations, grader_result=grade)
    print(f"[GRADER] Did not pass after {MAX_RETRIES} attempts.")
    return VerifiedResult(result.summary, grade, MAX_RETRIES, passed=False)


def main():
    """Run Level 2 on its own so students can watch the grade/retry cycle."""
    parser = argparse.ArgumentParser(description="Run the verification loop on a topic.")
    parser.add_argument("topic", nargs="*", help="The research topic (optional).")
    parser.add_argument(
        "--strict", action="store_true",
        help="Use the stricter rubric so the first draft usually fails and retries.",
    )
    args = parser.parse_args()
    if args.strict:
        set_strict(True)

    print("=" * 70)
    print("LEVEL 2 — THE VERIFICATION LOOP")
    print("Wrap the agent in a grader: finishing is not the same as being correct.")
    print(llm.mode_banner())
    if _STRICT:
        print("[GRADER] STRICT mode: requires plain prose (no markdown) AND a stated tradeoff.")
    print("=" * 70)

    topic = " ".join(args.topic) if args.topic else "What is a verification loop?"
    print(f"\nTopic: {topic}")

    result = run_verified_agent(topic)

    print("\n" + "-" * 70)
    print(f"[GRADER] Final verdict: {'PASS' if result.passed else 'FAIL'} "
          f"after {result.attempts} attempt(s).")
    print(f"[GRADER] Final summary:\n  {result.summary}")


if __name__ == "__main__":
    main()
