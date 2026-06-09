"""Try different photo_proof formats and find webcam JS bundle."""
import os, re, json, time, base64, struct, zlib
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
ok = c.login(
    os.environ['GITHUB_USERNAME'], 
    os.environ['GITHUB_PASSWORD'],
    totp_secret="SFDHLAA7MDH2S7TN",
)
print(f"Login: {'OK' if ok else 'FAIL'}")

# First, find the webcam-upload JS bundle
time.sleep(2)
resp = c.get("/settings/education/benefits")
soup = BeautifulSoup(resp.text, "html.parser")

print("\n=== JS bundles ===")
for script in soup.find_all("script", src=True):
    src = script.get("src")
    if "webcam" in src.lower() or "upload" in src.lower() or "education" in src.lower() or "react" in src.lower():
        print(f"  {src}")

# Find all js chunks
chunks = []
for script in soup.find_all("script", src=True):
    src = script.get("src")
    if "chunk" in src.lower():
        chunks.append(src)
print(f"\nChunk scripts: {len(chunks)}")
for ch in chunks[:10]:
    print(f"  {ch}")

# Now let's download the webcam-upload CSS to find the JS bundle name
print("\n=== Looking for webcam JS ===")
# The CSS was: webcam-upload.e66da9df6eb089e6.module.css
# The JS would be something similar
# Let's try common patterns

# The react-partial webcam-upload component - let me try step 1 -> step 2 via regular post and check all script tags
time.sleep(2)

# Step 1
resp1 = c.get("/settings/education/developer_pack_applications/new")
soup1 = BeautifulSoup(resp1.text, "html.parser")
form1 = soup1.find("form", {"action": "/settings/education/developer_pack_applications"})
token1 = form1.find("input", {"name": "authenticity_token"}).get("value")

data1 = {
    "authenticity_token": token1,
    "dev_pack_form[application_type]": "student",
    "dev_pack_form[school_name]": "SKT International College",
    "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
    "dev_pack_form[latitude]": "16.8661",
    "dev_pack_form[longitude]": "96.1951",
    "dev_pack_form[location_shared]": "true",
    "dev_pack_form[utm_source]": "",
    "dev_pack_form[utm_content]": "",
    "dev_pack_form[form_variant]": "initial_form",
    "dev_pack_form[browser_location]": "Yangon, Myanmar",
    "continue": "Continue",
}
time.sleep(3)
resp2 = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data=data1,
    headers={**c.HEADERS, "Origin": c.BASE, "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new"},
)
print(f"\nStep 1 (regular): {resp2.status_code}")
soup2 = BeautifulSoup(resp2.text, "html.parser")

# Find all scripts in the full page response
print("\nAll script srcs:")
for script in soup2.find_all("script", src=True):
    src = script.get("src")
    if "webcam" in src.lower():
        print(f"  WEBCAM: {src}")

# Try to find the webcam-upload JS chunk
# Search in all scripts for 'photo_proof' or 'webcam'
print("\nInline scripts with webcam/photo:")
for script in soup2.find_all("script"):
    text = script.get_text()
    if "webcam" in text.lower() or "photo_proof" in text.lower():
        print(f"  Found: {text[:300]}...")

# Let me try to fetch the webcam JS
# From CSS: webcam-upload.e66da9df6eb089e6.module.css
# Try: webcam-upload-*.js patterns
base_url = "https://github.githubassets.com/assets/"
# The chunk ID from CSS is e66da9df6eb089e6
# Try fetching with that hash

test_urls = [
    f"{base_url}webcam-upload.e66da9df6eb089e6.js",
    f"{base_url}chunk-webcam-upload.e66da9df6eb089e6.js",
]

for url in test_urls:
    resp_test = c.session.get(url)
    print(f"\n  {url.split('/')[-1]}: {resp_test.status_code}")
    if resp_test.status_code == 200:
        print(f"  Content: {resp_test.text[:500]}")

# Better approach: look for all asset URLs in page source
print("\n=== Asset URLs with 'webcam' or 'upload' ===")
asset_pattern = re.compile(r'github\.githubassets\.com/assets/[^"\')\s]+(?:webcam|upload)[^"\')\s]*', re.I)
for match in asset_pattern.findall(resp2.text):
    print(f"  {match}")

# Also check chunk manifest  
manifest_pattern = re.compile(r'github\.githubassets\.com/assets/chunk-[^"\')\s]+', re.I)
chunks_found = manifest_pattern.findall(resp2.text)
print(f"\nChunk references: {len(chunks_found)}")

# Search for the actual webpack chunk that handles photo_proof
print("\n=== Searching for photo_proof in page ===")
photo_refs = [(m.start(), resp2.text[max(0,m.start()-50):m.end()+50]) for m in re.finditer(r'photo_proof', resp2.text)]
for pos, context in photo_refs:
    print(f"  @{pos}: ...{context}...")
