#!/usr/bin/env python3
"""
Delete expired sessions (expires_at older than 7 days). For use as cron job.
Usage: python scripts/cleanup_sessions.py
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
    from auth import cleanup_expired_sessions

    database_manager.initialize(debug=False)
    count = cleanup_expired_sessions()
    print(f"Cleaned up {count} expired session(s).")


if __name__ == "__main__":
    main()
