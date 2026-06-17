"""
llm.py — One wrapper around the model call, shared by all four levels.

Why this file exists:
  1. ONE place defines which model we use (see MODEL below).
  2. ONE function, create_message(), makes the actual call — so Levels 1-4 never
     repeat client setup and stay focused on their *loop logic*.
  3. MOCK MODE. If there is no API key, this file returns canned responses that
     look EXACTLY like a real Anthropic SDK response (same .content blocks, same
     .stop_reason). That means the level code is identical whether you are
     hitting the real API or running offline in class. The loop is the lesson;
     the wrapper just decides who answers.

Read create_message() first, then the _mock_* helpers if you're curious how the
fake responses are built.
"""

import os
import sys

# Make sure printed output (em dashes, arrows, etc.) renders cleanly on Windows,
# where the default console/pipe encoding can be cp1252 instead of UTF-8. Every
# level imports llm, so doing this once here covers the whole demo.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass  # older/unusual stdout that can't be reconfigured — not fatal

# python-dotenv is optional — if it's installed we load .env so ANTHROPIC_API_KEY
# is available. If it isn't installed, we just skip it (mock mode still works).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# ---------------------------------------------------------------------------
# THE MODEL. Defined once, used everywhere.
#
# We use Haiku for the demo: it is fast and cheap, which matters when a loop
# may call the model many times. To trade cost for quality, swap this for a
# Sonnet or Opus id — every level picks the change up automatically.
#
#   Faster/cheaper : claude-haiku-4-5      (what we use)
#   Smarter        : claude-sonnet-4-6
#   Smartest       : claude-opus-4-8
#
# (The original spec pinned claude-3-5-haiku-20241022; we use the current-gen
# Haiku instead so the demo reflects how you'd really build this today.)
# ---------------------------------------------------------------------------
MODEL = "claude-haiku-4-5"


# Set to True to force mock mode even when a key is present (e.g. for testing).
# run_demo.py / the level files flip this on when you pass --mock.
_FORCE_MOCK = False


def set_mock(force: bool) -> None:
    """Force mock mode on/off from the outside (used by the --mock flag)."""
    global _FORCE_MOCK
    _FORCE_MOCK = force


def is_mock_mode() -> bool:
    """
    Decide whether we run with canned responses instead of the real API.

    Mock mode is ON when either:
      * --mock was requested (set_mock(True)), or
      * there is no usable ANTHROPIC_API_KEY in the environment.

    This is what lets the demo run in a classroom with zero setup.
    """
    if _FORCE_MOCK:
        return True
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    # Treat the placeholder from .env.example as "no key."
    return key == "" or key == "your_key_here"


def mode_banner() -> str:
    """A short, loud label so students always know which mode they're in."""
    if is_mock_mode():
        return "[MOCK MODE] No API key in use — responses are canned (free, offline)."
    return f"[LIVE MODE] Calling the real Anthropic API with model '{MODEL}'."


# ---------------------------------------------------------------------------
# In MOCK mode we hand back objects shaped exactly like the real SDK's response
# so the level code can't tell the difference. A real response has:
#   message.content      -> list of blocks
#   block.type           -> "text" or "tool_use"
#   block.text           -> (text blocks)
#   block.id/.name/.input-> (tool_use blocks)
#   message.stop_reason  -> "end_turn" or "tool_use"
# These two tiny classes reproduce that shape.
# ---------------------------------------------------------------------------
class _Block:
    """One content block — either a chunk of text or a request to use a tool."""

    def __init__(self, type, text=None, id=None, name=None, input=None):
        self.type = type
        self.text = text
        self.id = id
        self.name = name
        self.input = input


class _Message:
    """A whole model response: a list of blocks plus why it stopped."""

    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


# Cache the real client so we only build it once.
_client = None


def _get_client():
    """Lazily create the real Anthropic client (only needed in live mode)."""
    global _client
    if _client is None:
        try:
            import anthropic
        except ImportError:
            sys.exit(
                "The 'anthropic' package isn't installed. Run:\n"
                "    pip install -r requirements.txt\n"
                "Or run the demo in mock mode (remove your API key / pass --mock)."
            )
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the env
    return _client


def create_message(system, messages, tools=None, tool_choice=None, max_tokens=1024):
    """
    The single call every level uses to talk to the model.

    In LIVE mode this is a thin pass-through to client.messages.create().
    In MOCK mode it returns a hand-built response of the same shape.

    Args:
        system: The system prompt string (the agent's instructions).
        messages: The running conversation (list of {"role", "content"} dicts).
        tools: Optional list of tool schemas the model may call.
        tool_choice: Optional dict forcing a particular tool (used by the grader).
        max_tokens: Cap on the response length.

    Returns:
        An object with .content (list of blocks) and .stop_reason — real or mock.
    """
    if is_mock_mode():
        return _mock_create_message(system, messages, tools, tool_choice)

    # ---- LIVE: the real API call. This is the entire "agent step." ----------
    client = _get_client()
    kwargs = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
    if tool_choice:
        kwargs["tool_choice"] = tool_choice
    return client.messages.create(**kwargs)


# ===========================================================================
# MOCK IMPLEMENTATION
# The fake "brain." It reads the conversation and the system prompt to decide
# what a sensible model WOULD do next, then returns it in SDK shape. It is
# deliberately simple and deterministic so the demo is reproducible in class.
# ===========================================================================
def _mock_create_message(system, messages, tools, tool_choice):
    """
    Route to the right canned behavior based on which agent is calling.

    We match on each prompt's unique OPENING identity line ("You are a ...").
    Matching on a looser phrase is risky: the meta prompt, for example, also
    mentions "a quality grader" in passing, so a substring check would misroute
    it. The opening line is the reliable signal.
    """
    s = system.lower()
    if s.startswith("you are a quality grader"):
        return _mock_grader(messages)
    if s.startswith("you are a prompt engineer"):
        return _mock_meta_improver()
    # Default: the research agent (Level 1's loop).
    return _mock_research_agent(messages)


def _first_user_text(messages):
    """Pull the topic out of the first user message."""
    for m in messages:
        if m["role"] == "user":
            return _text_of(m["content"])
    return ""


def _clean_topic(messages):
    """
    Get just the research topic for a tidy mock search query — without the
    "Research this topic..." wrapper or any grader-feedback that run_agent
    appends on a retry. A real model would choose a clean query too.
    """
    text = _first_user_text(messages)
    first_line = text.splitlines()[0] if text else ""
    marker = "summary:"
    if marker in first_line:
        first_line = first_line.split(marker, 1)[1]
    return first_line.strip()


def _text_of(content):
    """Flatten a message's content (str or list of blocks) to plain text."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def _latest_tool_result(messages):
    """Return the text of the most recent tool_result, or '' if none yet."""
    for m in reversed(messages):
        if m["role"] == "user" and isinstance(m["content"], list):
            for block in m["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    return block.get("content", "")
    return ""


def _has_feedback(messages):
    """True once the verification loop has fed grader feedback back in."""
    for m in messages:
        if m["role"] == "user" and "GRADER FEEDBACK" in _text_of(m["content"]):
            return True
    return False


def _mock_research_agent(messages):
    """
    Mock of the Level 1 agent's decision each turn:
      * No search done yet  -> ask to call search (a tool_use block).
      * Search results in   -> write the summary and stop (a text block).

    On the FIRST attempt the summary is deliberately thin and vague so the
    Level 2 grader fails it. After feedback comes back, we write a specific,
    grounded summary that passes. That's how students see the loop converge.
    """
    search_results = _latest_tool_result(messages)

    if not search_results:
        # Turn 1: request a search. stop_reason "tool_use" tells the loop to run it.
        block = _Block(
            type="tool_use",
            id="mock_tool_1",
            name="search",
            input={"query": _clean_topic(messages)},
        )
        return _Message(content=[block], stop_reason="tool_use")

    # Turn 2: we have results — summarize and finish (stop_reason "end_turn").
    if _has_feedback(messages):
        # Improved attempt: ground a specific 3-4 sentence summary in the results.
        sentences = [s.strip() for s in search_results.split(". ") if s.strip()]
        detailed = ". ".join(sentences[:4]).rstrip(".") + "."
        summary = (
            f"Based on the search results: {detailed} In short, this gives a clear, "
            f"specific answer grounded only in what the search returned."
        )
    else:
        # First, weak attempt: short and vague on purpose (the grader will fail it).
        # Deliberately topic-neutral filler so students see WHY it fails the rubric.
        summary = (
            "This topic involves various aspects and a number of different things. "
            "It is generally useful in many ways and touches on many areas."
        )
    return _Message(content=[_Block(type="text", text=summary)], stop_reason="end_turn")


def _mock_grader(messages):
    """
    Mock of the Level 2 grader. It reads the summary it was handed and FAILS
    anything short or full of vague filler; otherwise it PASSES. Returns the
    verdict via the submit_grade tool, exactly like the live grader does.
    """
    submitted = _first_user_text(messages)
    vague_markers = ("various", "many aspects", "different ways", "many things")
    is_vague = any(marker in submitted.lower() for marker in vague_markers)
    too_short = len(submitted.split()) < 35

    if is_vague or too_short:
        verdict = {
            "pass": False,
            "feedback": (
                "Too short and vague — add specific details and concrete examples "
                "drawn directly from the search results."
            ),
        }
    else:
        verdict = {
            "pass": True,
            "feedback": "Clear, specific, and grounded in the search results.",
        }

    block = _Block(
        type="tool_use",
        id="mock_grade_1",
        name="submit_grade",
        input=verdict,
    )
    return _Message(content=[block], stop_reason="tool_use")


def _mock_meta_improver():
    """
    Mock of the Level 4 meta-agent: returns a rewritten research-agent system
    prompt that targets the failure pattern (vague, too-short first drafts).
    """
    improved = (
        "You are a research assistant. Answer the research question with a specific, "
        "well-supported summary.\n\n"
        "Process:\n"
        "1. Use the search tool to gather facts. Search again if the first results "
        "are thin — but avoid more than 2-3 searches for a single question.\n"
        "2. Write a 3-5 sentence summary that includes at least one concrete detail "
        "or example taken directly from the search results.\n\n"
        "Rules:\n"
        "- Never use vague filler like 'various aspects', 'many things', or 'different "
        "ways'. Name the actual aspects.\n"
        "- Only state facts that appear in your search results. Do not guess.\n"
        "- Lead with the direct answer to the question, then add supporting detail."
    )
    return _Message(content=[_Block(type="text", text=improved)], stop_reason="end_turn")
