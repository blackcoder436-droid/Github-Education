"""Test education form step 2 submission with base64 photo."""
import os, re, json, time, base64
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

time.sleep(2)

# Step 1: Submit initial form
print("\n=== Step 1: Initial form ===")
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
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new",
    },
)
print(f"Step 1 response: {resp2.status_code}")

soup2 = BeautifulSoup(resp2.text, "html.parser")
form2 = soup2.find("form")
if not form2:
    print("No form in step 2 response!")
    text = soup2.get_text(strip=True)
    print(f"Body: {text[:200]}")
    exit(1)

token2 = form2.find("input", {"name": "authenticity_token"}).get("value")
print(f"Step 2 form found, token: {token2[:20]}...")

# Create a minimal test image (1x1 white pixel JPEG)
# This is a valid minimal JPEG
import struct
# Just create a simple small PNG instead
import io, zlib

def create_test_png(w=100, h=100):
    """Create a minimal red PNG image."""
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return struct.pack('>I', len(data)) + c + crc
    
    # IHDR
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    
    # IDAT - red pixels
    raw = b''
    for y in range(h):
        raw += b'\x00'  # filter none
        for x in range(w):
            raw += b'\xff\x00\x00'  # red
    
    compressed = zlib.compress(raw)
    
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', ihdr)
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    return png

test_image = create_test_png(100, 100)
b64_image = base64.b64encode(test_image).decode()
data_url = f"data:image/png;base64,{b64_image}"

print(f"Test image: {len(test_image)} bytes, data URL: {len(data_url)} chars")

# Step 2: Submit with proof
print("\n=== Step 2: Upload proof ===")

# Extract all hidden fields from step 2 form
data2 = {}
for inp in form2.find_all("input", type="hidden"):
    name = inp.get("name")
    val = inp.get("value", "")
    if name:
        data2[name] = val

# Set our values
data2["dev_pack_form[proof_type]"] = "4. Dated class schedule for the semester"
data2["dev_pack_form[photo_proof]"] = data_url
data2["dev_pack_form[form_variant]"] = "upload_proof_form"
data2["submit"] = "Submit Application"

print(f"Submitting step 2 ({len(data2)} fields):")
for k, v in data2.items():
    if k == "dev_pack_form[photo_proof]":
        print(f"  {k} = [data URL, {len(v)} chars]")
    else:
        print(f"  {k} = {v[:80]}")

time.sleep(3)
resp3 = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data=data2,
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/benefits",
    },
)
print(f"\nStep 2 response: {resp3.status_code} Len: {len(resp3.text)}")

with open("edu_final_result.html", "w", encoding="utf-8") as f:
    f.write(resp3.text)
print("Saved edu_final_result.html")

soup3 = BeautifulSoup(resp3.text, "html.parser")
text = soup3.get_text(separator="\n", strip=True)
lines = [l for l in text.split("\n") if l.strip()]
print(f"\nResponse ({len(lines)} lines):")
for line in lines[:30]:
    print(f"  {line[:150]}")

# Check for errors
for err in soup3.find_all(class_=re.compile(r"error|flash|alert|Banner")):
    errtext = err.get_text(strip=True)[:200]
    if errtext:
        print(f"  ERROR: {errtext}")

# Check for success
for success in soup3.find_all(class_=re.compile(r"success|notice")):
    stext = success.get_text(strip=True)[:200]
    if stext:
        print(f"  SUCCESS: {stext}")

# Also try regular POST (without turbo-frame)
print("\n\n=== Try regular POST for step 2 ===")
time.sleep(3)

# Re-do step 1
resp4 = c.get("/settings/education/developer_pack_applications/new")
soup4 = BeautifulSoup(resp4.text, "html.parser")
form4 = soup4.find("form", {"action": "/settings/education/developer_pack_applications"})
token4 = form4.find("input", {"name": "authenticity_token"}).get("value")

data4 = {
    "authenticity_token": token4,
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
time.sleep(2)
resp5 = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data=data4,
    headers={
        **c.HEADERS,
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new",
    },
)
print(f"Step 1 (regular): {resp5.status_code} URL: {resp5.url}")

# Get the form from this response
soup5 = BeautifulSoup(resp5.text, "html.parser")
form5 = soup5.find("form", action=re.compile(r"developer_pack"))
if form5:
    token5 = form5.find("input", {"name": "authenticity_token"}).get("value")
    
    data5 = {}
    for inp in form5.find_all("input", type="hidden"):
        name = inp.get("name")
        val = inp.get("value", "")
        if name:
            data5[name] = val
    
    data5["dev_pack_form[proof_type]"] = "4. Dated class schedule for the semester"
    data5["dev_pack_form[photo_proof]"] = data_url
    data5["dev_pack_form[form_variant]"] = "upload_proof_form"
    data5["submit"] = "Submit Application"
    
    time.sleep(3)
    resp6 = c.session.post(
        f"{c.BASE}/settings/education/developer_pack_applications",
        data=data5,
        headers={
            **c.HEADERS,
            "Origin": c.BASE,
            "Referer": f"{c.BASE}/settings/education/benefits",
        },
        allow_redirects=False,
    )
    print(f"Step 2 (regular): {resp6.status_code}")
    loc = resp6.headers.get("Location", "none")
    print(f"Location: {loc}")
    
    if resp6.status_code in (301, 302, 303):
        url = loc if loc.startswith("http") else f"{c.BASE}{loc}"
        resp7 = c.session.get(url)
        print(f"Redirect: {resp7.status_code} URL: {resp7.url}")
        with open("edu_final_redirect.html", "w", encoding="utf-8") as f:
            f.write(resp7.text)
        soup7 = BeautifulSoup(resp7.text, "html.parser")
        text7 = soup7.get_text(separator="\n", strip=True)
        lines7 = [l for l in text7.split("\n") if l.strip() and len(l.strip()) > 5]
        for line in lines7[:20]:
            print(f"  {line[:150]}")
    elif resp6.status_code == 200:
        with open("edu_final_200.html", "w", encoding="utf-8") as f:
            f.write(resp6.text)
        soup6 = BeautifulSoup(resp6.text, "html.parser")
        
        for err in soup6.find_all(class_=re.compile(r"error|flash|Banner")):
            errtext = err.get_text(strip=True)[:200]
            if errtext:
                print(f"  ERROR: {errtext}")
        
        text6 = soup6.get_text(separator="\n", strip=True)
        lines6 = [l for l in text6.split("\n") if l.strip() and len(l.strip()) > 5]
        for line in lines6[:20]:
            print(f"  {line[:150]}")
