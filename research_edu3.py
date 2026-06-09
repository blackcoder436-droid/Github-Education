"""Fetch the actual education application form."""
import os, re, json
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Fetch the turbo-frame content
print("\n=== /settings/education/developer_pack_applications/new ===")
resp = c.get("/settings/education/developer_pack_applications/new")
print(f"Status: {resp.status_code}")
print(f"URL: {resp.url}")
print(f"Content-Type: {resp.headers.get('Content-Type','')}")

with open("edu_form.html", "w", encoding="utf-8") as f:
    f.write(resp.text)
print("Saved edu_form.html")

soup = BeautifulSoup(resp.text, "html.parser")

# Get visible text
text = soup.get_text(separator="\n", strip=True)
lines = [l for l in text.split("\n") if l.strip()]
print(f"\nContent ({len(lines)} lines):")
for line in lines[:80]:
    print(f"  {line[:150]}")

# Find forms
print("\n=== Forms ===")
forms = soup.find_all("form")
for form in forms:
    action = form.get("action", "")
    method = form.get("method", "")
    enc = form.get("enctype", "")
    if action:
        print(f"\n  Form: action={action} method={method} enctype={enc}")
        for inp in form.find_all(["input", "select", "textarea"]):
            name = inp.get("name", "")
            val = inp.get("value", "")[:80]
            typ = inp.get("type", inp.name)
            if name:
                print(f"    {typ}: {name} = {val}")
            # For select, show options
            if inp.name == "select":
                options = inp.find_all("option")
                for opt in options[:10]:
                    print(f"      option: {opt.get('value','')} -> {opt.text.strip()[:60]}")

# Custom elements
print("\n=== Custom elements ===")
for tag in soup.find_all(True):
    if "-" in tag.name:
        attrs = {k: str(v)[:100] for k, v in tag.attrs.items()}
        print(f"  <{tag.name}> {attrs}")

# Data attributes
print("\n=== Key data attributes ===")
for tag in soup.find_all(True):
    for attr, val in tag.attrs.items():
        if attr.startswith("data-") and isinstance(val, str) and len(val) > 10:
            if any(kw in attr.lower() for kw in ["url", "action", "target", "src"]):
                print(f"  <{tag.name}>[{attr}] = {val[:150]}")
