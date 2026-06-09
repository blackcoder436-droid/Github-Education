"""Check security page content after 2FA setup."""
import re
from bs4 import BeautifulSoup

with open("security_after_2fa.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Get the main content text around 2FA
text = soup.get_text(separator="\n", strip=True)
lines = text.split("\n")
for i, line in enumerate(lines):
    if any(kw in line.lower() for kw in ["two-factor", "2fa", "authenticator", "enabled", "disabled", "configured"]):
        print(f"  Line {i}: {line[:150]}")

# Find h2 headers
print("\n=== Headers ===")
for h in soup.find_all(["h1", "h2", "h3"]):
    print(f"  <{h.name}>: {h.text.strip()[:100]}")

# Check for the specific enable/disable link
print("\n=== 2FA related links ===")
for a in soup.find_all("a", href=re.compile(r"two_factor", re.I)):
    print(f"  {a.get('href')} -> {a.text.strip()[:60]}")

# Check for buttons
print("\n=== Buttons ===")
for btn in soup.find_all("button"):
    txt = btn.text.strip()[:80]
    if any(kw in txt.lower() for kw in ["factor", "disable", "enable", "2fa"]):
        print(f"  <button>: {txt}")
