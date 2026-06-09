"""Find webcam-upload JS chunk by searching element-registry."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {'OK' if ok else 'FAIL'}")

time.sleep(2)
resp = c.get("/settings/education/benefits")
soup = BeautifulSoup(resp.text, "html.parser")

# Get the element-registry JS
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if "element-registry" in src:
        print(f"Element registry: {src}")
        r = c.session.get(src)
        print(f"  Status: {r.status_code} Length: {len(r.text)}")
        
        # Search for webcam
        for m in re.finditer(r'.{0,60}webcam.{0,60}', r.text, re.I):
            print(f"  Match: {m.group()[:120]}")
        break

# Also check the wp-runtime for chunk mapping
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if "wp-runtime" in src:
        print(f"\nWP Runtime: {src}")
        r = c.session.get(src)
        print(f"  Status: {r.status_code} Length: {len(r.text)}")
        
        # Search for webcam
        for m in re.finditer(r'.{0,40}webcam.{0,40}', r.text, re.I):
            print(f"  Match: {m.group()[:100]}")
        
        # Find chunk ID mapping for webcam
        for m in re.finditer(r'(\d+):\s*"[a-f0-9]+"', r.text):
            chunk_id = m.group(1)
            # Check nearby text for webcam
            start = max(0, m.start() - 200)
            end = min(len(r.text), m.end() + 200)
            nearby = r.text[start:end]
            if "webcam" in nearby.lower():
                print(f"  Chunk {chunk_id}: {nearby[:200]}")
        break

# Check react-core or react-lib for partial mappings
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if "react-core" in src or "react-lib" in src:
        name = src.split("/")[-1]
        r = c.session.get(src)
        print(f"\n{name}: {r.status_code} {len(r.text)} bytes")
        for m in re.finditer(r'.{0,50}webcam.{0,50}', r.text, re.I):
            print(f"  Match: {m.group()[:100]}")
        # Also search for photo_proof
        for m in re.finditer(r'.{0,50}photo.?proof.{0,50}', r.text, re.I):
            print(f"  photo_proof: {m.group()[:100]}")

# Try behaviors bundle
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if "behaviors" in src:
        print(f"\nBehaviors: {src}")
        r = c.session.get(src)
        print(f"  {r.status_code} {len(r.text)} bytes")
        for m in re.finditer(r'.{0,50}webcam.{0,50}', r.text, re.I):
            print(f"  Match: {m.group()[:100]}")
        break
