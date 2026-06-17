"""
level3_event.py — LOOP 3: THE EVENT-DRIVEN LOOP

    [ file dropped in watch_inbox/ ]  --(event)-->  run the verified agent
                                                          |
                                                    write .summary.txt

Concept:
    So far a human ran the agent by hand. Level 3 is where the agent stops being
    a script you run and becomes a service that runs. The trigger is the SYSTEM,
    not the user: here, dropping a .txt file into a watched folder fires the
    whole Level 2 agent (loop + verification) automatically. A new file landing,
    a webhook, a cron tick — same idea.

Self-contained: run it directly, then drop a .txt file into watch_inbox/:

    python level3_event.py
    # ...then in another window:  echo "What is hill climbing?" > watch_inbox/q.txt
"""

import os
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import llm
from level2_verification import run_verified_agent

WATCH_INBOX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watch_inbox")

# Some operating systems fire the "created" event before the file is fully
# written (or fire it twice). A short pause lets the write settle and, combined
# with the _seen set below, prevents processing the same file twice.
DEBOUNCE_SECONDS = 0.5


def handle_topic_file(path):
    """
    The reaction to one event: read the topic, run the verified agent on it,
    and write the answer next to the input file as <name>.summary.txt.

    Args:
        path: Full path to the .txt file that was dropped into the inbox.
    """
    filename = os.path.basename(path)
    print("\n" + "#" * 70)
    print(f"[EVENT] EVENT RECEIVED — new file detected: {filename}")
    print("#" * 70)

    # The file's contents ARE the research topic (one line is enough).
    with open(path, "r", encoding="utf-8") as f:
        topic = f.read().strip()

    if not topic:
        print(f"[EVENT] {filename} is empty — nothing to research. Skipping.")
        return

    print(f"[EVENT] Topic from file: {topic}")

    # Fire the full Level 2 pipeline (agent loop + grading) on the topic.
    result = run_verified_agent(topic)

    # Write the answer beside the input: topic.txt -> topic.summary.txt
    base, _ = os.path.splitext(path)
    summary_path = base + ".summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        verdict = "PASS" if result.passed else "FAIL"
        f.write(f"Topic: {topic}\n")
        f.write(f"Grader verdict: {verdict} (after {result.attempts} attempt(s))\n")
        f.write(f"Feedback: {result.grader_result['feedback']}\n\n")
        f.write(result.summary + "\n")

    print(f"[EVENT] Wrote answer -> {os.path.relpath(summary_path)}")
    print("[EVENT] Still watching. Drop another file to trigger another run.\n")


class TopicFileHandler(FileSystemEventHandler):
    """
    watchdog calls on_created() whenever a file appears in the watched folder.
    We filter to the .txt topic files we care about and ignore the
    .summary.txt files we ourselves write (otherwise we'd trigger on our own
    output — an accidental loop!).
    """

    def __init__(self):
        super().__init__()
        self._seen = set()  # remember paths we've handled, to avoid double-fires

    def on_created(self, event):
        # Ignore directory-creation events.
        if event.is_directory:
            return

        path = event.src_path

        # Only react to topic .txt files — never to our own .summary.txt output.
        if not path.endswith(".txt") or path.endswith(".summary.txt"):
            return

        # De-dupe: some filesystems fire on_created more than once per file.
        if path in self._seen:
            return
        self._seen.add(path)

        time.sleep(DEBOUNCE_SECONDS)  # let the file finish being written
        handle_topic_file(path)


def start_observer():
    """
    Create and start a watchdog observer on the inbox. Returns it so a caller
    (like run_demo.py) can stop it later. The observer runs on its own thread.
    """
    os.makedirs(WATCH_INBOX, exist_ok=True)
    observer = Observer()
    observer.schedule(TopicFileHandler(), WATCH_INBOX, recursive=False)
    observer.start()
    return observer


def main():
    """Run Level 3 on its own: watch the inbox until Ctrl+C."""
    print("=" * 70)
    print("LEVEL 3 — THE EVENT-DRIVEN LOOP")
    print("The agent runs in response to an event, not a human pressing 'run'.")
    print(llm.mode_banner())
    print("=" * 70)
    print(f"\n[EVENT] Watching folder: {os.path.relpath(WATCH_INBOX)}")
    print("[EVENT] Drop a .txt file containing a research topic into that folder")
    print("[EVENT] to trigger the agent. Press Ctrl+C to stop.\n")

    observer = start_observer()
    try:
        # Keep the main thread alive while the observer thread does the watching.
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[EVENT] Stopping the watcher. Goodbye.")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
