"""Extract full b.u chunk URL mapping and download webcam chunks."""
import re, os, time
from dotenv import load_dotenv
from client import GitHubClient
load_dotenv()

with open("wp_runtime_raw.js", "rb") as f:
    runtime = f.read().decode("utf-8", errors="replace")

# Find b.u= function - it's a long ternary chain
idx = runtime.find('b.u=e=>"')
if idx < 0:
    print("b.u function not found!")
    exit(1)

# Extract until the end of the function (next b. assignment or semicolon before next var)
# The chain ends with : followed by e+"-"+{hash_map}[e]+".js"
# Find the end - look for the next ,b. pattern
end_candidates = []
depth = 0
for i in range(idx, len(runtime)):
    ch = runtime[i]
    if ch == '(':
        depth += 1
    elif ch == ')':
        depth -= 1
    elif ch == ',' and depth == 0:
        # Check if next is b.
        if runtime[i+1:i+3] == 'b.':
            end_candidates.append(i)
            break

u_func = runtime[idx:end_candidates[0]] if end_candidates else runtime[idx:idx+5000]
print(f"b.u function length: {len(u_func)}")

# Extract all chunk ID -> filename mappings
# Pattern: "CHUNKID"===e?"FILENAME.js"
mappings = re.findall(r'"(\d+)"===e\?"([^"]+\.js)"', u_func)
print(f"Direct mappings: {len(mappings)}")
for cid, fname in mappings:
    print(f"  {cid} -> {fname}")

# Also look for the fallback pattern (e+"-"+{hash}[e]+".js")
fallback = re.search(r'e\+"-"\+(\{[^}]+\})\[e\]\+"\.js"', u_func)
if fallback:
    hash_obj = fallback.group(1)
    fb_mappings = re.findall(r'(\d+):"([a-f0-9]+)"', hash_obj)
    print(f"\nFallback hash mappings: {len(fb_mappings)}")
else:
    # Try another pattern: ""+e+"-"+{hash}[e]+".js"  
    fallback2 = re.search(r'""\+e\+"-"\+(\{[^}]+\})\[e\]\+"\.js"', u_func)
    if fallback2:
        hash_obj = fallback2.group(1)
        fb_mappings = re.findall(r'(\d+):"([a-f0-9]+)"', hash_obj)
        print(f"\nFallback hash mappings: {len(fb_mappings)}")
    else:
        fb_mappings = []
        print(f"\nNo fallback pattern found")
        # Print the end of the u_func to see the fallback
        print(f"\nu_func end:\n{u_func[-500:]}")

# Build full URL map
chunk_urls = {}
for cid, fname in mappings:
    chunk_urls[cid] = f"https://github.githubassets.com/assets/{fname}"
for cid, h in fb_mappings:
    if cid not in chunk_urls:
        chunk_urls[cid] = f"https://github.githubassets.com/assets/{cid}-{h}.js"

# Webcam chunks
webcam_ids = ['13726', '59299', '83465', '90225', '98131', '7542', '29434', '2966',
              '28839', '49863', '17383', '68751', '39371', '34646', '60481', '63991',
              '24729', '22072']

print(f"\n=== Webcam chunk URLs ===")
for cid in webcam_ids:
    if cid in chunk_urls:
        print(f"  {cid}: {chunk_urls[cid]}")
    else:
        print(f"  {cid}: NOT FOUND")

# Download webcam chunks
c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
time.sleep(1)

webcam_keywords = ['webcam', 'camera', 'photo_proof', 'formFieldId', 'toDataURL', 
                   'getUserMedia', 'capturePhoto', 'canvas', 'MediaStream',
                   'snapshot', 'hidden', 'getElementById', 'allowFileUpload',
                   'proof', 'upload']

print(f"\n=== Downloading and searching chunks ===")
for cid in webcam_ids:
    url = chunk_urls.get(cid)
    if not url:
        continue
    resp = c.session.get(url)
    if resp.status_code != 200:
        print(f"  {cid}: HTTP {resp.status_code}")
        continue
    content = resp.text
    hits = [kw for kw in webcam_keywords if kw.lower() in content.lower()]
    if hits:
        print(f"  {cid} ({len(content)} bytes): HITS = {hits}")
        # Save chunks with important hits
        if any(h in ['webcam', 'formFieldId', 'photo_proof', 'toDataURL', 'getUserMedia', 'allowFileUpload'] for h in hits):
            with open(f"chunk_{cid}.js", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"    -> Saved as chunk_{cid}.js")
    else:
        print(f"  {cid} ({len(content)} bytes): no relevant hits")
    time.sleep(0.3)
