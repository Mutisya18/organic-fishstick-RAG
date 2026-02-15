#!/usr/bin/env python3
"""
Create the first admin user. Exits with error if any users already exist.
Usage: python scripts/create_admin.py
"""

import os
import sys

# Load .env from project root
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
    from auth import create_user, list_users, validate_password, validate_email

    database_manager.initialize(debug=False)
    users = list_users()
    if len(users) > 0:
        print("Error: Users already exist. Create the first admin only when the users table is empty.")
        sys.exit(1)

    email = (input("Email: ").strip() or "").strip()
    if not email:
        print("Error: Email is required.")
        sys.exit(1)
    ok, err = validate_email(email)
    if not ok:
        print("Error:", err)
        sys.exit(1)
    full_name = (input("Full Name: ").strip() or "").strip()
    if not full_name:
        print("Error: Full name is required.")
        sys.exit(1)
    password = input("Password: ")
    if not password:
        print("Error: Password is required.")
        sys.exit(1)
    password2 = input("Confirm Password: ")
    if password != password2:
        print("Error: Passwords do not match.")
        sys.exit(1)
    ok, err = validate_password(password)
    if not ok:
        print("Error:", err)
        sys.exit(1)

    try:
        create_user(email=email, password=password, full_name=full_name)
    except ValueError as e:
        print("Error:", e)
        sys.exit(1)
    print("Admin user created successfully.")


if __name__ == "__main__":
    main()
