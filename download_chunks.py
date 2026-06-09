"""Download webcam-upload chunks and find the photo_proof logic."""
import re, os, time, json
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

# Load runtime to get hash maps
with open("wp_runtime_raw.js", "rb") as f:
    runtime = f.read().decode("utf-8", errors="replace")

# Extract both hash map objects
hash_maps = re.findall(r'\{(?:\d+:"[a-f0-9]+",?\s*)+\}', runtime)
print(f"Found {len(hash_maps)} hash maps")

# Parse all entries
full_map = {}
for hm in hash_maps:
    for m in re.finditer(r'(\d+):"([a-f0-9]+)"', hm):
        full_map[m.group(1)] = m.group(2)

print(f"Total chunk->hash entries: {len(full_map)}")

# All webcam chunk IDs
chunk_ids = ['13726', '59299', '83465', '90225', '98131', '7542', '29434', '2966',
             '28839', '49863', '17383', '68751', '39371', '34646', '60481', '63991',
             '24729', '22072']

# Build URLs
base = "https://github.githubassets.com/assets/"
urls = {}
for cid in chunk_ids:
    if cid in full_map:
        urls[cid] = f"{base}{cid}-{full_map[cid]}.js"
    else:
        print(f"  WARNING: no hash for chunk {cid}")

print(f"Resolved URLs: {len(urls)}/{len(chunk_ids)}")

# Login and download chunks
c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
time.sleep(1)

# Download each chunk and search for webcam-related code
webcam_keywords = ['webcam', 'camera', 'photo_proof', 'formFieldId', 'toDataURL', 
                   'getUserMedia', 'capturePhoto', 'canvas', 'MediaStream', 
                   'video', 'snapshot', 'dataURL', 'blob', 'upload_proof',
                   'proof_type', 'hidden', 'value', 'getElementById']

found_chunks = []
for cid, url in urls.items():
    resp = c.session.get(url)
    if resp.status_code != 200:
        print(f"  Chunk {cid}: HTTP {resp.status_code}")
        continue
    
    content = resp.text
    hits = []
    for kw in webcam_keywords:
        if kw.lower() in content.lower():
            hits.append(kw)
    
    if hits:
        found_chunks.append((cid, content, hits))
        print(f"  Chunk {cid} ({len(content)} bytes): HITS = {hits}")
    else:
        print(f"  Chunk {cid} ({len(content)} bytes): no relevant hits")
    time.sleep(0.3)

# Analyze found chunks in detail
print(f"\n{'='*60}")
print(f"Chunks with webcam-related code: {len(found_chunks)}")

for cid, content, hits in found_chunks:
    print(f"\n--- Chunk {cid} (hits: {hits}) ---")
    
    # Search for key patterns
    for pattern in [
        r'formFieldId["\s:]+["\']?(\w+)',
        r'photo_proof',
        r'toDataURL[^)]*\)',
        r'getUserMedia',
        r'canvas.*?getContext',
        r'value\s*=.*?(?:dataURL|base64|blob)',
        r'getElementById\s*\([^)]+\)',
        r'\.value\s*=',
        r'hidden.*?value',
        r'capturePhoto|takePhoto|onCapture|onPhoto',
        r'webcam.*?upload|upload.*?webcam',
        r'proof_type',
        r'submit.*?form|form.*?submit',
    ]:
        for m in re.finditer(pattern, content, re.I):
            ctx_start = max(0, m.start() - 100)
            ctx_end = min(len(content), m.end() + 100)
            ctx = content[ctx_start:ctx_end].replace('\n', ' ')
            print(f"  [{pattern[:30]}]: ...{ctx}...")
            break  # Just first match per pattern

# Save the most relevant chunk(s) for detailed analysis
for cid, content, hits in found_chunks:
    if 'formFieldId' in hits or 'photo_proof' in hits or 'webcam' in hits or 'toDataURL' in hits:
        fname = f"chunk_{cid}.js"
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\nSaved {fname} ({len(content)} bytes)")
