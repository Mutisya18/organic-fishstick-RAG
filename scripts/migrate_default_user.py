#!/usr/bin/env python3
"""
Migrate all conversations with user_id='default_user' to the first admin user.
Run after create_admin.py. Exits with error if no users exist.
Usage: python scripts/migrate_default_user.py
"""

import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _load_env():
    env_path = os.path.join(_project_root, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)


def main():
    _load_env()
    from database import db as database_manager
    from database.core.session import get_session
    from auth import list_users
    from sqlalchemy import text

    database_manager.initialize(debug=False)
    users = list_users()
    if not users:
        print("Error: No users found. Run scripts/create_admin.py first.")
        sys.exit(1)
    first_user_id = users[0]["user_id"]

    with get_session() as session:
        result = session.execute(
            text("UPDATE conversations SET user_id = :uid WHERE user_id = 'default_user'"),
            {"uid": first_user_id},
        )
        count = result.rowcount
    print(f"Migrated {count} conversation(s) to {first_user_id}")


if __name__ == "__main__":
    main()
