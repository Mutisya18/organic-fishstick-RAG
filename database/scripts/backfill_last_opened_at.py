"""
One-off backfill: set last_opened_at = created_at for conversations where last_opened_at is NULL.

Run once after deploying multi-conversation columns. Safe to run multiple times.
Usage: python -m database.scripts.backfill_last_opened_at
"""

import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Limit iterations (NASA-style fixed bound)
_MAX_ROWS = 10000


def main():
    from database import db
    from database.core.session import get_session
    from database.models import Conversation

    db.initialize(debug=False)

    updated = 0
    try:
        with get_session() as session:
            rows = (
                session.query(Conversation)
                .filter(Conversation.last_opened_at.is_(None))
                .limit(_MAX_ROWS)
                .all()
            )
            for conv in rows:
                conv.last_opened_at = conv.created_at
                session.add(conv)
                updated += 1
            session.commit()
        logger.info("Backfill complete: updated %d conversations", updated)
        return 0
    except Exception as e:
        logger.error("Backfill failed: %s", str(e))
        return 1


if __name__ == "__main__":
    sys.exit(main())
