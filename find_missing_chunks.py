"""Find the missing webcam chunk URLs in runtime."""
import re

with open("wp_runtime_raw.js", "rb") as f:
    runtime = f.read().decode("utf-8", errors="replace")

# Missing chunk IDs
missing = ['59299', '29434', '28839', '49863', '17383', '68751', '39371', 
           '34646', '60481', '63991', '24729', '22072']

# Search for each in runtime
for cid in missing:
    # Look for cid in the b.u function 
    for m in re.finditer(re.escape(cid), runtime):
        ctx = runtime[max(0, m.start()-30):min(len(runtime), m.end()+80)]
        print(f"  {cid} at {m.start()}: ...{ctx}...")

print("\n=== Extracting the fallback hash map ===")
# The b.u function ends with (...hash_map...)[e]+".js"
# Find the last occurrence of })[e]+".js" in b.u area
idx = runtime.find('b.u=e=>"')
# Find the hash map object - it should be a large {...} before [e]+".js"
end_pattern = ')[e]+".js"'
last_end = runtime.rfind(end_pattern, idx, idx + 35000)
if last_end > 0:
    # Find the matching { for this }
    brace_pos = last_end
    while brace_pos > idx and runtime[brace_pos] != '}':
        brace_pos -= 1
    # Now find the matching opening brace
    depth = 1
    open_pos = brace_pos - 1
    while open_pos > idx and depth > 0:
        if runtime[open_pos] == '}':
            depth += 1
        elif runtime[open_pos] == '{':
            depth -= 1
        open_pos -= 1
    open_pos += 1
    
    hash_obj = runtime[open_pos:brace_pos+1]
    print(f"Hash object: {len(hash_obj)} chars")
    
    # Parse entries
    entries = re.findall(r'(\d+):"([a-f0-9]+)"', hash_obj)
    print(f"Entries: {len(entries)}")
    
    hash_map = {e[0]: e[1] for e in entries}
    
    # Check missing chunks
    for cid in missing:
        if cid in hash_map:
            url = f"https://github.githubassets.com/assets/{cid}-{hash_map[cid]}.js"
            print(f"  {cid}: {url}")
        else:
            print(f"  {cid}: NOT in hash map")
