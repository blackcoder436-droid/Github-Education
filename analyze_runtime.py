"""Analyze wp-runtime JS for chunk loading mechanism."""
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

for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if "wp-runtime" in src:
        r = c.session.get(src)
        text = r.text
        with open("wp_runtime.js", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Saved wp_runtime.js ({len(text)} bytes)")
        
        # Look for the chunk URL builder function
        # Find patterns like: __webpack_require__.p + ... + chunk + ...
        # Or: "https://...assets/" + ... 
        
        # Find all string literals that look like hashes
        hashes = re.findall(r'"([a-f0-9]{16,20})"', text)
        print(f"\nHash-like strings: {len(hashes)}")
        
        # Find the __webpack_require__.u function (chunk URL generation)
        for m in re.finditer(r'\.u\s*=\s*function', text):
            start = m.start()
            # Find the closing brace
            depth = 0
            end = start
            for i in range(start, min(start + 2000, len(text))):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            print(f"\nChunk URL function: {text[start:end]}")
            break
        
        # Also look for __webpack_require__.p (public path)
        for m in re.finditer(r'\.p\s*=\s*"[^"]+"', text):
            print(f"\nPublic path: {m.group()}")
            break
        
        # Look for the chunk loading function - usually e.ensure or e.f.j
        for m in re.finditer(r'\.f\.j\s*=\s*function', text):
            start = m.start()
            depth = 0
            for i in range(start, min(start + 3000, len(text))):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            print(f"\nJSON-P function length: {end - start}")
            print(text[start:start+500])
            break
        
        break

# Also check element-registry for partial name mappings
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if "element-registry" in src:
        r = c.session.get(src)
        text = r.text
        with open("element_registry.js", "w", encoding="utf-8") as f:
            f.write(text)
        print(f"\nSaved element_registry.js ({len(text)} bytes)")
        
        # Find react-partial mapping
        for m in re.finditer(r'.{0,100}react.partial.{0,100}', text, re.I):
            print(f"  react-partial: {m.group()[:200]}")
        
        # Find partial-name or webcam refs
        for m in re.finditer(r'.{0,100}partial.name.{0,100}', text, re.I):
            print(f"  partial-name: {m.group()[:200]}")
        
        break
