"""Research 2FA setup flow on GitHub."""
import os, re
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in")

# Step 1: Check 2FA status
print("\n=== Checking 2FA status ===")
resp = c.get("/settings/security")
soup = BeautifulSoup(resp.text, "html.parser")

# Look for 2FA related elements
tfa_section = soup.find(string=re.compile(r"Two-factor|2FA|two.factor", re.I))
if tfa_section:
    parent = tfa_section.find_parent("div") or tfa_section.find_parent("li")
    if parent:
        print("Found 2FA section:")
        print(parent.get_text(strip=True)[:300])

# Check if already enabled
enabled = soup.find(string=re.compile(r"Two-factor authentication is enabled|Enabled", re.I))
if enabled:
    print("\n2FA is ALREADY ENABLED")
else:
    print("\n2FA is NOT enabled")

# Step 2: Visit 2FA setup page
print("\n=== Visiting 2FA setup ===")
resp2 = c.get("/settings/two_factor_authentication/setup")
print(f"Status: {resp2.status_code}")
print(f"URL: {resp2.url}")

soup2 = BeautifulSoup(resp2.text, "html.parser")

# Find forms
forms = soup2.find_all("form")
print(f"Forms found: {len(forms)}")
for i, form in enumerate(forms):
    action = form.get("action", "")
    method = form.get("method", "")
    inputs = [inp.get("name") for inp in form.find_all("input") if inp.get("name")]
    if "two_factor" in action or "two_factor" in str(inputs):
        print(f"\nForm {i}: action={action} method={method}")
        print(f"  inputs: {inputs}")

# Look for TOTP secret
totp_el = soup2.find("input", {"id": re.compile(r"totp", re.I)})
if totp_el:
    print(f"\nTOTP input: {totp_el}")

# Look for QR code or secret key
secret_el = soup2.find(string=re.compile(r"secret|setup.key|TOTP", re.I))
if secret_el:
    print(f"\nSecret element: {secret_el[:200]}")

# Look for otpauth URI in any element
for tag in soup2.find_all(True):
    for attr_val in tag.attrs.values():
        if isinstance(attr_val, str) and "otpauth" in attr_val:
            print(f"\notpauth found in {tag.name}: {attr_val[:200]}")

# Check for password confirmation needed
pwd_form = soup2.find("form", action=re.compile(r"sudo|confirm|password"))
if pwd_form:
    print(f"\nPassword confirmation needed: {pwd_form.get('action')}")

# Save HTML for inspection
with open("2fa_setup.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)
print("\nSaved 2fa_setup.html")
print(f"Page title: {soup2.title.string if soup2.title else 'N/A'}")
