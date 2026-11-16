from cloud_run import signature

# Pinned in cloud-run/tests/test_facts.py too, so the two services can't drift apart (ADR-9).
VECTOR = {
    "secret": b"golden-secret-golden-secret-golden-secret",
    "timestamp": "1800000000",
    "method": "GET",
    "path": "/internal/facts",
    "body": b"",
}
EXPECTED = "3c48205d4bc6cd99d227f30885e077e6bacaa57113c3010eb233dba32965275b"


def test_signature_matches_cloud_run() -> None:
    assert signature(**VECTOR) == EXPECTED
