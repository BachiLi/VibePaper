"""Shared read/write helpers with file locking for all_papers_enriched.json."""

import json
import msvcrt
import time
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "all_papers_enriched.json"

MAX_RETRIES = 10
RETRY_DELAY = 0.5  # seconds


def load_papers(path=DATA_FILE):
    """Load papers with file locking and retry."""
    for attempt in range(MAX_RETRIES):
        try:
            with open(path, "r", encoding="utf-8") as f:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                try:
                    data = json.load(f)
                finally:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                return data
        except (OSError, PermissionError) as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError(f"Failed to read {path} after {MAX_RETRIES} attempts: {e}")


def save_papers(papers, path=DATA_FILE):
    """Save papers with file locking and retry."""
    for attempt in range(MAX_RETRIES):
        try:
            with open(path, "w", encoding="utf-8") as f:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                try:
                    json.dump(papers, f, ensure_ascii=False)
                finally:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                return
        except (OSError, PermissionError) as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise RuntimeError(f"Failed to write {path} after {MAX_RETRIES} attempts: {e}")
