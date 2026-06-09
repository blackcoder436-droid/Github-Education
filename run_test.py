#!/usr/bin/env python3
"""Quick test — login with .env credentials and run all 3 steps."""
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
if updater.run():
    print("All steps completed!")
else:
    print("Process incomplete!")
