"""Minimal step 2 test to isolate the issue."""
import os, re, json, time, base64
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
import requests as req
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {'OK' if ok else 'FAIL'}")

time.sleep(2)

# Step 1: Submit and get step 2 form via turbo
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

time.sleep(2)
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
print(f"Step 1: {resp2.status_code}")

soup2 = BeautifulSoup(resp2.text, "html.parser")
form2 = soup2.find("form")
if not form2:
    print("No form in step 1 response!")
    exit(1)

token2 = form2.find("input", {"name": "authenticity_token"}).get("value")
print(f"Token2: {token2[:20]}...")

# Print EVERY hidden input
print("\n=== All hidden inputs from step 2 form ===")
hidden_inputs = form2.find_all("input", type="hidden")
for inp in hidden_inputs:
    name = inp.get("name", "NO_NAME")
    val = inp.get("value", "NO_VALUE")[:80]
    print(f"  {name} = '{val}'")

# Create a test photo 
img_resp = req.get("https://randomuser.me/api/portraits/men/42.jpg", timeout=15)
jpeg_b64 = base64.b64encode(img_resp.content).decode()
data_url = f"data:image/jpeg;base64,{jpeg_b64}"
print(f"\nPhoto: {len(img_resp.content)} bytes, data URL: {len(data_url)} chars")

# Test A: Simple dict submission
print("\n=== Test A: Dict POST ===")
data_a = {
    "authenticity_token": token2,
    "dev_pack_form[proof_type]": "1. Dated school ID",
    "dev_pack_form[photo_proof]": data_url,
    "dev_pack_form[application_type]": "student",
    "dev_pack_form[browser_location]": "Yangon, Myanmar",
    "dev_pack_form[form_variant]": "upload_proof_form",
    "dev_pack_form[latitude]": "16.8661",
    "dev_pack_form[location_shared]": "true",
    "dev_pack_form[longitude]": "96.1951",
    "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
    "dev_pack_form[school_name]": "SKT International College",
    "dev_pack_form[utm_content]": "",
    "dev_pack_form[utm_source]": "",
    "submit": "Submit Application",
}

time.sleep(3)
resp_a = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data=data_a,
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/benefits",
    },
)
# Check response
soup_a = BeautifulSoup(resp_a.text, "html.parser")
err_a = soup_a.find(class_=re.compile(r"Banner--error"))
if err_a:
    print(f"  Error: {err_a.get_text(strip=True)[:100]}")
else:
    text_a = soup_a.get_text(strip=True)[:200]
    print(f"  Response: {text_a}")
# Check what values the server returned
form_a = soup_a.find("form")
if form_a:
    for inp in form_a.find_all("input", {"name": re.compile(r"proof_type|photo_proof")}):
        name = inp.get("name")
        val = inp.get("value", "")[:80]
        print(f"  Server returned: {name} = '{val}'")

# Test B: Try with application/json content type
print("\n=== Test B: JSON body ===")
time.sleep(2)
# Re-do step 1 to get fresh token
resp1b = c.get("/settings/education/developer_pack_applications/new")
soup1b = BeautifulSoup(resp1b.text, "html.parser")
form1b = soup1b.find("form", {"action": "/settings/education/developer_pack_applications"})
token1b = form1b.find("input", {"name": "authenticity_token"}).get("value")

time.sleep(2)
resp2b = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data={**data1, "authenticity_token": token1b},
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new",
    },
)
soup2b = BeautifulSoup(resp2b.text, "html.parser")
form2b = soup2b.find("form")
token2b = form2b.find("input", {"name": "authenticity_token"}).get("value") if form2b else ""

time.sleep(2)
resp_b = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    json={
        "authenticity_token": token2b,
        "dev_pack_form": {
            "proof_type": "1. Dated school ID",
            "photo_proof": data_url,
            "application_type": "student",
            "browser_location": "Yangon, Myanmar",
            "form_variant": "upload_proof_form",
            "latitude": "16.8661",
            "location_shared": "true",
            "longitude": "96.1951",
            "school_email": "thawkhant.1280@gmail.com",
            "school_name": "SKT International College",
            "utm_content": "",
            "utm_source": "",
        },
        "submit": "Submit Application",
    },
    headers={
        **c.HEADERS,
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/benefits",
    },
)
print(f"  JSON POST: {resp_b.status_code} Len: {len(resp_b.text)}")
soup_b = BeautifulSoup(resp_b.text, "html.parser")
err_b = soup_b.find(class_=re.compile(r"Banner--error|flash-error"))
if err_b:
    print(f"  Error: {err_b.get_text(strip=True)[:100]}")
else:
    text_b = soup_b.get_text(strip=True)[:200]
    print(f"  Response: {text_b}")

# Test C: multipart/form-data
print("\n=== Test C: Multipart form ===")
time.sleep(2)
# Re-do step 1
resp1c = c.get("/settings/education/developer_pack_applications/new")
soup1c = BeautifulSoup(resp1c.text, "html.parser")
form1c = soup1c.find("form", {"action": "/settings/education/developer_pack_applications"})
token1c = form1c.find("input", {"name": "authenticity_token"}).get("value")

time.sleep(2)
resp2c = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data={**data1, "authenticity_token": token1c},
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new",
    },
)
soup2c = BeautifulSoup(resp2c.text, "html.parser")
form2c = soup2c.find("form")
token2c = form2c.find("input", {"name": "authenticity_token"}).get("value") if form2c else ""

# Use multipart/form-data via files parameter
time.sleep(2)
multipart_data = {
    "authenticity_token": (None, token2c),
    "dev_pack_form[proof_type]": (None, "1. Dated school ID"),
    "dev_pack_form[photo_proof]": (None, data_url),
    "dev_pack_form[application_type]": (None, "student"),
    "dev_pack_form[browser_location]": (None, "Yangon, Myanmar"),
    "dev_pack_form[form_variant]": (None, "upload_proof_form"),
    "dev_pack_form[latitude]": (None, "16.8661"),
    "dev_pack_form[location_shared]": (None, "true"),
    "dev_pack_form[longitude]": (None, "96.1951"),
    "dev_pack_form[school_email]": (None, "thawkhant.1280@gmail.com"),
    "dev_pack_form[school_name]": (None, "SKT International College"),
    "dev_pack_form[utm_content]": (None, ""),
    "dev_pack_form[utm_source]": (None, ""),
    "submit": (None, "Submit Application"),
}

resp_c = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    files=multipart_data,
    headers={
        **{k: v for k, v in c.HEADERS.items() if k.lower() != "content-type"},
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/benefits",
    },
)
print(f"  Multipart: {resp_c.status_code} Len: {len(resp_c.text)}")
soup_c = BeautifulSoup(resp_c.text, "html.parser")
err_c = soup_c.find(class_=re.compile(r"Banner--error|flash-error"))
if err_c:
    print(f"  Error: {err_c.get_text(strip=True)[:100]}")
else:
    text_c = soup_c.get_text(strip=True)[:200]
    print(f"  Response: {text_c}")
    with open("edu_multipart_result.html", "w", encoding="utf-8") as f:
        f.write(resp_c.text)
