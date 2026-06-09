"""Find JS bundles from full education page and test upload endpoints."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
ok = c.login(
    os.environ['GITHUB_USERNAME'], 
    os.environ['GITHUB_PASSWORD'],
    totp_secret="SFDHLAA7MDH2S7TN",
)
print(f"Login: {'OK' if ok else 'FAIL'}")

time.sleep(2)

# Get the full education benefits page
resp = c.get("/settings/education/benefits")
html = resp.text
print(f"Benefits page: {resp.status_code} {len(html)} bytes")

soup = BeautifulSoup(html, "html.parser")

# Find ALL script tags
print("\n=== ALL script tags ===")
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    name = src.split("/")[-1]
    print(f"  {name}")

# Find link modulepreload
print("\n=== Module preloads ===")
for link in soup.find_all("link", rel="modulepreload"):
    href = link.get("href", "")
    name = href.split("/")[-1]
    if "webcam" in name.lower() or "upload" in name.lower() or "chunk" in name.lower():
        print(f"  {href}")

# Find all pre-loaded/deferred chunks
print("\n=== All import references in JS ===")
# Search for chunk loading patterns like "webcam" in inline scripts
for script in soup.find_all("script"):
    text = script.get_text()
    if len(text) > 100:
        # Look for chunk mappings
        if "webcam" in text.lower():
            # Find context around webcam
            idx = text.lower().find("webcam")
            start = max(0, idx - 100)
            end = min(len(text), idx + 200)
            print(f"  Found in inline script: ...{text[start:end]}...")

# Test upload policy endpoints
print("\n=== Testing upload endpoints ===")
time.sleep(1)
endpoints = [
    "/upload/policies/education",
    "/upload/policies/assets",
    "/upload/policies/developer-pack",
    "/settings/education/developer_pack_applications/upload",
]
for ep in endpoints:
    try:
        r = c.session.post(
            f"{c.BASE}{ep}",
            json={"name": "test.jpg", "size": 1000, "content_type": "image/jpeg"},
            headers={**c.HEADERS, "Accept": "application/json"},
        )
        print(f"  POST {ep}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"  POST {ep}: ERROR {e}")
    time.sleep(1)

# Check for GitHub's general upload mechanism
print("\n=== GitHub upload setup ===")
# Look for upload-policy-url patterns in the full page
for m in re.finditer(r'data-upload[^=]*=["\'][^"\']+["\']', html):
    print(f"  {m.group()}")

# Check for assets upload endpoint in meta tags or data attributes
for el in soup.find_all(True):
    for attr, val in el.attrs.items():
        if isinstance(val, str) and "upload" in attr.lower() and val:
            print(f"  {el.name}[{attr}] = {val}")

# Try fetching the app JS to find chunk manifests
print("\n=== App JS bundles ===")
app_scripts = [s.get("src") for s in soup.find_all("script", src=True)]
# Look for the main app bundle
for src in app_scripts:
    if "app" in src.lower():
        print(f"  {src}")
        # Try to fetch a small portion
        r = c.session.get(src, headers={"Range": "bytes=0-5000"})
        print(f"  Status: {r.status_code} Len: {len(r.text)}")
        # Search for webcam-upload reference
        if "webcam" in r.text.lower():
            idx = r.text.lower().find("webcam")
            print(f"  webcam ref found at {idx}: {r.text[max(0,idx-50):idx+100]}")
