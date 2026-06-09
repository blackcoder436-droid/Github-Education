"""Extract full webcam-upload chunk mapping and fetch the webcam code."""
import re, os, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

with open("element_registry_raw.js", "rb") as f:
    raw = f.read()
text = raw.decode("utf-8", errors="replace")

# Find the webcam-upload mapping
idx = text.find('react-partial[partial-name="webcam-upload"]')
if idx < 0:
    print("webcam-upload not found!")
    exit(1)

# Extract from the mapping start to the next mapping
# The pattern is: 'react-partial[...webcam-upload...]':()=>Promise.all([chunks]).then(a.bind(a,moduleId))
end = text.find(",'react-partial", idx + 20)
if end < 0:
    end = text.find("};", idx)
mapping_str = text[idx:end]
print(f"Webcam mapping:\n{mapping_str}\n")

# Extract chunk IDs
chunk_ids = re.findall(r'a\.e\("(\d+)"\)', mapping_str)
print(f"Chunk IDs ({len(chunk_ids)}): {chunk_ids}")

# Extract module ID from a.bind(a,XXXXX)
bind_match = re.search(r'a\.bind\(a,(\d+)\)', mapping_str)
if bind_match:
    module_id = bind_match.group(1)
    print(f"Module ID: {module_id}")
else:
    print("Module ID not found!")
    module_id = None

# Now need to find the chunk file URLs
# First get the chunk mapping (chunkId -> hash) from wp-runtime
with open("wp_runtime_raw.js", "rb") as f:
    runtime_raw = f.read()
runtime = runtime_raw.decode("utf-8", errors="replace")

# Find the chunk hash mapping function
# Look for patterns like: e[12345]="abc123" or chunkId=>{...12345:"abc123"...}
# Modern webpack uses a function like: __webpack_require__.u = function(chunkId) { return "assets/" + {chunk:hash}[chunkId] + ".js" }

# Try different patterns
print(f"\nRuntime length: {len(runtime)}")

# Pattern 1: Object literal with numeric keys
hash_maps = re.findall(r'\{(?:\d+:"[a-f0-9]+",?\s*)+\}', runtime)
print(f"Hash map objects found: {len(hash_maps)}")
for hm in hash_maps:
    if len(hm) > 100:
        print(f"  ({len(hm)} chars): {hm[:300]}...")

# Pattern 2: Switch/case style
switch = re.findall(r'case\s+(\d+):.*?"([a-f0-9]{16})"', runtime)
if switch:
    print(f"Switch cases: {len(switch)}")

# Pattern 3: Ternary chains - e===123?"hash":e===456?"hash":...
ternary = re.findall(r'===\s*(\d+)\s*\?\s*"([a-f0-9]{8,})"', runtime)
if ternary:
    print(f"Ternary patterns: {len(ternary)}")

# Let me just search near "githubassets" 
for m in re.finditer(r'githubassets', runtime, re.I):
    start = max(0, m.start() - 300)
    end = min(len(runtime), m.end() + 300)
    print(f"\n  URL context: ...{runtime[start:end]}...")

# Actually, the page already has existing chunk URLs loaded as scripts
# Let me match those to find the pattern
c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
time.sleep(2)
resp = c.get("/settings/education/benefits")
soup = BeautifulSoup(resp.text, "html.parser")

# Build map of chunk_id -> url from page scripts
page_chunk_map = {}
for script in soup.find_all("script", src=True):
    src = script.get("src", "")
    m = re.search(r'/(\d+)-([a-f0-9]+)\.js', src)
    if m:
        cid = m.group(1)
        chash = m.group(2)
        page_chunk_map[cid] = src
        
print(f"\nPage chunks: {len(page_chunk_map)}")

# Which webcam chunks are NOT on the page?
missing = [cid for cid in chunk_ids if cid not in page_chunk_map]
print(f"Missing chunks (not on page): {missing}")

# For missing chunks, try to construct URL from the runtime
# The URL pattern is: https://github.githubassets.com/assets/{chunkId}-{hash}.js
# We need the hash for each missing chunk
# Let me search the runtime for these specific chunk IDs
for cid in missing:
    # Search for the chunk ID followed by a hash in runtime
    for m in re.finditer(rf'{cid}["\s:]+["\']*([a-f0-9]{{8,20}})', runtime):
        h = m.group(1)
        url = f"https://github.githubassets.com/assets/{cid}-{h}.js"
        print(f"  {cid} -> hash={h}")
        break
