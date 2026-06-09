"""Research 2FA setup flow - find correct endpoint."""
import os, re
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in")

# Try various 2FA endpoints
endpoints = [
    "/settings/security",
    "/settings/two_factor_authentication",
    "/settings/two_factor_authentication/setup",
    "/settings/two_factor_authentication/configure",
    "/settings/authentication",
    "/settings/password_and_authentication",
    "/settings/security/two-factor-authentication",
]

for ep in endpoints:
    resp = c.get(ep)
    status = resp.status_code
    url = resp.url
    title = ""
    if status == 200:
        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title else ""
    redirected = " -> " + url if url != f"https://github.com{ep}" else ""
    print(f"  {status} {ep}{redirected}")
    if title:
        print(f"    title: {title}")
