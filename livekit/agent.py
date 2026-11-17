"""Voice and video agent for checking the pipeline.

Pipeline: LiveKit Inference STT -> Gemini 3.5 Flash (Google plugin, own key)
-> ElevenLabs TTS (plugin, own key) -> Tavus avatar, which lip-syncs to that
audio. Lee's published facts go into the prompt (facts.py), fetched from cloud-run at each call
start, or read from the local seed file when CLOUD_RUN_URL is unset (ADR-21). The transcript
goes back to cloud-run in batches (transcript.py, A4).

Needs GOOGLE_API_KEY, ELEVEN_API_KEY and ELEVENLABS_VOICE_ID in .env, plus
TAVUS_API_KEY and TAVUS_FACE_ID for the avatar.

Run it:
    uv run agent.py console   # voice only in this terminal; console has no room, so no avatar
    uv run agent.py dev       # connect to LiveKit Cloud, then see the avatar in the Agent Console
"""

import asyncio
import json
import logging
import random
from collections.abc import AsyncIterable, Awaitable, Callable

import aiohttp
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    APIStatusError,
    ConversationItemAddedEvent,
    ModelSettings,
    inference,
    llm,
    room_io,
)
from livekit.agents.voice.io import TimedString
from livekit.plugins import ai_coustics, elevenlabs, google, silero, tavus
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from config import AgentSettings
from delivery import DELIVERY_NOTES, allow_listed_tags_only, without_tags
from facts import (
    GROUNDING_RULES,
    STORY_RULES,
    FactSet,
    NoFactsError,
    facts_prompt,
    get_published_facts,
)
from persona import GREETINGS, VOICE_NOTES
from transcript import (
    Transcript,
    cloud_run_post,
    facts_version_number,
    session_id_from_metadata,
)

# The SDK and plugins read their own keys from the environment, so .env goes there first.
load_dotenv()
settings = AgentSettings()

logger = logging.getLogger("agent")

# ElevenLabs' realtime model for agents. It reads audio tags such as [laughs] and treats
# ellipses and dashes as pauses (see delivery.py). The plugin streams it over the
# text-to-dialogue websocket, which takes only `stability` from voice settings and no SSML.
ELEVENLABS_MODEL = "eleven_v4_turbo"

# Same base URL the Tavus plugin uses, for ending the conversation it started.
TAVUS_API_URL = "https://tavusapi.com/v2"

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

# Spoken when there are no facts to answer from, then the call ends (ADR-21, A8).
NO_FACTS_REPLY = (
    "Hi, I'm Lee's AI twin. Sorry, I can't answer questions right now because something's "
    "wrong on my end. Please try again later, or reach out to Lee directly."
)


# cloud-run sends the call's length limit in the dispatch metadata (I7). This is the fallback
# when it's missing or out of range, and matches cloud-run's default.
DEFAULT_MAX_SESSION_MINUTES = 6.0

# The goodbye starts this long before the limit, so it's heard in full before the call ends.
GOODBYE_LEAD_SECONDS = 20.0

TIME_UP_REPLY = (
    "That's all the time we have for this call. Thanks so much for talking with me, and goodbye!"
)


def _dispatch_metadata(metadata: str) -> dict:
    try:
        value = json.loads(metadata or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _max_session_minutes(metadata: dict) -> float:
    try:
        value = float(metadata.get("max_session_minutes"))
    except (ValueError, TypeError):
        return DEFAULT_MAX_SESSION_MINUTES
    return value if 1 <= value <= 60 else DEFAULT_MAX_SESSION_MINUTES


# Each call's transcript, by job ID, for on_session_end to send the final batch.
_transcripts: dict[str, Transcript] = {}


async def _end_at_time_limit(
    ctx: agents.JobContext,
    session: AgentSession,
    minutes: float,
    before_end: Callable[[], Awaitable[None]],
) -> None:
    await asyncio.sleep(max(minutes * 60 - GOODBYE_LEAD_SECONDS, 0))
    logger.info("time limit reached", extra={"max_session_minutes": minutes})
    try:
        # Queued behind any reply in progress; the timeout keeps the call from running over.
        await asyncio.wait_for(
            session.say(TIME_UP_REPLY, allow_interruptions=False), timeout=GOODBYE_LEAD_SECONDS
        )
    except (TimeoutError, RuntimeError, APIStatusError) as error:
        # The call still ends below. RuntimeError covers a session that already closed.
        logger.warning("goodbye failed", extra={"error": type(error).__name__})
    # The final batch goes first. Deleting the room sends room_finished, and cloud-run refuses
    # batches once that has ended the call.
    await before_end()
    # Not in a finally: a shutdown cancels this task, and that must not delete the room.
    # Disconnects the visitor too, and LiveKit's room_finished webhook closes the session in
    # cloud-run (A4).
    await ctx.delete_room()


def _is_safety_block(error: APIStatusError) -> bool:
    # The Google plugin raises these two messages for a blocked reply and a blocked prompt.
    return error.message.startswith("generation blocked by gemini") or (
        '"block_reason"' in error.message
    )


async def _end_tavus_conversation(avatar: tavus.AvatarSession | None) -> None:
    conversation_id = avatar.conversation_id if avatar else None
    if not conversation_id:
        return
    try:
        async with aiohttp.ClientSession() as http, http.post(
            f"{TAVUS_API_URL}/conversations/{conversation_id}/end",
            headers={"x-api-key": settings.tavus_api_key.get_secret_value()},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            if not response.ok:
                # Status only: the body could echo request details (ADR-14).
                logger.warning("tavus end failed", extra={"status": response.status})
    except (aiohttp.ClientError, TimeoutError) as error:
        logger.warning("tavus end failed", extra={"error": type(error).__name__})


class Assistant(Agent):
    def __init__(self, facts: FactSet | None) -> None:
        super().__init__(
            instructions=(
                f"{VOICE_NOTES} {DELIVERY_NOTES} "
                "Say you are an AI if asked. Keep replies to one or two short sentences, except "
                "a story, which takes about four. Use plain spoken English, with no lists, "
                "emojis or symbols.\n\n"
                f"{GROUNDING_RULES}\n\n{STORY_RULES}\n\n{facts_prompt(facts)}"
                if facts
                # Never used to answer: with no facts the call ends after NO_FACTS_REPLY.
                else f"{VOICE_NOTES} You have no facts about Lee. Answer nothing about Lee."
            ),
        )
        # User messages Gemini blocked. They stay in the transcript but are never sent again,
        # or one blocked turn would block every turn after it.
        self._blocked_message_ids: set[str] = set()

    def is_blocked(self, message_id: str) -> bool:
        """Marked as a violation in the transcript, so Lee sees why a call ended (A4)."""
        return message_id in self._blocked_message_ids

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

    async def transcription_node(
        self, text: AsyncIterable[str | TimedString], model_settings: ModelSettings
    ) -> AsyncIterable[str | TimedString]:
        # Visitors see the words only. Audio tags shape the voice and never reach the captions.
        async for chunk in without_tags(text):
            yield chunk


server = AgentServer()


async def _send_final_transcript(ctx: agents.JobContext) -> None:
    # Runs after the session closes, so every turn is in, and before the agent leaves the room,
    # so the final batch reaches cloud-run ahead of room_finished. The SDK allows it 5 minutes.
    transcript = _transcripts.pop(ctx.job.id, None)
    if transcript is not None:
        await transcript.finish()


@server.rtc_session(
    agent_name=settings.livekit_agent_name, on_session_end=_send_final_transcript
)
async def entrypoint(ctx: agents.JobContext) -> None:
    # Fetched per call, so a publish in admin reaches the next call with no deploy (ADR-21).
    facts: FactSet | None
    try:
        facts = await get_published_facts()
        # The version only, never fact text (ADR-14). It's also sent with each transcript batch.
        logger.info("facts loaded", extra={"facts_version": facts.version})
    except NoFactsError as error:
        facts = None
        logger.error("no facts for this call", extra={"reason": str(error)})

    metadata = _dispatch_metadata(ctx.job.metadata)
    assistant = Assistant(facts)
    transcript: Transcript | None = None
    session_id = session_id_from_metadata(metadata)
    post = cloud_run_post(session_id) if session_id else None
    if post is None:
        # Local runs: no CLOUD_RUN_URL, or a dispatch that didn't come from cloud-run.
        logger.info("transcript not sent for this call")
    else:
        transcript = Transcript(
            post=post,
            facts_version=facts_version_number(facts.version if facts else None),
            is_violation=assistant.is_blocked,
        )
        _transcripts[ctx.job.id] = transcript

    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-3-6-pro", language="en"),
        # Minimal thinking keeps voice replies fast. Gemini 3 takes a level only; there is no
        # time cap. Raise to "low" only if answers from the fact file need more reasoning.
        llm=google.LLM(
            model="gemini-3.5-flash",
            thinking_config={"thinking_level": "minimal"},
            # Least variation in wording. It doesn't stop invention; the facts and rules do that.
            temperature=0,
            safety_settings=GEMINI_SAFETY_SETTINGS,
        ),
        # English only (ADR-20).
        tts=elevenlabs.TTS(
            voice_id=settings.elevenlabs_voice_id, model=ELEVENLABS_MODEL, language="en"
        ),
        # The defaults, plus the allowlist that drops any tag not in delivery.ALLOWED_TAGS.
        tts_text_transforms=["filter_markdown", "filter_emoji", allow_listed_tags_only],
        # Explicit, though it matches the SDK default, so a default change can't alter it quietly.
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        use_tts_aligned_transcript=True,
    )

    if transcript is not None:

        @session.on("conversation_item_added")
        def _on_item(event: ConversationItemAddedEvent) -> None:
            if isinstance(event.item, llm.ChatMessage):
                transcript.add(event.item.id, event.item.role, event.item.text_content)

    async def _finish_transcript() -> None:
        if transcript is not None:
            await transcript.finish()

    # Started before the avatar and greeting, so time spent joining counts toward the limit.
    time_limit = asyncio.create_task(
        _end_at_time_limit(ctx, session, _max_session_minutes(metadata), _finish_transcript)
    )

    async def _cancel_time_limit() -> None:
        time_limit.cancel()

    ctx.add_shutdown_callback(_cancel_time_limit)

    avatar: tavus.AvatarSession | None = None
    if not ctx.is_fake_job():
        # No default face, for the same reason as the voice: without a face ID the plugin
        # shows a stock Tavus face. Read here, not at import, so console runs without it.
        # The stock PAL is used: echo mode, so Tavus only moves the face to our audio and
        # never hears the visitor or writes replies.
        avatar = tavus.AvatarSession(face_id=settings.tavus_face_id)
        # The plugin never ends the Tavus conversation, so every call would hold a slot until
        # Tavus times it out, and the account soon hits its concurrent-conversation cap.
        # Registered before start, so a start that fails partway still cleans up.
        ctx.add_shutdown_callback(lambda: _end_tavus_conversation(avatar))
        # Before session.start, so agent audio goes to the avatar and not straight to the room.
        await avatar.start(session, room=ctx.room)

    await session.start(
        room=ctx.room,
        agent=assistant,
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
    if facts is None:
        await session.say(NO_FACTS_REPLY, allow_interruptions=False)
        ctx.shutdown(reason="no facts")
        return
    await session.say(random.choice(GREETINGS), allow_interruptions=False)


if __name__ == "__main__":
    agents.cli.run_app(server)
