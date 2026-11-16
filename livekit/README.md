# LiveKit agent

The AI twin, deployed to LiveKit Cloud. It joins only rooms dispatched by the `cloud-run` gatekeeper, and has no database access.

## Configuration

Copy `.env.example` to `.env` for local development. In production, store these values as LiveKit Cloud agent secrets.

Anything in the agent's prompt can be extracted by a visitor, so it should only contain information that's already public. It must also be verified by Lee, because the agent answers onlycd from that material (ADR-19).

## Running locally

Install dependencies once with `uv sync`, and fill in `.env` first.

### Console (terminal only)

```bash
uv run agent.py console
```

Talks to the agent through your microphone and speakers, with no room or frontend. The Tavus avatar has no video here, so this checks voice, prompt and facts only.

### Cloud playground (test room with video)

```bash
uv run agent.py dev
```

Registers the agent with the LiveKit Cloud project in `.env` and reloads on code changes. Then open the [Agents Playground](https://agents-playground.livekit.io), sign in, pick the same project and connect.

The agent uses explicit dispatch (`LIVEKIT_AGENT_NAME`, default `portfolio-twin`), so it won't join the playground room on its own. Dispatch it to the room the playground created:

```bash
lk dispatch create --room <room-name> --agent-name portfolio-twin
```

In production, `cloud-run` does this dispatch instead.
