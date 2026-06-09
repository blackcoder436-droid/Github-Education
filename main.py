#!/usr/bin/env python3
"""GitHub Profile Updater CLI — update name, photo, billing, 2FA, and education."""

import sys
import getpass

from client import GitHubClient
from steps import ProfileUpdater


BANNER = """\
+--------------------------------------+
|   GitHub Profile Updater CLI         |
+--------------------------------------+
"""


def main():
    print(BANNER)

    # ── Login ───────────────────────────────────────────────────
    print("Login Options:")
    print("  1. Username & Password")
    print("  2. Cookie")

    choice = input("Choice (1-2): ").strip()
    client = GitHubClient()

    if choice == "1":
        username = input("Username or Email: ").strip()
        password = getpass.getpass("Password: ")
        if not username or not password:
            print("x Username and password required!")
            sys.exit(1)
        totp_secret = input("TOTP Secret (blank if no 2FA): ").strip() or None
        print("Logging in...")
        if not client.login(username, password, totp_secret=totp_secret):
            print("x Login failed!")
            sys.exit(1)
        print("Logged in")

    elif choice == "2":
        cookie = input("Cookie: ").strip()
        if not cookie:
            print("x Cookie required!")
            sys.exit(1)
        client.set_cookies(cookie)
        print("Verifying session...")
        if not client.verify_session():
            print("x Invalid session!")
            sys.exit(1)
        print("Session valid")

    else:
        print("Invalid choice!")
        sys.exit(1)

    print()

    # ── Run Steps ──────────────────────────────────────────────
    updater = ProfileUpdater(client)
    success = updater.run()

    if success:
        print("All steps completed!")
        if updater.totp_secret:
            print(f"\nTOTP Secret: {updater.totp_secret}")
            print("Recovery Codes:")
            for rc in updater.recovery_codes:
                print(f"  {rc}")
    else:
        print("Process incomplete!")
        sys.exit(1)


if __name__ == "__main__":
    main()
