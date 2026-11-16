"""Lee's facts: a working set Lee edits, and numbered published versions (ADR-19, ADR-21).

Firestore layout:
- `facts/{id}`: the working set, which is what admin edits. Anything not yet published is a draft.
- `fact_versions/{number}`: a published snapshot of the whole working set.
- `fact_meta/current`: `{"version": n}`, the live version.

Only published versions ever reach the agent. Facts are Lee's own content, not visitor data,
so they have no `delete_at`. Everything published is treated as public (ADR-7).
"""

from datetime import UTC, datetime, timedelta
from typing import Literal

from google.cloud import firestore
from pydantic import BaseModel, ConfigDict, Field

# Prompt order in the agent. `not_skills` is what Lee doesn't have, so a "no" is stated (ADR-19).
SECTIONS = ("profile", "experience", "skills", "spoken_languages", "education", "not_skills")
Section = Literal["profile", "experience", "skills", "spoken_languages", "education", "not_skills"]

Text = Field(default="", max_length=2000)


class Story(BaseModel):
    """One STAR story, told in this order when a visitor asks for an example."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    situation: str = Text
    task: str = Text
    action: str = Text
    result: str = Text


class FactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: Section
    topic: str = Field(min_length=1, max_length=200)
    level: str = Field(default="", max_length=200)
    verified: str = Text
    limits: str = Text
    stories: list[Story] = Field(default_factory=list, max_length=10)


FACT_FIELDS = ("section", "topic", "level", "verified", "limits", "stories")


def _facts(db: firestore.Client):
    return db.collection("facts")


def _versions(db: firestore.Client):
    return db.collection("fact_versions")


def _meta(db: firestore.Client):
    return db.collection("fact_meta").document("current")


def _version_id(number: int) -> str:
    # Zero-padded, so document IDs sort by number.
    return f"{number:06d}"


def _public(doc_id: str, data: dict) -> dict:
    return {
        "id": doc_id,
        **{key: data.get(key, "" if key != "stories" else []) for key in FACT_FIELDS},
    }


def _sort_key(data: dict) -> tuple:
    section = data.get("section")
    return (SECTIONS.index(section) if section in SECTIONS else len(SECTIONS), data["created_at"])


def _working(snapshots) -> list[dict]:
    docs = sorted(((s.id, s.to_dict()) for s in snapshots), key=lambda pair: _sort_key(pair[1]))
    return [_public(doc_id, data) for doc_id, data in docs]


def list_working(db: firestore.Client) -> list[dict]:
    return _working(_facts(db).stream())


def list_versions(db: firestore.Client) -> list[dict]:
    return [
        {"number": v["number"], "publishedAt": v["published_at"].isoformat(), "facts": v["facts"]}
        for v in (s.to_dict() for s in _versions(db).order_by("number").stream())
    ]


def facts_state(db: firestore.Client) -> dict:
    return {"working": list_working(db), "versions": list_versions(db)}


def create_fact(db: firestore.Client, fact: FactInput) -> str:
    ref = _facts(db).document()
    ref.set({**fact.model_dump(), "created_at": datetime.now(UTC)})
    return ref.id


def update_fact(db: firestore.Client, fact_id: str, fact: FactInput) -> bool:
    ref = _facts(db).document(fact_id)
    if not ref.get().exists:
        return False
    ref.update(fact.model_dump())
    return True


def delete_fact(db: firestore.Client, fact_id: str) -> None:
    _facts(db).document(fact_id).delete()


@firestore.transactional
def _publish(transaction, db: firestore.Client, restore_number: int | None) -> int | None:
    # Every read comes before any write, as Firestore transactions require.
    meta = _meta(db).get(transaction=transaction).to_dict() or {}
    # A transaction reads queries, not bare collections, hence the order_by.
    working = list(transaction.get(_facts(db).order_by("created_at")))
    restored = None
    if restore_number is not None:
        snapshot = _versions(db).document(_version_id(restore_number)).get(transaction=transaction)
        if not snapshot.exists:
            return None
        restored = snapshot.to_dict()["facts"]

    if restored is None:
        facts = _working(working)
    else:
        # Rolling back replaces the working set, so unpublished drafts are discarded.
        for doc in working:
            transaction.delete(doc.reference)
        start = datetime.now(UTC)
        for i, fact in enumerate(restored):
            data = {key: fact[key] for key in FACT_FIELDS}
            # Spaced created_at keeps the restored order.
            data["created_at"] = start + timedelta(microseconds=i)
            transaction.set(_facts(db).document(fact["id"]), data)
        facts = restored

    number = meta.get("version", 0) + 1
    transaction.set(
        _versions(db).document(_version_id(number)),
        {"number": number, "published_at": datetime.now(UTC), "facts": facts},
    )
    transaction.set(_meta(db), {"version": number})
    return number


def publish(db: firestore.Client) -> int:
    """Publishes the whole working set as the next version. Live from the next call."""
    return _publish(db.transaction(), db, None)


def rollback(db: firestore.Client, number: int) -> int | None:
    """Publishes an earlier version's facts as a new version. None if there's no such version."""
    return _publish(db.transaction(), db, number)


def published(db: firestore.Client) -> dict | None:
    """The live version for the agent, or None if nothing is published. Never drafts."""
    meta = _meta(db).get().to_dict()
    if not meta:
        return None
    version = _versions(db).document(_version_id(meta["version"])).get().to_dict()
    facts = [{key: fact[key] for key in FACT_FIELDS} for fact in version["facts"]]
    return {"version": version["number"], "facts": facts}
