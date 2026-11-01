import json
from datetime import timedelta

from livekit import api

from app.config import Settings


def create_visitor_token(settings: Settings, session_id: str) -> tuple[str, str]:
    """Returns (room, token). The token only allows this visitor's mic in this one room."""
    room = f"session-{session_id}"
    grants = api.VideoGrants(
        room_join=True,
        room=room,
        can_publish=True,
        can_publish_sources=["microphone"],
        can_publish_data=False,
        can_subscribe=True,
    )
    metadata = json.dumps(
        {"session_id": session_id, "max_session_minutes": settings.max_session_minutes}
    )
    # Explicit dispatch: the agent joins only rooms that passed through this service.
    room_config = api.RoomConfiguration(
        empty_timeout=60,
        departure_timeout=30,
        agents=[api.RoomAgentDispatch(agent_name=settings.livekit_agent_name, metadata=metadata)],
    )
    token = (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret.get_secret_value())
        .with_identity(f"visitor-{session_id}")
        .with_ttl(timedelta(seconds=settings.token_ttl_seconds))
        .with_grants(grants)
        .with_room_config(room_config)
        .to_jwt()
    )
    return room, token
