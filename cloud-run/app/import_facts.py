"""One-time import of the profile's facts seed file into Firestore (ADR-21, ADR-23). Run from
cloud-run/:

uv run python -m app.import_facts --publish

The seed is `facts.yaml` in the profile folder: PROFILE_DIR if set, else `profile/` at the repo
root, else the fake sample in `profile.example/`. Pass a path to import another file.

Only `reviewed: true` entries are imported. The rest are listed so Lee can finish them in admin.
It refuses to run once any facts or versions exist, so it can't overwrite Lee's admin edits.
With --publish, the imported set goes live as version 1.
"""

import argparse
import os
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.facts import SECTIONS, FactInput, create_fact, publish
from app.store import get_db

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED_NAME = "facts.yaml"


def profile_dir() -> Path:
    if configured := os.environ.get("PROFILE_DIR"):
        return Path(configured)
    real = REPO_ROOT / "profile"
    return real if real.is_dir() else REPO_ROOT / "profile.example"


def default_seed() -> Path:
    return profile_dir() / SEED_NAME


def _text(value: object) -> str:
    # YAML folded blocks keep line breaks and a trailing newline.
    return " ".join(str(value or "").split())


def read_seed(path: Path) -> tuple[list[FactInput], list[str]]:
    """Returns (reviewed facts, topics skipped as unreviewed)."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    reviewed, skipped = [], []
    for section in SECTIONS:
        for entry in data.get(section) or ():
            topic = _text(entry.get("topic"))
            if entry.get("reviewed") is not True:
                skipped.append(topic)
                continue
            stories = [
                {
                    key: _text(story.get(key))
                    for key in ("title", "situation", "task", "action", "result")
                }
                for story in entry.get("stories") or ()
            ]
            reviewed.append(
                FactInput(
                    section=section,
                    topic=topic,
                    level=_text(entry.get("level")),
                    verified=_text(entry.get("verified")),
                    limits=_text(entry.get("limits")),
                    stories=stories,
                )
            )
    return reviewed, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("path", type=Path, nargs="?", help="Default: the profile's facts.yaml")
    parser.add_argument("--publish", action="store_true", help="Publish the import as version 1")
    args = parser.parse_args()

    path = args.path or default_seed()
    print(f"Importing {path}")
    if path.resolve().parent == (REPO_ROOT / "profile.example").resolve():
        print("This is the fake sample profile. Set PROFILE_DIR or add profile/ for a real one.")

    db = get_db()
    if any(db.collection("facts").limit(1).stream()) or any(
        db.collection("fact_versions").limit(1).stream()
    ):
        sys.exit("Facts already exist. Edit them in admin instead of importing again.")

    try:
        reviewed, skipped = read_seed(path)
    except ValidationError as error:
        sys.exit(f"The seed file has an invalid entry:\n{error}")

    for fact in reviewed:
        create_fact(db, fact)
    print(f"Imported {len(reviewed)} reviewed facts.")
    if skipped:
        print("Skipped as unreviewed (add them in admin when ready):")
        for topic in skipped:
            print(f"  - {topic}")
    if args.publish:
        print(f"Published as version {publish(db)}.")
    else:
        print("Nothing is live yet. Publish from the admin Facts page.")


if __name__ == "__main__":
    main()
