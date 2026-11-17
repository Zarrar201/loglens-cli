"""
LogLens core logic. Pure functions only: no FastAPI, no database.
That makes it easy to test and easy to explain.
"""
import re
from collections import Counter

# --- Step 1: normalise a log line so similar errors look identical ---
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?Z?\s*")
UUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
IP_ADDRESS = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b")
NUMBER = re.compile(r"\d+")

# A line counts as an error if it contains one of these levels as a whole word.
ERROR_LEVEL = re.compile(r"\b(ERROR|FATAL)\b")


def normalize(line: str) -> str:
    """Replace the changing parts of a log line with placeholders.

    'user 4521 failed from 10.0.0.7'  ->  'user <NUM> failed from <IP>'
    The order matters: UUID and IP must be replaced before plain numbers.
    """
    line = TIMESTAMP.sub("", line.strip())
    line = UUID.sub("<UUID>", line)
    line = IP_ADDRESS.sub("<IP>", line)
    line = NUMBER.sub("<NUM>", line)
    return line


def is_error(line: str) -> bool:
    return ERROR_LEVEL.search(line) is not None


# --- Step 2: count how many times each error pattern appears ---
def count_patterns(lines: list[str]) -> Counter:
    return Counter(normalize(line) for line in lines if is_error(line))


# --- Step 3: compare a baseline (before) with the current (after) ---
def compare(baseline: Counter, current: Counter, spike_factor: float = 3, min_count: int = 3) -> dict:
    """Find error patterns that are new or have spiked.

    min_count ignores rare one-off errors (reduces false alarms).
    spike_factor: the current count must be MORE than this many times the baseline.
    """
    new_patterns = []
    spikes = []

    for pattern, count in current.items():
        if count < min_count:
            continue
        before = baseline.get(pattern, 0)
        if before == 0:
            new_patterns.append({"pattern": pattern, "count": count})
        elif count > spike_factor * before:
            spikes.append({"pattern": pattern, "before": before, "after": count})

    new_patterns.sort(key=lambda item: item["count"], reverse=True)
    spikes.sort(key=lambda item: item["after"], reverse=True)
    return {"new_patterns": new_patterns, "spikes": spikes}
