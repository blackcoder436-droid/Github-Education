"""Quick test — avatar upload only."""
import os
from dotenv import load_dotenv
load_dotenv()

from client import GitHubClient
from steps import ProfileUpdater

client = GitHubClient()
username = os.environ.get("GITHUB_USERNAME", "")
password = os.environ.get("GITHUB_PASSWORD", "")

print(f"Logging in as {username}...")
if not client.login(username, password):
    print("x Login failed!")
    exit(1)
print("Logged in\n")

updater = ProfileUpdater(client)

print("(2/3) Profile Photo")
ok = updater.step_avatar()
if ok:
    print("\nDone!")
else:
    print("\nFailed!")
