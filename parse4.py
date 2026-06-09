"""Deep analysis of the two-factor-setup-verification component."""
import re
from bs4 import BeautifulSoup

with open("2fa_intro.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Find the custom element
tfv = soup.find("two-factor-setup-verification")
if tfv:
    print("=== two-factor-setup-verification element ===")
    # Print all attributes
    for attr, val in tfv.attrs.items():
        val_str = str(val)
        print(f"  {attr} = {val_str[:200]}")
    
    # Print inner HTML (first 2000 chars)
    inner = str(tfv)
    print(f"\n=== Inner HTML ({len(inner)} chars) ===")
    print(inner[:3000])
    print("...")
    if len(inner) > 3000:
        print(inner[3000:6000])

# Find the QR code img  
print("\n=== QR Code ===")
imgs = soup.find_all("img")
for img in imgs:
    src = img.get("src", "")
    # QR codes might be inline data URIs or specific URLs
    if src:
        print(f"  img src: {src[:200]} alt={img.get('alt','')}")

# Find the mashed secret dialog content
dialog = soup.find("dialog", {"id": "two-factor-setup-verification-mashed-secret"})
if dialog:
    print("\n=== Mashed Secret Dialog ===")
    print(dialog.prettify()[:2000])

# Check for JavaScript that loads the secret
print("\n=== JS with two-factor ===")
for script in soup.find_all("script"):
    text = script.string or ""
    src = script.get("src", "")
    if "two-factor" in text.lower() or "two_factor" in text.lower():
        print(f"  Script (inline): {text[:200]}")
    if "two-factor" in src.lower() or "two_factor" in src.lower():
        print(f"  Script src: {src}")

# Check for template/slot elements
print("\n=== Templates inside the component ===")
if tfv:
    templates = tfv.find_all("template")
    for t in templates:
        print(f"  Template: {str(t)[:500]}")
    
    # Find all data-target attributes
    targets = tfv.find_all(True, attrs={"data-target": True})
    for t in targets:
        print(f"  data-target: {t['data-target']} tag={t.name} text={t.text.strip()[:80]}")
    
    # Find all data-action attributes
    actions = tfv.find_all(True, attrs={"data-action": True})
    for a in actions:
        print(f"  data-action: {a['data-action'][:100]} tag={a.name}")

# The initiate form - this might start the 2FA setup
print("\n=== Initiate form ===")
init_form = soup.find("form", {"action": "/settings/two_factor_authentication/setup/initiate"})
if init_form:
    print(init_form.prettify()[:1000])
