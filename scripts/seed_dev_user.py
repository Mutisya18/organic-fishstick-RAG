#!/usr/bin/env python3
"""
In development (ENV=dev), create test user test@test.com / password123 if not present.
Exit silently if not dev or if user already exists.
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
    if os.getenv("ENV", "dev").lower() != "dev":
        return
    from database import db as database_manager
    from auth import create_user, get_user_by_email

    database_manager.initialize(debug=False)
    if get_user_by_email("test@test.com") is not None:
        return
    try:
        create_user(
            email="test@test.com",
            password="password123!",
            full_name="Test User",
        )
        print("Dev user created: test@test.com / password123!")
    except Exception:
        pass


if __name__ == "__main__":
    main()
