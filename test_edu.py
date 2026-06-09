"""Test education step only — uses credentials from env/hardcoded."""
import os
os.environ.setdefault("GITHUB_EDU_SCHOOL_NAME", "Yangon Technological University")
os.environ.setdefault("GITHUB_EDU_SCHOOL_EMAIL", "thawkhant.1280@gmail.com")
os.environ.setdefault("GITHUB_EDU_LATITUDE", "16.8661")
os.environ.setdefault("GITHUB_EDU_LONGITUDE", "96.1951")

from client import GitHubClient
from steps import ProfileUpdater

USERNAME = "thawkhant1280-00"
PASSWORD = "Mka&Omk@2016"
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

client = GitHubClient()
print("Logging in...")
if not client.login(USERNAME, PASSWORD, totp_secret=TOTP_SECRET):
    print("x Login failed!")
    exit(1)
print("Logged in")

updater = ProfileUpdater(client)
print("\nRunning Education step...")
ok = updater.step_education()
print(f"\nResult: {'SUCCESS' if ok else 'FAILED'}")
