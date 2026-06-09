"""Debug 2FA enable - check verify response and security page."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
import pyotp
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Check current 2FA status on security page
resp = c.get("/settings/security")
soup = BeautifulSoup(resp.text, "html.parser")

# Search for 2FA-related text
for s in soup.find_all(string=re.compile(r"two.factor|2FA|TOTP|authenticator", re.I)):
    parent = s.find_parent()
    if parent:
        print(f"  <{parent.name}>: {s.strip()[:100]}")

# Search for disable button/link
disable = soup.find_all(string=re.compile(r"Disable|disable", re.I))
for d in disable:
    parent = d.find_parent()
    print(f"  Disable: <{parent.name}> {d.strip()[:80]}")

# Look for "Enable" link
enable = soup.find_all("a", href=re.compile(r"two_factor"))
for e in enable:
    print(f"  Link: {e.get('href')} -> {e.text.strip()[:60]}")

# Let's try the full flow again with more debugging
print("\n=== Full 2FA setup with debug ===")
resp = c.get("/settings/two_factor_authentication/setup/intro")
if resp.status_code != 200:
    print(f"  Intro page: {resp.status_code} {resp.url}")
    exit(1)

soup = BeautifulSoup(resp.text, "html.parser")

# Check if it shows "already enabled"
text = soup.get_text()
if "already" in text.lower() and "enabled" in text.lower():
    print("  Page says already enabled")
if "Disable" in text:
    print("  Page has Disable option")

# Get initiate form
init_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/initiate"})
if not init_form:
    print("  No initiate form - 2FA might already be set up")
    # Save and check
    with open("2fa_debug.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 5]
    for line in lines[:30]:
        print(f"    {line[:120]}")
    exit(0)

init_data = {}
for inp in init_form.find_all("input"):
    name = inp.get("name")
    if name:
        init_data[name] = inp.get("value", "")
init_data["type"] = "app"

# Get verify form
verify_data = {}
for form in soup.find_all("form", {"action": "/settings/two_factor_authentication/setup/verify"}):
    type_inp = form.find("input", {"name": "type"})
    if type_inp and type_inp.get("value") == "app":
        for inp in form.find_all("input"):
            name = inp.get("name")
            if name:
                verify_data[name] = inp.get("value", "")
        break

# Initiate
json_h = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": c.BASE,
    "Referer": f"{c.BASE}/settings/two_factor_authentication/setup/intro",
}
time.sleep(2)
r = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/initiate",
    data=init_data,
    headers={**c.HEADERS, **json_h},
)
print(f"  Initiate: {r.status_code} CT={r.headers.get('Content-Type','')}")
print(f"  Body: {r.text[:300]}")

payload = r.json()
secret = payload.get("mashed_secret", "")
recovery = payload.get("formatted_recovery_codes", [])
print(f"  Secret: {secret}")

# Generate code and verify
time.sleep(3)
totp = pyotp.TOTP(secret)
code = totp.now()
print(f"  Code: {code}")

verify_data["otp"] = code
r2 = c.session.post(
    f"{c.BASE}/settings/two_factor_authentication/setup/verify",
    data=verify_data,
    headers={**c.HEADERS, **json_h},
)
print(f"\n  Verify: {r2.status_code}")
print(f"  Headers: {dict(r2.headers)}")
print(f"  Body: {r2.text[:300]}")

# Check security page IMMEDIATELY
time.sleep(1)
r3 = c.get("/settings/security")
soup3 = BeautifulSoup(r3.text, "html.parser")
text3 = soup3.get_text()

# Check for specific strings  
checks = [
    "Disable two-factor authentication",
    "Two-factor authentication",
    "Enabled",
    "enabled",
    "Authenticator app",
    "Configured",
    "two-factor methods",
]
print("\n  Security page checks:")
for check in checks:
    found = check in text3
    print(f"    '{check}': {found}")

# Save security page
with open("security_after_2fa.html", "w", encoding="utf-8") as f:
    f.write(r3.text)
print("  Saved security_after_2fa.html")
