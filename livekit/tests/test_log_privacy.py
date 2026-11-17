import logging

from log_privacy import DropPII, drop_pii_from_logs


def record_with(**fields) -> logging.LogRecord:
    record = logging.LogRecord("livekit.agents", logging.WARNING, "", 0, "skipping", None, None)
    record.__dict__.update(fields)
    return record


def test_drops_what_the_visitor_said_and_keeps_the_rest() -> None:
    record = record_with(**{"lk.pii.user_input": "my phone number is...", "job_id": "AJ_1"})
    assert DropPII().filter(record)
    assert "lk.pii.user_input" not in record.__dict__
    assert record.__dict__["job_id"] == "AJ_1"


def test_installed_once_on_every_root_handler() -> None:
    handler = logging.Handler()
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        drop_pii_from_logs()
        drop_pii_from_logs()
        assert sum(isinstance(f, DropPII) for f in handler.filters) == 1
    finally:
        root.removeHandler(handler)
