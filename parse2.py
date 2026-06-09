import os
f = open("2fa_intro.html", "r", encoding="utf-8")
html = f.read()
f.close()
print("File size:", len(html))

# Search for key patterns
import re
patterns = [
    ("otpauth", r"otpauth"),
    ("totp", r"totp"),
    ("secret", r"secret"),
    ("setup.key", r"setup.key"),
    ("base32", r"[A-Z2-7]{16,}"),
    ("qr", r"qr"),
    ("scan", r"scan"),
    ("authenticator", r"authenticator"),
    ("verify", r"verify"),
    ("recovery", r"recovery"),
]

for name, pat in patterns:
    matches = re.findall(pat, html, re.I)
    print(f"  {name}: {len(matches)} matches")

# Find text content around "Two-factor" or "2FA"
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")

# Get visible text
main = soup.find("main") or soup.find("div", {"id": "js-repo-pjax-container"}) or soup.find("div", {"role": "main"})
if main:
    text = main.get_text(separator="\n", strip=True)
    lines = [l for l in text.split("\n") if l.strip()]
    print(f"\n=== Main content ({len(lines)} lines) ===")
    for line in lines[:80]:
        print(f"  {line[:120]}")
else:
    # Just print all visible text
    for tag in soup.find_all(["h1","h2","h3","h4","p","label","button","a","span","li"]):
        txt = tag.get_text(strip=True)
        if txt and len(txt) > 3 and len(txt) < 200:
            if any(kw in txt.lower() for kw in ["factor","auth","key","secret","scan","setup","verify","enable","recovery","code","sms","app"]):
                print(f"  <{tag.name}>: {txt[:120]}")
