"""Parse the Education Benefits page."""
import os, re, time, json
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Get the education benefits page
resp = c.get("/settings/education/benefits")
print(f"Status: {resp.status_code} URL: {resp.url}")

with open("edu_benefits.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("Saved edu_benefits.html")

soup = BeautifulSoup(resp.text, "html.parser")
title = soup.title.string.strip() if soup.title else ""
print(f"Title: {title}")

# Find main content
main = soup.find("main") or soup.find("div", {"role": "main"})
if main:
    text = main.get_text(separator="\n", strip=True)
    lines = [l for l in text.split("\n") if l.strip()]
    print(f"\nMain content ({len(lines)} lines):")
    for line in lines[:100]:
        print(f"  {line[:120]}")

# Find all forms
print("\n=== Forms ===")
forms = soup.find_all("form")
for form in forms:
    action = form.get("action", "")
    method = form.get("method", "")
    if action and "search" not in action and "logout" not in action:
        print(f"  Form: action={action} method={method}")
        for inp in form.find_all(["input", "select", "textarea"]):
            name = inp.get("name", "")
            val = inp.get("value", "")[:60]
            typ = inp.get("type", inp.name)
            if name:
                print(f"    {typ}: {name} = {val}")

# Find buttons and links related to education
print("\n=== Education links ===")
for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.text.strip()[:60]
    if any(kw in href.lower() for kw in ["education", "student", "discount", "benefit", "apply"]):
        print(f"  {href} -> {text}")
