"""Search ALL JS chunks for webcam/upload related code."""
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

# Collect all JS URLs
js_urls = []
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if src:
        js_urls.append(src)

print(f"Total JS files: {len(js_urls)}")

# Search each for webcam/upload/formFieldId/photo_proof
search_terms = ["webcam", "formFieldId", "photo_proof", "allowFileUpload", "toDataURL", "capturePhoto"]

for i, url in enumerate(js_urls):
    name = url.split("/")[-1]
    try:
        r = c.session.get(url, timeout=15)
        text = r.text
        found = []
        for term in search_terms:
            if term.lower() in text.lower():
                found.append(term)
        if found:
            print(f"\n[{i}] {name} ({len(text)} bytes) - MATCHES: {found}")
            # Show context for each match
            for term in found:
                for m in re.finditer(re.escape(term), text, re.I):
                    start = max(0, m.start() - 80)
                    end = min(len(text), m.end() + 80)
                    print(f"  {term}: ...{text[start:end]}...")
                    break  # Just show first match
    except Exception as e:
        print(f"[{i}] {name}: ERROR {e}")
    time.sleep(0.2)

print("\nDone!")
