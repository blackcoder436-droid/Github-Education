#!/usr/bin/env python3
"""Debug billing submission."""
import os, re
from dotenv import load_dotenv
load_dotenv()
from client import GitHubClient
from bs4 import BeautifulSoup

c = GitHubClient()
c.login(os.environ["GITHUB_USERNAME"], os.environ["GITHUB_PASSWORD"])

# Fresh GET of billing page
r = c.get("/settings/billing/payment_information")
print(f"GET billing: {r.status_code}, url: {r.url}")

soup = BeautifulSoup(r.text, "html.parser")
bf = None
for form in soup.find_all("form"):
    if form.find("input", {"name": re.compile(r"billing_contact")}):
        bf = form
        break

if not bf:
    print("No billing form!")
    exit(1)

# Show ALL form fields so we can see what's being sent
data = c.extract_form_data(bf)
print(f"\nOriginal form fields ({len(data)}):")
for k, v in sorted(data.items()):
    print(f"  {k} = {repr(v)[:60]}")

# Only update the billing_contact fields, leave everything else
data["billing_contact[first_name]"] = "VERIFY123"
data["billing_contact[last_name]"] = "SAVING456"
data["billing_contact[address1]"] = "No.99 Verify Road"
data["billing_contact[city]"] = "Mandalay"
data["billing_contact[postal_code]"] = "11061"
data["billing_contact[country_code]"] = "MM"

action = bf.get("action", "/account/contact")
print(f"\nPOST {action}")

# Use direct session.post with explicit referer pointing to billing page
resp = c.session.post(
    f"{c.BASE}{action}",
    data=data,
    headers={
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/billing/payment_information",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-User": "?1",
    },
    allow_redirects=False,
)
print(f"Status: {resp.status_code}")
print(f"Location: {resp.headers.get('Location', 'none')}")
print(f"Set-Cookie: {resp.headers.get('Set-Cookie', 'none')[:200]}")

# Check for flash cookies
loc = resp.headers.get("Location", "")
if loc:
    r2 = c.session.get(loc)
    print(f"Redirect: {r2.status_code}")
    s2 = BeautifulSoup(r2.text, "html.parser")
    for cls in ("flash-error", "flash-warn", "flash-success", "flash"):
        el = s2.find("div", class_=cls)
        if el:
            print(f"  {cls}: {el.get_text(strip=True)[:150]}")
    # Check if billing info was saved
    bf2 = None
    for form in s2.find_all("form"):
        if form.find("input", {"name": re.compile(r"billing_contact")}):
            bf2 = form
            break
    if bf2:
        fn = bf2.find("input", {"name": "billing_contact[first_name]"})
        if fn:
            print(f"  Saved first_name: {fn.get('value', '?')}")
        ln = bf2.find("input", {"name": "billing_contact[last_name]"})
        if ln:
            print(f"  Saved last_name: {ln.get('value', '?')}")

s2 = BeautifulSoup(resp.text, "html.parser")
for cls in ("flash-error", "flash-warn", "flash-full", "flash-success"):
    el = s2.find("div", class_=cls)
    if el:
        print(f"  {cls}: {el.get_text(strip=True)[:150]}")

# Also check: does the billing page even show for this account type?
# Check if there's something else on the page
title = s2.find("title")
if title:
    print(f"  Page title: {title.get_text(strip=True)[:80]}")
