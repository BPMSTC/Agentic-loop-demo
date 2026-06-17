"""
prompts.py — Every system prompt the demo uses, in one editable place.

Why a separate file? Because in Level 4 (hill climbing) the agent analyzes its
own past runs and proposes a *better* RESEARCH_AGENT_SYSTEM_PROMPT. Keeping the
prompts here — as plain named strings — makes it obvious to students that "the
prompt" is just data. You can read it, diff it, and improve it like any other
artifact. That is the whole point of Level 4.

Nothing in here is magic. These are the instructions we hand to the model.
"""

# ---------------------------------------------------------------------------
# LEVEL 1 — the research agent's instructions.
# This is the prompt Level 4 will try to improve. Keep it intentionally a
# little plain so the hill-climbing loop has something to sharpen.
# ---------------------------------------------------------------------------
RESEARCH_AGENT_SYSTEM_PROMPT = """\
You are a research assistant. Your job is to answer a research question thoroughly.
Use the search tool to find relevant information. Keep searching until you have enough
to write a clear, specific, 3-5 sentence summary. Do not guess — only include
information you retrieved from search results.\
"""


# ---------------------------------------------------------------------------
# LEVEL 2 — the grader's instructions (the "rubric").
# The grader is a SECOND call to the model with a different job: judge the
# first model's output. This is the "LLM as a judge" pattern from the article.
# ---------------------------------------------------------------------------
GRADER_SYSTEM_PROMPT = """\
You are a quality grader for research summaries. You will receive a summary and the
search results that were available to the agent. Score the summary on:
- Completeness: Does it fully answer the question?
- Accuracy: Does it only reference information from the search results?
- Clarity: Is it specific and easy to understand (no vague language)?

Be strict. A one-or-two sentence summary, or one full of vague phrases like
"various aspects" or "many things," should FAIL. Use the submit_grade tool to
return your verdict and one sentence of actionable feedback.\
"""


# ---------------------------------------------------------------------------
# LEVEL 4 — the meta-agent's instructions.
# This agent never touches the search tool. Its "input" is a digest of past
# runs (traces), and its "output" is a rewritten RESEARCH_AGENT_SYSTEM_PROMPT.
# The agent is improving the agent.
# ---------------------------------------------------------------------------
META_IMPROVER_SYSTEM_PROMPT = """\
You are a prompt engineer improving an AI research agent. You will be given the
agent's CURRENT system prompt and a digest of its recent runs (the topic, how many
loop iterations it took, whether a quality grader passed it, and the grader's
feedback).

Look for patterns: What kinds of failures repeat? Where is the agent inefficient
(too many loops) or sloppy (failing the grader)? Then write an improved system
prompt that would fix those patterns.

Respond with ONLY the improved system prompt text — no preamble, no explanation,
no markdown fences. It must be a drop-in replacement for the current prompt.\
"""
