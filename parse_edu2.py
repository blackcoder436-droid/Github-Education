"""Inspect edu page for upload mechanism."""
import re, json
from bs4 import BeautifulSoup

with open("edu_try2_200.html", "r", encoding="utf-8") as f:
    html = f.read()
print(f"Length: {len(html)}")
soup = BeautifulSoup(html, "html.parser")

# Find webcam/upload related scripts
for script in soup.find_all("script"):
    src = script.get("src", "")
    if "webcam" in src.lower() or "upload" in src.lower() or "education" in src.lower():
        print(f"Script: {src}")
    text = script.get_text()
    if "webcam" in text.lower() or "photo_proof" in text.lower() or "upload" in text.lower():
        print(f"Inline script: {text[:200]}")

# Find any upload policy URLs
for el in soup.find_all(True, attrs={"src": re.compile(r"upload|policy", re.I)}):
    tag = el.name
    src = el.get("src")
    print(f"Upload element: {tag} src={src}")

# Find the webcam-upload React partial
for react in soup.find_all("react-partial"):
    name = react.get("partial-name", "")
    if name:
        script = react.find("script")
        data = script.get_text(strip=True) if script else ""
        print(f"React partial: {name} data={data[:200]}")

# Find form
form = soup.find("form", action=re.compile(r"education|developer_pack"))
if form:
    enc = form.get("enctype")
    print(f"\nForm action={form.get('action')} enctype={enc} method={form.get('method')}")
    for inp in form.find_all("input"):
        name = inp.get("name", "")
        val = inp.get("value", "")[:60]
        typ = inp.get("type", "text")
        if name:
            print(f"  {typ}: {name} = {val}")
    for btn in form.find_all("button", type="submit"):
        print(f"  submit: name={btn.get('name')} value={btn.get('value')}")

# Find any upload-related URLs anywhere
print("\n=== Upload URLs ===")
for a in soup.find_all(True):
    for attr in ["action", "src", "data-upload-policy-url", "data-direct-upload-url", "data-blob-url-template"]:
        val = a.get(attr, "")
        if val and ("upload" in val.lower() or "policy" in val.lower()):
            print(f"  {a.name} {attr}={val}")

# Check for any data-url or data-*-url attributes
print("\n=== All data-*-url attributes ===")
for el in soup.find_all(True):
    for k, v in el.attrs.items():
        if k.endswith("-url") and isinstance(v, str) and v.startswith("/"):
            print(f"  {el.name} {k}={v}")
