"""
level1_agent.py — LOOP 1: THE AGENT LOOP

    request --> [ model <--> tools ] --> repeat until done --> result

Concept:
    At its core, an agent is just an LLM in a loop. The model receives a task,
    calls tools, reads the results, and decides what to do next — over and over —
    until it decides it is finished. The MODEL decides when it's done, not the
    programmer. Our code just runs the loop and the tools.

This file is self-contained: read it top to bottom and you understand Level 1.
Run it directly to watch one agent loop execute:

    python level1_agent.py
"""

import json
import os
import sys
from datetime import datetime

import llm
from prompts import RESEARCH_AGENT_SYSTEM_PROMPT
from tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS

# A safety rail. The model decides when to stop — but if it never does (a buggy
# prompt, an infinite tool loop), we cap the number of turns so the demo can't
# run away and rack up cost. 10 is plenty for a single research question.
MAX_ITERATIONS = 10

TRACES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traces")


class AgentResult:
    """The outcome of one full agent loop, passed back to the caller."""

    def __init__(self, summary, messages, iterations):
        self.summary = summary          # the final text answer
        self.messages = messages        # full conversation (for tracing)
        self.iterations = iterations    # how many loop turns it took


def _serialize_content(content):
    """
    Convert the model's response blocks into plain dicts we can store in the
    messages list and write to JSON. This works the same for a real SDK
    response or a mock one, so the loop code below never has to care which.
    """
    out = []
    for block in content:
        if block.type == "text":
            out.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            out.append(
                {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
            )
    return out


def _final_text(content):
    """Join all text blocks in a response into the final answer string."""
    return "\n".join(block.text for block in content if block.type == "text").strip()


def run_agent(topic, feedback=None):
    """
    Run ONE agent loop on a research topic and return the result.

    This is the entire Level 1 idea. Levels 2-4 all build on top of this exact
    function — the verification loop calls it, the event loop triggers it, and
    the hill-climbing loop analyzes the traces it leaves behind.

    Args:
        topic: The research question, e.g. "What is an agentic loop?"
        feedback: Optional grader feedback from a previous failed attempt
            (Level 2 passes this in to make the agent try again, better).

    Returns:
        An AgentResult with the final summary, the full message log, and the
        number of loop iterations it took.
    """
    # Build the opening user message. On a retry, we prepend the grader's note
    # so the model knows what to fix. The literal phrase "GRADER FEEDBACK" is how
    # later turns (and the mock) recognize this is a second attempt.
    if feedback:
        user_text = (
            f"Research this topic and write a summary: {topic}\n\n"
            f"Your previous attempt was rejected. GRADER FEEDBACK: {feedback}\n"
            f"Write a better summary that fixes this."
        )
    else:
        user_text = f"Research this topic and write a summary: {topic}"

    messages = [{"role": "user", "content": user_text}]
    iterations = 0

    # ---- THE LOOP -----------------------------------------------------------
    # while True + a max guard. Each pass is one "turn": ask the model, and if
    # it asked for tools, run them and feed the results back. We exit the moment
    # the model returns plain text with no tool calls — that's "done."
    while True:
        iterations += 1
        print(f"\n  ----- Agent loop iteration {iterations} -----")
        print("[AGENT] Asking the model what to do next...")

        message = llm.create_message(
            system=RESEARCH_AGENT_SYSTEM_PROMPT,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )

        # Record the model's turn in the conversation so it remembers context.
        messages.append({"role": "assistant", "content": _serialize_content(message.content)})

        # Did the model ask to use any tools this turn?
        tool_uses = [block for block in message.content if block.type == "tool_use"]

        # STOP CONDITION: no tool calls means the model is done and gave us text.
        if not tool_uses:
            summary = _final_text(message.content)
            print("[AGENT] No tool call this turn -> the model is DONE.")
            print(f"[AGENT] Final summary:\n         {summary}")
            return AgentResult(summary=summary, messages=messages, iterations=iterations)

        # Otherwise: run every tool the model asked for, collect the results.
        #
        # HUMAN IN THE LOOP (oversight touch point #1): this is the spot where a
        # production agent would PAUSE and ask a person to approve a sensitive
        # action before running it — sending money, deleting a row, opening a PR.
        # Our tools (search, read_file) are read-only and safe, so we just run
        # them. Whenever a tool can change the real world, gate it here.
        tool_results = []
        for tool_use in tool_uses:
            print(f"[TOOL]  Model called '{tool_use.name}' with {tool_use.input}")
            func = TOOL_FUNCTIONS[tool_use.name]
            result = func(**tool_use.input)
            preview = result if len(result) <= 120 else result[:117] + "..."
            print(f"[TOOL]  Result: {preview}")
            # A tool_result block points back to the tool_use it answers, by id.
            tool_results.append(
                {"type": "tool_result", "tool_use_id": tool_use.id, "content": result}
            )

        # Feed all tool results back as the next user turn, then loop again.
        messages.append({"role": "user", "content": tool_results})

        # Safety rail: don't let a misbehaving agent loop forever.
        if iterations >= MAX_ITERATIONS:
            print(f"[AGENT] Hit the {MAX_ITERATIONS}-iteration safety cap — stopping.")
            summary = _final_text(message.content) or "(no final summary — hit iteration cap)"
            return AgentResult(summary=summary, messages=messages, iterations=iterations)


def write_trace(topic, messages, iterations, grader_result=None):
    """
    Save a run to traces/ as JSON for Level 4 (hill climbing) to analyze later.

    The schema is fixed here so every level writes the SAME shape and Level 4
    can rely on it:
        {"topic", "messages", "iterations", "grader_result"}
    grader_result is None for a plain Level 1 run and filled in by Level 2.
    """
    os.makedirs(TRACES_DIR, exist_ok=True)
    trace = {
        "topic": topic,
        "messages": messages,
        "iterations": iterations,
        "grader_result": grader_result,
    }
    # Microseconds in the name so back-to-back runs never overwrite each other.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = os.path.join(TRACES_DIR, f"trace_{timestamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2)
    print(f"[AGENT] Wrote trace -> {os.path.relpath(path)}")
    return path


def main():
    """Run Level 1 on its own so students can watch a single agent loop."""
    print("=" * 70)
    print("LEVEL 1 — THE AGENT LOOP")
    print("An LLM calls tools in a loop until it decides the task is done.")
    print(llm.mode_banner())
    print("=" * 70)

    # Allow a custom topic from the command line; otherwise use the classic one.
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What is an agentic loop?"
    print(f"\nTopic: {topic}")

    result = run_agent(topic)
    write_trace(topic, result.messages, result.iterations, grader_result=None)

    print(f"\n[AGENT] Done in {result.iterations} iteration(s).")


if __name__ == "__main__":
    main()
