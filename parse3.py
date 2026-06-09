"""Extract TOTP secret from 2FA intro page."""
import re
from bs4 import BeautifulSoup

with open("2fa_intro.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Look for setup key / secret in nearby elements
# The text says "setup key" to manually configure
# Find elements near "setup key" text
print("=== Looking for setup key / secret ===")

# Search for elements with "secret" in attributes or nearby
for tag in soup.find_all(True):
    attrs = tag.attrs
    for attr_name, attr_val in attrs.items():
        if isinstance(attr_val, str) and "secret" in attr_name.lower():
            print(f"Attr: <{tag.name}>[{attr_name}] = {attr_val[:100]}")
        if isinstance(attr_val, str) and "secret" in attr_val.lower():
            print(f"Val: <{tag.name}>[{attr_name}] = {attr_val[:100]}")

# Look for the setup key display area
# Usually it's a button or code element that reveals the key
print("\n=== Elements with 'key' or 'setup' in class/id ===")
for tag in soup.find_all(True, {"class": re.compile(r"key|secret|setup|totp", re.I)}):
    print(f"  <{tag.name}> class={tag.get('class')} text={tag.text.strip()[:80]}")
for tag in soup.find_all(True, {"id": re.compile(r"key|secret|setup|totp", re.I)}):
    print(f"  <{tag.name}> id={tag.get('id')} text={tag.text.strip()[:80]}")

# Look for data- attributes with potential secret  
print("\n=== Data attributes ===")
for tag in soup.find_all(True):
    for attr_name in tag.attrs:
        if attr_name.startswith("data-") and any(kw in attr_name.lower() for kw in ["secret", "key", "totp", "otp", "setup", "qr"]):
            val = tag[attr_name]
            if isinstance(val, str):
                print(f"  <{tag.name}>[{attr_name}] = {val[:120]}")

# Look for React/Vue/Web component with props
print("\n=== Web components / custom elements ===")
for tag in soup.find_all(True):
    name = tag.name
    if "-" in name:  # Custom element
        attrs_str = " ".join(f"{k}={v}" for k,v in tag.attrs.items() if isinstance(v, str))[:200]
        if any(kw in attrs_str.lower() for kw in ["secret", "key", "totp", "qr"]):
            print(f"  <{name}> {attrs_str}")

# Look in script tags for embedded data
print("\n=== Script data ===")
for script in soup.find_all("script"):
    text = script.string or ""
    if any(kw in text.lower() for kw in ["secret", "totp", "setup_key", "setupkey"]):
        # Find the relevant line
        for line in text.split("\n"):
            if any(kw in line.lower() for kw in ["secret", "totp", "setup_key"]):
                print(f"  {line.strip()[:150]}")

# The form that verifies the TOTP code
print("\n=== App verify form (detailed) ===")
forms = soup.find_all("form", {"action": "/settings/two_factor_authentication/setup/verify"})
for form in forms:
    type_input = form.find("input", {"name": "type"})
    if type_input and type_input.get("value") == "app":
        print("Found app verify form!")
        # Get all content in this form's parent section
        parent_section = form.find_parent("div")
        if parent_section:
            # Look for nearby QR/secret elements
            for child in parent_section.find_all(True):
                if child.name == "img" and "qr" in str(child.attrs).lower():
                    print(f"  QR img: {child.get('src', '')[:100]}")
                if child.name in ("code", "pre", "kbd"):
                    print(f"  <{child.name}>: {child.text.strip()[:100]}")

# Look for base32 strings near "secret" or "key"
print("\n=== Base32 near keywords ===")
# Find positions of "secret" or "setup key" in html
for m in re.finditer(r"(?:secret|setup.key)", html, re.I):
    start = max(0, m.start() - 200)
    end = min(len(html), m.end() + 200)
    chunk = html[start:end]
    b32 = re.findall(r"[A-Z2-7]{16,}", chunk)
    if b32:
        print(f"  Near '{m.group()}' at pos {m.start()}: {b32}")
    else:
        # Show the chunk
        clean = re.sub(r"\s+", " ", chunk)
        print(f"  Near '{m.group()}': ...{clean[-150:]}...")
