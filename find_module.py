"""Find module 92969 (webcam-upload entry) in downloaded chunks."""
import re, os, time
from dotenv import load_dotenv
from client import GitHubClient
load_dotenv()

chunk_urls = {
    '13726': 'https://github.githubassets.com/assets/runtime-helpers-3cd71e27e349021d.js',
    '83465': 'https://github.githubassets.com/assets/primer-react-b33ebb42ade85c76.js',
    '90225': 'https://github.githubassets.com/assets/react-core-5860ae2cdde78efe.js',
    '98131': 'https://github.githubassets.com/assets/react-lib-e74a1db7c21f7e74.js',
    '7542': 'https://github.githubassets.com/assets/octicons-react-39f7eb9c9327cc85.js',
    '29434': 'https://github.githubassets.com/assets/29434-2774a83323075b9c.js',
    '2966': 'https://github.githubassets.com/assets/2966-25cb8e34b31306a4.js',
    '28839': 'https://github.githubassets.com/assets/28839-632d00a964e8dbd5.js',
    '49863': 'https://github.githubassets.com/assets/49863-8861e351482cb073.js',
    '17383': 'https://github.githubassets.com/assets/17383-c2d6c26148878501.js',
    '68751': 'https://github.githubassets.com/assets/68751-4d3d1aac1f81a213.js',
    '39371': 'https://github.githubassets.com/assets/39371-1dbcd92cbf0a739d.js',
    '34646': 'https://github.githubassets.com/assets/34646-bc4bb033e1164ca1.js',
    '60481': 'https://github.githubassets.com/assets/60481-f092b7fbcf4211fc.js',
    '63991': 'https://github.githubassets.com/assets/63991-b12b587cf80dae46.js',
    '24729': 'https://github.githubassets.com/assets/24729-b5fe8eb05b99c9dc.js',
}

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
time.sleep(1)

print("=== Looking for module 92969 ===")
for cid, url in chunk_urls.items():
    resp = c.session.get(url)
    if resp.status_code != 200:
        print(f"  {cid}: HTTP {resp.status_code}")
        continue
    content = resp.text
    
    # Look for module definition
    if '92969' in content:
        print(f"  {cid} ({len(content)} bytes): CONTAINS 92969!")
        # Find context around 92969
        for m in re.finditer(r'92969', content):
            start = max(0, m.start() - 50)
            end = min(len(content), m.end() + 200)
            ctx = content[start:end].replace('\n', ' ')
            print(f"    at {m.start()}: ...{ctx}...")
        
        # Save this chunk
        with open(f"chunk_{cid}_full.js", "w", encoding="utf-8") as f:
            f.write(content)
        print(f"    -> Saved")
    
    # Also look for common React patterns even with minification
    # Look for patterns like: getUserMedia, navigator.media, video, canvas, toDataURL
    # But in minified form they would still be string literals
    for kw in ['getUserMedia', 'toDataURL', 'MediaDevices', 'navigator.media',
               'video', 'canvas', 'Camera', 'capture', 'photo', 'webcam',
               'formFieldId', 'allowFileUpload', 'data:image']:
        if kw.lower() in content.lower():
            # Only report first match
            idx = content.lower().find(kw.lower())
            ctx = content[max(0,idx-80):min(len(content),idx+120)]
            print(f"  {cid}: found '{kw}' at {idx}: ...{ctx}...")
    
    time.sleep(0.3)

# Also check the entry module - it was loaded via bind(a, 92969)
# Module 92969 defines the React component export
# Let me also check if there's a separate lazy chunk for it
print("\n=== Checking if 92969 is in fallback hash map ===")
with open("wp_runtime_raw.js", "rb") as f:
    runtime = f.read().decode("utf-8", errors="replace")

for m in re.finditer(r'92969', runtime):
    start = max(0, m.start() - 50)
    end = min(len(runtime), m.end() + 100)
    print(f"  Runtime at {m.start()}: ...{runtime[start:end]}...")

# Also look for the actual webcam-upload lazy chunk filename
# The naming convention seen is: lazy-react-partial-webcam-upload-{hash}.js
# Let me search for "webcam" in the b.u function
idx = runtime.find('b.u=e=>"')
end = runtime.find(',b.', idx + 100)
u_func = runtime[idx:end] if end > idx else runtime[idx:idx+32000]
if 'webcam' in u_func.lower():
    widx = u_func.lower().find('webcam')
    print(f"\n  Found 'webcam' in b.u: ...{u_func[max(0,widx-100):widx+200]}...")
