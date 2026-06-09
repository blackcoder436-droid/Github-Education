"""Try with real JPEG photo and different encodings."""
import os, re, json, time, base64, io
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
import requests
load_dotenv()

c = GitHubClient()
ok = c.login(
    os.environ['GITHUB_USERNAME'], 
    os.environ['GITHUB_PASSWORD'],
    totp_secret="SFDHLAA7MDH2S7TN",
)
print(f"Login: {'OK' if ok else 'FAIL'}")

# Download a real image
print("\nDownloading test image...")
img_resp = requests.get("https://randomuser.me/api/portraits/men/25.jpg", timeout=15)
print(f"Image: {img_resp.status_code} {len(img_resp.content)} bytes")

jpeg_b64 = base64.b64encode(img_resp.content).decode()
jpeg_data_url = f"data:image/jpeg;base64,{jpeg_b64}"
print(f"Data URL length: {len(jpeg_data_url)} chars")

# Helper to submit
def submit_initial(client):
    """Submit step 1 and return step 2 turbo response."""
    resp = client.get("/settings/education/developer_pack_applications/new")
    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", {"action": "/settings/education/developer_pack_applications"})
    token = form.find("input", {"name": "authenticity_token"}).get("value")
    
    data = {
        "authenticity_token": token,
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
    
    r = client.session.post(
        f"{client.BASE}/settings/education/developer_pack_applications",
        data=data,
        headers={
            **client.HEADERS,
            "Turbo-Frame": "dev-pack-form",
            "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
            "Origin": client.BASE,
            "Referer": f"{client.BASE}/settings/education/developer_pack_applications/new",
        },
    )
    return r

def try_step2(client, photo_value, label, extra_headers=None):
    """Submit step 2 with given photo value."""
    time.sleep(2)
    resp1 = submit_initial(client)
    soup = BeautifulSoup(resp1.text, "html.parser")
    form = soup.find("form")
    if not form:
        print(f"  [{label}] No form in step 1 response!")
        return
    
    token = form.find("input", {"name": "authenticity_token"}).get("value")
    
    data = {}
    for inp in form.find_all("input", type="hidden"):
        name = inp.get("name")
        val = inp.get("value", "")
        if name:
            data[name] = val
    
    data["dev_pack_form[proof_type]"] = "4. Dated class schedule for the semester"
    data["dev_pack_form[photo_proof]"] = photo_value
    data["dev_pack_form[form_variant]"] = "upload_proof_form"
    data["submit"] = "Submit Application"
    
    headers = {
        **client.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": client.BASE,
        "Referer": f"{client.BASE}/settings/education/benefits",
    }
    if extra_headers:
        headers.update(extra_headers)
    
    time.sleep(2)
    resp = client.session.post(
        f"{client.BASE}/settings/education/developer_pack_applications",
        data=data,
        headers=headers,
    )
    
    soup2 = BeautifulSoup(resp.text, "html.parser")
    # Check for errors
    errors = []
    for err in soup2.find_all(class_=re.compile(r"error|flash|Banner")):
        text = err.get_text(strip=True)[:200]
        if text:
            errors.append(text)
    
    text = soup2.get_text(separator="|", strip=True)
    
    if errors:
        print(f"  [{label}] Status: {resp.status_code} ERROR: {errors[0][:100]}")
    elif "Your application has been submitted" in text or "Thank you" in text:
        print(f"  [{label}] Status: {resp.status_code} SUCCESS!")
        with open(f"edu_{label}_success.html", "w", encoding="utf-8") as f:
            f.write(resp.text)
    else:
        print(f"  [{label}] Status: {resp.status_code} Text: {text[:200]}")
        with open(f"edu_{label}.html", "w", encoding="utf-8") as f:
            f.write(resp.text)

# Test 1: JPEG data URL
print("\n=== Test 1: JPEG data URL ===")
try_step2(c, jpeg_data_url, "jpeg_dataurl")

# Test 2: Raw base64 (no data: prefix)
print("\n=== Test 2: Raw base64 ===")
try_step2(c, jpeg_b64, "raw_b64")

# Test 3: PNG data URL (from canvas.toDataURL)
print("\n=== Test 3: PNG data URL ===")
# Convert JPEG to a simple data URL with PNG mime
png_data_url = f"data:image/png;base64,{jpeg_b64}"
try_step2(c, png_data_url, "png_dataurl")

# Test 4: Try without turbo-frame header 
print("\n=== Test 4: Regular POST ===")
time.sleep(2)
resp1 = c.get("/settings/education/developer_pack_applications/new")
soup1 = BeautifulSoup(resp1.text, "html.parser")
form1 = soup1.find("form", {"action": "/settings/education/developer_pack_applications"})
token1 = form1.find("input", {"name": "authenticity_token"}).get("value")

# Step 1 - regular
data_s1 = {
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
    data=data_s1,
    headers={**c.HEADERS, "Origin": c.BASE, "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new"},
)
print(f"Step 1 regular: {resp2.status_code}")

soup2 = BeautifulSoup(resp2.text, "html.parser")
form2 = soup2.find("form", action=re.compile(r"developer_pack"))
if form2:
    token2 = form2.find("input", {"name": "authenticity_token"}).get("value")
    data_s2 = {}
    for inp in form2.find_all("input", type="hidden"):
        name = inp.get("name")
        val = inp.get("value", "")
        if name:
            data_s2[name] = val
    
    data_s2["dev_pack_form[proof_type]"] = "4. Dated class schedule for the semester"
    data_s2["dev_pack_form[photo_proof]"] = jpeg_data_url
    data_s2["dev_pack_form[form_variant]"] = "upload_proof_form"
    data_s2["submit"] = "Submit Application"
    
    time.sleep(3)
    resp3 = c.session.post(
        f"{c.BASE}/settings/education/developer_pack_applications",
        data=data_s2,
        headers={**c.HEADERS, "Origin": c.BASE, "Referer": f"{c.BASE}/settings/education/benefits"},
        allow_redirects=False,
    )
    print(f"Step 2 regular: {resp3.status_code} Location: {resp3.headers.get('Location', 'none')}")
    
    if resp3.status_code == 302:
        redir = resp3.headers["Location"]
        if not redir.startswith("http"):
            redir = f"{c.BASE}{redir}"
        resp4 = c.session.get(redir)
        print(f"Redirect: {resp4.status_code} URL: {resp4.url}")
        soup4 = BeautifulSoup(resp4.text, "html.parser")
        for flash in soup4.find_all(class_=re.compile(r"flash|Banner|notice")):
            text = flash.get_text(strip=True)[:200]
            if text:
                print(f"  {text}")
    elif resp3.status_code == 200:
        soup3 = BeautifulSoup(resp3.text, "html.parser")
        for err in soup3.find_all(class_=re.compile(r"error|flash|Banner")):
            text = err.get_text(strip=True)[:200]
            if text:
                print(f"  ERROR: {text}")
        
        text3 = soup3.get_text(separator="|", strip=True)
        if len(text3) < 500:
            print(f"  Body: {text3}")
