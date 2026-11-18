import pytest
from aiohttp import web

from cloud_run import release_session, signature

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


@pytest.mark.asyncio
async def test_release_is_a_signed_empty_post_to_the_session() -> None:
    secret = b"release-secret-release-secret-release!!"
    seen: list[tuple[str, str, bool]] = []

    async def handler(request: web.Request) -> web.Response:
        body = await request.read()
        expected = signature(
            secret, request.headers["X-Agent-Timestamp"], "POST", request.path, body
        )
        seen.append((request.path, body.decode(), request.headers["X-Agent-Signature"] == expected))
        return web.json_response({"released": True})

    app = web.Application()
    app.router.add_post("/internal/sessions/{session_id}/release", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        status = await release_session(f"http://127.0.0.1:{port}/", secret, "abc123", 5.0)
    finally:
        await runner.cleanup()

    assert status == 200
    assert seen == [("/internal/sessions/abc123/release", "", True)]
