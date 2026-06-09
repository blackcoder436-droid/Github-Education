"""Download all webcam chunks with correct URLs."""
import re, os, time
from dotenv import load_dotenv
from client import GitHubClient
load_dotenv()

# Manually extracted URLs from runtime output
chunk_urls = {
    '13726': 'https://github.githubassets.com/assets/runtime-helpers-3cd71e27e349021d.js',
    '59299': None,  # CSS chunk, skip
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
    '22072': 'https://github.githubassets.com/assets/22072-c3b88bcc40dc78b1.js',
}

# Also need the entry module 92969
# It might be in one of these chunks or in the fallback hash map
# Let me check the hash map for 92969 too

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
time.sleep(1)

webcam_keywords = ['webcam', 'camera', 'photo_proof', 'formFieldId', 'toDataURL', 
                   'getUserMedia', 'capturePhoto', 'canvas', 'MediaStream',
                   'snapshot', 'getElementById', 'allowFileUpload',
                   'proof', 'upload', 'hidden']

print("=== Downloading webcam chunks ===")
important_chunks = []
for cid, url in chunk_urls.items():
    if url is None:
        continue
    resp = c.session.get(url)
    if resp.status_code != 200:
        print(f"  {cid}: HTTP {resp.status_code}")
        continue
    content = resp.text
    hits = [kw for kw in webcam_keywords if kw.lower() in content.lower()]
    if hits:
        important = any(h in ['webcam', 'formFieldId', 'photo_proof', 'toDataURL', 
                               'getUserMedia', 'allowFileUpload', 'capturePhoto'] for h in hits)
        marker = " *** IMPORTANT ***" if important else ""
        print(f"  {cid} ({len(content)} bytes): {hits}{marker}")
        if important:
            important_chunks.append((cid, content, hits))
            with open(f"chunk_{cid}.js", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"    -> Saved as chunk_{cid}.js")
    else:
        print(f"  {cid} ({len(content)} bytes): no hits")
    time.sleep(0.3)

# Deep analysis of important chunks
for cid, content, hits in important_chunks:
    print(f"\n{'='*60}")
    print(f"=== Deep analysis of chunk {cid} ===")
    
    # Find all relevant contexts
    for kw in ['webcam', 'formFieldId', 'photo_proof', 'toDataURL', 'getUserMedia',
               'allowFileUpload', 'capturePhoto', 'canvas', 'getElementById',
               'value=', '.value', 'hidden']:
        for m in re.finditer(re.escape(kw), content, re.I):
            start = max(0, m.start() - 150)
            end = min(len(content), m.end() + 150)
            ctx = content[start:end].replace('\n', ' ')
            print(f"\n  [{kw}] at {m.start()}: ...{ctx}...")
