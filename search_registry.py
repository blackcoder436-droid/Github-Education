"""Search element registry for webcam-upload chunk mapping."""
import re

with open("element_registry_raw.js", "rb") as f:
    raw = f.read()

text = raw.decode("utf-8", errors="replace")
print(f"Length: {len(text)}")

# Search for webcam
for m in re.finditer(r"webcam", text, re.I):
    start = max(0, m.start() - 200)
    end = min(len(text), m.end() + 200)
    print(f"\n  @{m.start()}: ...{text[start:end]}...")

# Also search for education-schools or education
for m in re.finditer(r"education", text, re.I):
    start = max(0, m.start() - 150)
    end = min(len(text), m.end() + 150)
    print(f"\n  @{m.start()}: ...{text[start:end]}...")
