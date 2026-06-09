"""Parse 2FA intro page to find TOTP secret and flow."""
import re
from bs4 import BeautifulSoup

with open("2fa_intro.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Find otpauth URI
m = re.search(r"otpauth://[^\s\"'<>]+", html)
if m:
    print("TOTP URI:", m.group())

# Find base32 secret in code elements
for c in soup.find_all("code"):
    txt = c.text.strip()
    if len(txt) > 10:
        print(f"Code element: {txt[:80]}")

# Find secret in data attributes
for tag in soup.find_all(True):
    for attr, val in tag.attrs.items():
        if isinstance(val, str) and ("secret" in attr.lower() or "totp" in attr.lower()):
            print(f"  {tag.name}[{attr}] = {val[:100]}")

# Look for QR code image
for img in soup.find_all("img"):
    src = img.get("src", "")
    if "qr" in src.lower() or "totp" in src.lower() or src.startswith("data:image"):
        print(f"QR img: src={src[:120]}")

# Look for the app verification form
app_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/verify"})
if app_form:
    print("\n=== App Verify Form ===")
    for inp in app_form.find_all("input"):
        print(f"  {inp.get('type','?')}: {inp.get('name','?')} = {inp.get('value','')[:60]}")

# Find all text containing "key" or "secret"
for el in soup.find_all(string=re.compile(r"key|secret|setup", re.I)):
    parent = el.find_parent()
    if parent and parent.name not in ("script", "style"):
        txt = el.strip()[:120]
        if txt:
            print(f"  Text in <{parent.name}>: {txt}")

# Find the recovery codes form
rec_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/recovery_download"})
if rec_form:
    print("\n=== Recovery Download Form ===")
    for inp in rec_form.find_all("input"):
        print(f"  {inp.get('type','?')}: {inp.get('name','?')} = {inp.get('value','')[:60]}")

# Find the enable form
enable_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/enable"})
if enable_form:
    print("\n=== Enable Form ===")
    for inp in enable_form.find_all("input"):
        print(f"  {inp.get('type','?')}: {inp.get('name','?')} = {inp.get('value','')[:60]}")

# Search for base32 pattern (TOTP secrets are usually base32)
base32_matches = re.findall(r"[A-Z2-7]{16,}", html)
if base32_matches:
    print(f"\n=== Base32 candidates ({len(base32_matches)}) ===")
    for m in base32_matches[:5]:
        print(f"  {m}")

# Look for the setup key in text near "setup key" or "can't scan"
for el in soup.find_all(string=re.compile(r"setup key|can.t scan|manual|enter.*key", re.I)):
    parent = el.find_parent()
    # Get next sibling or nearby code/text
    if parent:
        print(f"\n  Near '{el.strip()[:40]}' in <{parent.name}>:")
        for sib in parent.find_next_siblings()[:3]:
            print(f"    <{sib.name}>: {sib.text.strip()[:100]}")
