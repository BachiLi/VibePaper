#!/usr/bin/env python
"""
Build script for the paper recommender database.

Usage:
    python build.py           # Build everything (database + embeddings)
    python build.py database  # Build only the JSON database
    python build.py embeddings # Build only the embeddings (requires database)
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def run_script(name: str):
    """Run a Python script and stream output."""
    script = SCRIPT_DIR / name
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=SCRIPT_DIR,
    )
    return result.returncode == 0


def main():
    args = sys.argv[1:]

    if not args or "all" in args:
        # Build everything
        print("Building complete database...\n")
        if not run_script("build_database.py"):
            print("\nDatabase build failed!")
            sys.exit(1)
        print("\n" + "-" * 60 + "\n")
        if not run_script("build_embeddings.py"):
            print("\nEmbeddings build failed!")
            sys.exit(1)

    elif "database" in args or "db" in args:
        if not run_script("build_database.py"):
            sys.exit(1)

    elif "embeddings" in args or "emb" in args:
        if not run_script("build_embeddings.py"):
            sys.exit(1)

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
