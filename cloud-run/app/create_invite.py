"""Creates an invite. Run from cloud-run/:

uv run python -m app.create_invite --label "Acme recruiter" --expires-days 14
"""

import argparse
from datetime import UTC, datetime, timedelta

from app.store import create_invite, get_db


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="Who this invite is for")
    parser.add_argument("--max-sessions", type=int, default=2)
    parser.add_argument("--expires-days", type=int, default=14)
    args = parser.parse_args()

    expires_at = datetime.now(UTC) + timedelta(days=args.expires_days)
    code, invite_id = create_invite(get_db(), args.label, args.max_sessions, expires_at)
    print(f"Code (shown once): {code}")
    print(f"Invite ID: {invite_id}")
    print(f"Expires: {expires_at:%Y-%m-%d}")


if __name__ == "__main__":
    main()
