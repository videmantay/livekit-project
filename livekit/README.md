# LiveKit agent

The AI twin, deployed to LiveKit Cloud. It joins only rooms dispatched by the `cloud-run` gatekeeper, and has no database access. The agent code isn't written yet.

## Configuration

Copy `.env.example` to `.env` for local development. In production, store these values as LiveKit Cloud agent secrets.

Anything in the agent's prompt can be extracted by a visitor, so it should only contain information that's already public.
