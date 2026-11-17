"""Keeps personal data out of the agent's plain logs (ADR-14).

The SDK marks fields that hold personal data, such as what the visitor said, as `lk.pii.*`. It
strips them from its telemetry, but not from the logs that `lk agent logs` shows, and those
must never hold transcripts.
"""

import logging

from livekit.agents.telemetry.pii import is_pii_attribute


class DropPII(logging.Filter):
    """Removes every `lk.pii.*` field from a record, and keeps the record."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in [key for key in record.__dict__ if is_pii_attribute(key)]:
            delattr(record, key)
        return True


_DROP_PII = DropPII()


def drop_pii_from_logs() -> None:
    """Call in the job process, once its log handlers exist. Safe to call more than once."""
    # On every handler, because a filter on a logger doesn't apply to its children's records.
    for handler in logging.getLogger().handlers:
        if _DROP_PII not in handler.filters:
            handler.addFilter(_DROP_PII)
