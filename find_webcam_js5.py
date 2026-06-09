"""Find webcam-upload chunk URL by analyzing page source."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")

time.sleep(2)
resp = c.get("/settings/education/benefits")
soup = BeautifulSoup(resp.text, "html.parser")

# Look at ALL inline scripts for chunk loading info
print("=== Searching inline scripts ===")
for i, script in enumerate(soup.find_all("script")):
    src = script.get("src", "")
    text = script.get_text()
    if text and len(text) > 20:
        # Look for webpack chunk loading patterns
        if any(term in text for term in ["__webpack", "webpackChunk", "chunkId", ".u=", "script.src"]):
            print(f"\n[script {i}] length={len(text)}")
            print(text[:500])
            print("...")
    
    # Look for module/import maps
    if script.get("type") == "importmap" or "importmap" in script.get("type", ""):
        print(f"\n[importmap] {text[:500]}")

# Check for dynamic chunk loading via self.__webpack_nonce__
print("\n=== Scripts with type/nonce ===")
for script in soup.find_all("script"):
    nonce = script.get("nonce", "")
    typ = script.get("type", "")
    src = script.get("src", "")
    if nonce or typ:
        name = src.split("/")[-1] if src else "(inline)"
        print(f"  type={typ} nonce={nonce[:10]}... name={name}")

# Get the element registry and look for partial-name to chunk mapping
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if "element-registry" in src:
        # Fetch without compression
        r = c.session.get(src, headers={"Accept-Encoding": "identity"})
        text = r.text
        print(f"\nElement registry: {len(text)} bytes, encoding={r.encoding}")
        
        # Save raw
        with open("element_registry_raw.js", "wb") as f:
            f.write(r.content)
        
        # Search for partial mappings
        # React partial maps partial-name to lazy import function
        for m in re.finditer(r'webcam|photo|upload|partial', text, re.I):
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 100)
            print(f"  @{m.start()}: {text[start:end]}")
        break

# Also get wp-runtime without compression
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if "wp-runtime" in src:
        r = c.session.get(src, headers={"Accept-Encoding": "identity"})
        text = r.text
        print(f"\nWP Runtime: {len(text)} bytes, encoding={r.encoding}")
        with open("wp_runtime_raw.js", "wb") as f:
            f.write(r.content)
        
        # Find chunk hash mapping - look for the chunkToUrlMapping
        # E.g. {12345:"abc123"} pattern
        for m in re.finditer(r'\{["\d]+\s*:\s*"[a-f0-9]+"(?:\s*,\s*["\d]+\s*:\s*"[a-f0-9]+")+\}', text):
            mapping = m.group()
            if len(mapping) > 100:
                print(f"\n  Chunk mapping ({len(mapping)} chars): {mapping[:300]}...")
                break
        
        # Find URL builder
        for m in re.finditer(r'githubassets\.com', text, re.I):
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 80)
            print(f"\n  URL ref: {text[start:end]}")
        break

# Try react-core too
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if "react-core" in src:
        r = c.session.get(src, headers={"Accept-Encoding": "identity"})
        text = r.text
        print(f"\nReact core: {len(text)} bytes")
        
        for m in re.finditer(r'webcam|photo.proof|formFieldId', text, re.I):
            start = max(0, m.start() - 100)
            end = min(len(text), m.end() + 100)
            print(f"  @{m.start()}: {text[start:end]}")
        break
