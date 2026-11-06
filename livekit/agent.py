"""Voice and video agent for checking the pipeline.

Pipeline: LiveKit Inference STT -> Gemini 3.5 Flash (Google plugin, own key)
-> ElevenLabs TTS (plugin, own key) -> Tavus avatar, which lip-syncs to that
audio. It is not the twin yet: no fact file. That comes later.

Needs GOOGLE_API_KEY, ELEVEN_API_KEY and ELEVENLABS_VOICE_ID in .env, plus
TAVUS_API_KEY and TAVUS_FACE_ID for the avatar.

Run it:
    uv run agent.py console   # voice only in this terminal; console has no room, so no avatar
    uv run agent.py dev       # connect to LiveKit Cloud, then see the avatar in the Agent Console
"""

import os
import random
from collections.abc import AsyncIterable

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    APIStatusError,
    ModelSettings,
    inference,
    llm,
    room_io,
)
from livekit.plugins import ai_coustics, elevenlabs, google, silero, tavus
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from persona import GREETINGS, VOICE_NOTES

load_dotenv()

# Explicit dispatch (U3): with a name set, the agent only joins rooms it is dispatched to.
AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "portfolio-twin")

# No default voice: the twin must never fall back to a stock voice by accident.
ELEVENLABS_VOICE_ID = os.environ["ELEVENLABS_VOICE_ID"]

# How long the greeting waits for the avatar's video before the call fails.
AVATAR_JOIN_TIMEOUT_SECONDS = 30.0

# Strictest level on every adjustable Gemini filter. Unset categories default to off on Gemini
# 2.5 and later. Gemini has no profanity or child-safe filter, so the prompt covers those.
GEMINI_SAFETY_SETTINGS = [
    {"category": category, "threshold": "BLOCK_LOW_AND_ABOVE"}
    for category in (
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
        "HARM_CATEGORY_JAILBREAK",
    )
]

# Spoken in place of a reply Gemini blocked, once per blocked turn.
BLOCKED_REPLY = "That's not something I can talk about, but I'm happy to tell you about Lee's work."


def _is_safety_block(error: APIStatusError) -> bool:
    # The Google plugin raises these two messages for a blocked reply and a blocked prompt.
    return error.message.startswith("generation blocked by gemini") or (
        '"block_reason"' in error.message
    )


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                f"{VOICE_NOTES} "
                "Say you are an AI if asked. Keep replies to one or two short sentences, "
                "in plain spoken English, with no lists, emojis or symbols."
            ),
        )
        # User messages Gemini blocked. They stay in the transcript but are never sent again,
        # or one blocked turn would block every turn after it.
        self._blocked_message_ids: set[str] = set()

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.Tool],
        model_settings: ModelSettings,
    ) -> AsyncIterable[llm.ChatChunk | str]:
        chat_ctx = chat_ctx.copy()
        for message_id in self._blocked_message_ids:
            if chat_ctx.index_by_id(message_id) is not None:
                chat_ctx.remove(message_id)

        replied = False
        try:
            async for chunk in Agent.default.llm_node(self, chat_ctx, tools, model_settings):
                replied = True
                yield chunk
        except APIStatusError as error:
            if not _is_safety_block(error):
                raise
            user_messages = [m for m in chat_ctx.messages() if m.role == "user"]
            if user_messages:
                self._blocked_message_ids.add(user_messages[-1].id)
            # A reply blocked partway has already been spoken up to the block; don't add to it.
            if not replied:
                yield BLOCKED_REPLY


server = AgentServer()


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: agents.JobContext) -> None:
    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-3-6-pro", language="en"),
        # Minimal thinking keeps voice replies fast. Gemini 3 takes a level only; there is no
        # time cap. Raise to "low" only if answers from the fact file need more reasoning.
        llm=google.LLM(
            model="gemini-3.5-flash",
            thinking_config={"thinking_level": "minimal"},
            safety_settings=GEMINI_SAFETY_SETTINGS,
        ),
        # English only (ADR-20).
        tts=elevenlabs.TTS(voice_id=ELEVENLABS_VOICE_ID, language="en"),
        # Explicit, though it matches the SDK default, so a default change can't alter it quietly.
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        use_tts_aligned_transcript=True,
    )

    avatar: tavus.AvatarSession | None = None
    if not ctx.is_fake_job():
        # No default face, for the same reason as the voice: without a face ID the plugin
        # shows a stock Tavus face. Read here, not at import, so console runs without it.
        # The stock PAL is used: echo mode, so Tavus only moves the face to our audio and
        # never hears the visitor or writes replies. The plugin removes the avatar on shutdown.
        avatar = tavus.AvatarSession(face_id=os.environ["TAVUS_FACE_ID"])
        # Before session.start, so agent audio goes to the avatar and not straight to the room.
        await avatar.start(session, room=ctx.room)

    await session.start(
        room=ctx.room,
        agent=Assistant(),
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # Voice isolation for one visitor on a laptop mic. It runs before VAD, STT and
                # turn detection. The frontend must not add its own Krisp filter on top.
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S,
                ),
            ),
        ),
    )
    if avatar is not None:
        # The greeting waits for the face, so the visitor sees who is talking. Raises after the
        # timeout, which ends the call.
        await avatar.wait_for_join(timeout=AVATAR_JOIN_TIMEOUT_SECONDS)
    # Lee's own words, spoken as written, and not interruptible so the AI disclosure is always
    # heard in full (ADR-8, I6).
    await session.say(random.choice(GREETINGS), allow_interruptions=False)


if __name__ == "__main__":
    agents.cli.run_app(server)
