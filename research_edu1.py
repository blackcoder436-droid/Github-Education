"""Research GitHub Education Student Developer Pack application."""
import os, re, time, json
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Check education-related pages
print("\n=== Education pages ===")
endpoints = [
    "/settings/education",
    "/settings/education/benefits",
    "/education",
    "/education/students",
    "/education/discount_requests/application",
    "/education/discount_requests/new",
    "/education/benefits",
    "/education/benefits/application",
]
for ep in endpoints:
    resp = c.get(ep, allow_redirects=False)
    loc = resp.headers.get("Location", "")
    print(f"  {resp.status_code} {ep}" + (f" -> {loc}" if loc else ""))
