"""Basic voice agent for checking the audio pipeline locally.

Pipeline: LiveKit Inference STT -> Gemini 3.5 Flash (Google plugin, own key)
-> ElevenLabs TTS (plugin, own key). It is not the twin yet: no Tavus and no
fact file. Those come later.

Needs GOOGLE_API_KEY, ELEVEN_API_KEY and ELEVENLABS_VOICE_ID in .env.

Run it:
    uv run agent.py console   # talk to it in this terminal, nothing else needed
    uv run agent.py dev       # connect to LiveKit Cloud, then use the Agent Console
"""

import os

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    TurnHandlingOptions,
    inference,
)
from livekit.plugins import elevenlabs, google

load_dotenv()

# Explicit dispatch (U3): with a name set, the agent only joins rooms it is dispatched to.
AGENT_NAME = os.getenv("LIVEKIT_AGENT_NAME", "portfolio-twin")

# No default voice: the twin must never fall back to a stock voice by accident.
ELEVENLABS_VOICE_ID = os.environ["ELEVENLABS_VOICE_ID"]


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are an AI voice assistant used to test audio on a developer's machine. "
                "Say you are an AI if asked. Keep replies to one or two short sentences, "
                "in plain spoken English, with no lists, emojis or symbols."
            ),
        )


server = AgentServer()


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: agents.JobContext) -> None:
    session = AgentSession(
        stt=inference.STT(model="assemblyai/universal-3-6-pro", language="en"),
        # Minimal thinking keeps voice replies fast.
        llm=google.LLM(
            model="gemini-3.5-flash",
            thinking_config={"thinking_level": "minimal"},
        ),
        # English only (ADR-20).
        tts=elevenlabs.TTS(voice_id=ELEVENLABS_VOICE_ID, language="en"),
        turn_handling=TurnHandlingOptions(turn_detection=inference.TurnDetector()),
        use_tts_aligned_transcript=True,
    )

    await session.start(room=ctx.room, agent=Assistant())
    await session.generate_reply(instructions="Greet the user briefly and ask how you can help.")


if __name__ == "__main__":
    agents.cli.run_app(server)
