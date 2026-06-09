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

    # ── Verify Account Age ──────────────────────────────────────
    print("Checking account validity...")
    if not client.check_account_age(min_days=3):
        print("x Account validation failed!")
        sys.exit(1)
    print()

    # ── Check and Enable 2FA ────────────────────────────────────
    print("Checking 2FA status...")
    twofa_status = client.check_2fa_enabled()
    
    if twofa_status is False:
        # Enable 2FA
        print("Setting up 2FA...")
        twofa_result = client.enable_2fa_and_get_secrets()
        if twofa_result:
            # Save account details
            client.save_account_details(twofa_result)
            print(f"\n2FA Secret: {twofa_result['secret']}")
            print("Recovery Codes:")
            for code in twofa_result['recovery_codes']:
                print(f"  {code}")
        else:
            print("x 2FA setup failed!")
            sys.exit(1)
    elif twofa_status is True:
        print("  ✓ 2FA already enabled")
    else:
        print("  x Cannot determine 2FA status")
        sys.exit(1)
    print()

    # ── Select Role ────────────────────────────────────────────
    print("Select Your Role:")
    print("  1. Student (default)")
    print("  2. Teacher")
    
    role_choice = input("Choice (1-2, default 1): ").strip() or "1"
    if role_choice == "2":
        role = "teacher"
    else:
        role = "student"
    print(f"Role: {role.upper()}")
    print()

    # ── Run Steps ──────────────────────────────────────────────
    updater = ProfileUpdater(client, role=role)
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
