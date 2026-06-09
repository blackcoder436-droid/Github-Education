"""Analyze webpack runtime chunk URL generation."""
import re

with open("wp_runtime_raw.js", "rb") as f:
    runtime = f.read().decode("utf-8", errors="replace")

# Search for the .u function that generates chunk URLs
# Webpack 5 pattern: __webpack_require__.u = function(chunkId) { return ... }
# or: a.u = chunkId => "assets/" + {...}[chunkId] + ".js"

# Find all references to .u =
for m in re.finditer(r'\.u\s*=\s*', runtime):
    start = m.start()
    # Get context
    ctx = runtime[max(0, start-50):min(len(runtime), start+500)]
    print(f"  .u at offset {start}:\n{ctx}\n{'='*60}")

print("\n\n=== Looking for chunk filename function ===")
# Also look for patterns with chunkId
for m in re.finditer(r'chunkId|chunk_id', runtime, re.I):
    start = m.start()
    ctx = runtime[max(0, start-100):min(len(runtime), start+200)]
    print(f"  chunkId at {start}: ...{ctx}...")
    print()

print("\n\n=== Looking for assets/ path ===")
for m in re.finditer(r'assets/', runtime):
    start = m.start()
    ctx = runtime[max(0, start-200):min(len(runtime), start+300)]
    print(f"  assets/ at {start}: ...{ctx}...")
    print()
    
print("\n\n=== Looking for .js extension ===")
count = 0
for m in re.finditer(r'\.js["\']', runtime):
    start = m.start()
    ctx = runtime[max(0, start-150):min(len(runtime), start+50)]
    if 'chunk' in ctx.lower() or 'hash' in ctx.lower() or '+' in ctx:
        print(f"  .js at {start}: ...{ctx}...")
        count += 1
        if count > 5:
            break
