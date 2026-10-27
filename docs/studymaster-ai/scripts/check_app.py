"""Check StudyMaster from a link through a saved pack.

The plain command stays offline. It walks the learner path with a fake
page, then runs the test suite. --live reads one public page only after
those checks pass. It never prints the API key or the page text.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARN = "https://learn.microsoft.com/en-us/entra/fundamentals/whatis"


def main() -> int:
    """Run the offline checks, then the live study when asked."""
    parser = argparse.ArgumentParser(
        description="Check StudyMaster from beginning to end."
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="After the offline checks pass, read one public page.",
    )
    args = parser.parse_args()
    journey = _pytest(["tests/test_end_to_end.py"])
    print("Offline journey: passed" if journey == 0 else "Offline journey: failed")
    if journey != 0:
        return journey
    suite = _pytest([])
    print("Full suite: passed" if suite == 0 else "Full suite: failed")
    if suite != 0:
        return suite
    if not args.live:
        print("Live study: skipped")
        return 0
    return _live()


def _pytest(extra: list[str]) -> int:
    """Run pytest from the project folder. A set database path is ignored."""
    env = os.environ.copy()
    env.pop("DATABASE_PATH", None)
    env.pop("MAX_SOURCE_CHARS", None)
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line", *extra],
        cwd=ROOT,
        env=env,
    )
    return completed.returncode


def _live() -> int:
    """Read one public page and write one pack in a temporary database."""
    from studymaster.config import get_settings
    from studymaster.storage.database import StudyStore
    from studymaster.ui.study_flow import study_page

    current = get_settings()
    if not current.openai_api_key:
        print("Live study: failed. Add OPENAI_API_KEY to the .env file.")
        return 1
    with tempfile.TemporaryDirectory() as folder:
        database = Path(folder) / "live.db"
        outcome = study_page(
            url=LEARN,
            level="Beginner",
            goal="Explain what this page says.",
            minutes=15,
            settings=replace(current, database_path=database),
            store=StudyStore(database),
        )
    if not outcome.ok:
        print(f"Live study: failed. {outcome.message}")
        return 1
    pieces = ", ".join(section.kind for section in outcome.sections)
    print(f"Live study: passed. Saved {outcome.title}. Pieces: {pieces}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
