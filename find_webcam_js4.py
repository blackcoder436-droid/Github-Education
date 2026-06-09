"""Decode webpack chunk mapping from wp-runtime to find webcam chunk."""
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

# Get wp-runtime
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    if "wp-runtime" in src:
        r = c.session.get(src)
        runtime_text = r.text
        print(f"WP Runtime: {len(runtime_text)} bytes")
        
        # Find chunk ID to filename mapping
        # Typical webpack pattern: {chunkId: "hash"}
        # or e[chunkId] = "hash"
        
        # Look for the chunk hash mapping
        # Pattern like: 12345:"abc123def456"
        chunk_maps = re.findall(r'(\d+):\s*"([a-f0-9]{16})"', runtime_text)
        print(f"\nChunk mappings found: {len(chunk_maps)}")
        
        # Also find the URL template
        # Usually something like: return "https://..." + chunkId + "-" + hash + ".js"
        url_patterns = re.findall(r'"(https://github\.githubassets\.com/assets/)"', runtime_text)
        print(f"URL base: {url_patterns}")
        
        # Find all chunk IDs referenced in the page's scripts
        page_chunks = set()
        for s in soup.find_all("script", src=True):
            src2 = s.get("src", "")
            m = re.search(r'/(\d+)-([a-f0-9]+)\.js', src2)
            if m:
                page_chunks.add(m.group(1))
        
        # Find chunk IDs NOT on page (lazy-loaded)
        all_chunk_ids = {cid for cid, _ in chunk_maps}
        lazy_chunks = all_chunk_ids - page_chunks
        print(f"\nAll chunks: {len(all_chunk_ids)}, On page: {len(page_chunks)}, Lazy: {len(lazy_chunks)}")
        print(f"Lazy chunk IDs: {sorted(lazy_chunks)[:20]}")
        
        # For each lazy chunk, try to fetch and search for webcam
        base = "https://github.githubassets.com/assets/"
        chunk_hash_map = dict(chunk_maps)
        
        print(f"\n=== Searching lazy chunks for webcam... ===")
        for cid in sorted(lazy_chunks):
            h = chunk_hash_map.get(cid, "")
            if not h:
                continue
            url = f"{base}{cid}-{h}.js"
            try:
                r2 = c.session.get(url, timeout=10)
                if r2.status_code == 200:
                    if any(term in r2.text.lower() for term in ["webcam", "formfieldid", "photo_proof", "allowfileupload", "captureimage", "getusermedia"]):
                        print(f"\n  FOUND! Chunk {cid}: {url}")
                        print(f"  Size: {len(r2.text)} bytes")
                        # Save it
                        with open(f"chunk_{cid}.js", "w", encoding="utf-8") as f:
                            f.write(r2.text)
                        print(f"  Saved chunk_{cid}.js")
                        # Show context
                        for term in ["webcam", "formFieldId", "photo_proof", "allowFileUpload", "toDataURL", "getUserMedia"]:
                            for m in re.finditer(re.escape(term), r2.text, re.I):
                                start = max(0, m.start() - 100)
                                end = min(len(r2.text), m.end() + 100)
                                print(f"  {term}: ...{r2.text[start:end]}...")
                                break
            except Exception as e:
                pass
            time.sleep(0.1)
        
        break

print("\nDone!")
