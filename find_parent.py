"""Find the parent page that embeds the education turbo-frame."""
import re

# Check edu_benefits.html for turbo-frame references
html = open("edu_benefits.html", "r", encoding="utf-8").read()
print(f"edu_benefits.html: {len(html)} bytes")

# Find turbo frames
for m in re.finditer(r'<turbo-frame[^>]*>', html):
    tag = m.group()
    print(f"\nTurbo frame: {tag[:200]}")

# Find links to education developer pack
for m in re.finditer(r'developer_pack_applications[^"<]{0,100}', html):
    print(f"devpack ref: {m.group()[:150]}")

# Check the URL/title
for m in re.finditer(r'<title[^>]*>([^<]*)</title>', html):
    print(f"Title: {m.group(1).strip()}")

# Check for the education form or link to it
for m in re.finditer(r'href="[^"]*education[^"]*"', html):
    print(f"Education link: {m.group()[:150]}")
