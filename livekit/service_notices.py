"""Notices the call screen shows when a provider fails partway (I7).

The agent sets these as attributes on its own participant, and the frontend's call screen
(firebase/src/visitor/call-screen.tsx) reads them and shows a short, professional message.
The keys and values here must match the ones there.

Only these fixed values are ever sent: never error text, which could echo request details
(ADR-14).
"""

# Tavus couldn't start the avatar, so the call continues with voice only.
VIDEO = "notice.video"
VIDEO_UNAVAILABLE = "unavailable"

# ElevenLabs failed, so the backup voice is speaking. Cleared when ElevenLabs recovers.
VOICE = "notice.voice"
VOICE_BACKUP = "backup"
CLEARED = ""


def voice_notice(primary_available: bool) -> str:
    return CLEARED if primary_available else VOICE_BACKUP
