"""
tools.py — The tools the agent can call, plus their schemas.

A "tool" is just a normal Python function. The only special part is the SCHEMA
(see TOOL_DEFINITIONS at the bottom): a JSON description we hand to the model so
it knows the tool exists, what it does, and what arguments it takes. The model
never runs your code — it just *asks* for a tool by name, and OUR loop runs the
function and feeds the result back. That hand-off is the heart of an agent.

The search tool here is SIMULATED — it returns canned, plausible text so the
demo runs offline with no search API key. The single line you'd change to make
it real is marked below.
"""

import os

# Folder that the search tool / read_file pretend to "know about."
# Level 3 drops .txt files here, and read_file can pull them back.
WATCH_INBOX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watch_inbox")


# A tiny "knowledge base." Real search hits the web; we key off topic keywords
# so common demo questions get a sensible paragraph back. Anything unknown gets
# a generic-but-plausible result so the loop still has something to chew on.
_FAKE_RESULTS = {
    "agentic loop": (
        "An agentic loop is the core pattern behind AI agents: a language model is "
        "given a task and a set of tools, and it calls those tools in a loop until it "
        "decides the task is complete. Each turn the model reads the latest results, "
        "decides the next action, and either calls another tool or returns a final "
        "answer. Crucially, the MODEL decides when to stop — the loop is open-ended, "
        "not a fixed number of steps. Sydney Runkle describes four levels: the agent "
        "loop, a verification loop that grades output, an event-driven loop triggered "
        "by your systems, and a hill-climbing loop that improves the agent itself."
    ),
    "verification": (
        "A verification loop wraps an agent with a grader that scores the output "
        "against a rubric. If the output fails, the feedback is sent back to the agent "
        "for another attempt. Graders can be deterministic (run tests) or agentic "
        "('LLM as a judge'). The tradeoff is latency and cost per run in exchange for "
        "more consistent, correct results — worth it whenever quality matters more "
        "than raw speed, which covers most production use cases."
    ),
    "event": (
        "An event-driven agent does not wait for a human to press 'run.' Instead it is "
        "wired into a system — a new file lands, a webhook arrives, a schedule fires — "
        "and that event triggers the agent. This turns an agent from a script you run "
        "into a service that runs continuously inside a larger system, reacting to the "
        "world as things happen."
    ),
    "hill climbing": (
        "A hill-climbing loop closes the loop on the loops: every agent run emits a "
        "trace of what it did, and a meta-agent analyzes those traces to improve the "
        "harness itself — usually by rewriting the system prompt or tweaking tools. "
        "Each generation of runs becomes training signal for the next, so the system "
        "compounds: it gets better the more it is used. Human review before deploying "
        "the improvement keeps a person in the loop."
    ),
    "python": (
        "Python is a high-level, general-purpose programming language known for "
        "readable syntax and a large standard library. It is widely used for AI and "
        "data work because of libraries like the Anthropic SDK, NumPy, and pandas. "
        "Python uses indentation to define blocks and is dynamically typed."
    ),
}


def search(query: str) -> str:
    """
    Pretend to search the web and return a short paragraph of results.

    In a real agent this would call Brave / Tavily / SerpAPI and return live
    snippets. We keep it fake so the demo needs no second API key and gives the
    same answer every time (great for teaching — the loop is reproducible).

    Args:
        query: The natural-language search query the model chose.

    Returns:
        A short paragraph of plausible "search results" as plain text.
    """
    # --- THIS is the one line you would swap for a real search call ---------
    #   return real_search_api(query)["summary"]
    # -----------------------------------------------------------------------

    # Match the query against our fake knowledge base by keyword. We lowercase
    # and look for any known topic as a substring so "What is an agentic loop?"
    # still matches the "agentic loop" entry.
    q = query.lower()
    for keyword, result in _FAKE_RESULTS.items():
        if keyword in q:
            return result

    # Fallback for any topic we did not pre-write: still plausible, so the agent
    # has real text to summarize instead of an error.
    return (
        f"Search results for '{query}': This topic covers several key ideas that "
        f"experts generally agree on. The most important point is that '{query}' is "
        f"best understood through concrete examples and clear definitions rather than "
        f"abstract description. Multiple reputable sources describe its core principles, "
        f"common use cases, and the trade-offs involved in applying it in practice."
    )


def read_file(filename: str) -> str:
    """
    Read a .txt file from the watch_inbox/ folder (used by Level 3).

    Args:
        filename: A bare filename like "topic.txt" (no path). We deliberately
            join it onto WATCH_INBOX rather than trusting an absolute path, so
            the tool can only read from the one folder it is meant to.

    Returns:
        The file's text contents, or a clear error string the model can read.
    """
    # Use only the base name so the model can't escape the inbox folder
    # (e.g. by passing "../secrets.txt"). Small, but worth showing students.
    safe_name = os.path.basename(filename)
    path = os.path.join(WATCH_INBOX, safe_name)
    if not os.path.exists(path):
        return f"ERROR: No file named '{safe_name}' exists in watch_inbox/."
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


# ---------------------------------------------------------------------------
# A registry so the loop can look up the Python function by the name the model
# asked for. The model says "call search"; we map that string to search().
# ---------------------------------------------------------------------------
TOOL_FUNCTIONS = {
    "search": search,
    "read_file": read_file,
}


# ---------------------------------------------------------------------------
# TOOL DEFINITIONS — the schemas we pass to client.messages.create(tools=...).
# This is the model's "menu." Each entry's name must match a key in
# TOOL_FUNCTIONS above. input_schema is JSON Schema describing the arguments.
# ---------------------------------------------------------------------------
TOOL_DEFINITIONS = [
    {
        "name": "search",
        "description": (
            "Search the web for information about a topic. Returns a short "
            "paragraph of results. Call this whenever you need facts you do "
            "not already have."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query, phrased as you would type it into a search engine.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a .txt file from the watch_inbox folder by its filename. "
            "Use this to load a research topic that was dropped into the inbox."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "The bare filename to read, e.g. 'topic.txt'.",
                }
            },
            "required": ["filename"],
        },
    },
]
