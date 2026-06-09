"""Debug the exact HTTP request/response for step 2."""
import os, re, json, time, base64
from urllib.parse import urlencode
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
import requests as req
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {'OK' if ok else 'FAIL'}")

time.sleep(2)

# Step 1 fresh
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

print("\n=== Step 1 ===")
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
print(f"Step 1: {resp2.status_code}")
print(f"Response headers:")
for k, v in resp2.headers.items():
    if k.lower() in ('set-cookie', 'location', 'content-type', 'x-request-id'):
        print(f"  {k}: {v[:100]}")

# Check if there's a session cookie set
print(f"\nCookies after step 1:")
for cookie in c.session.cookies:
    if "education" in cookie.name.lower() or "application" in cookie.name.lower() or "dev_pack" in cookie.name.lower():
        print(f"  {cookie.name}={cookie.value[:50]}")

soup2 = BeautifulSoup(resp2.text, "html.parser")
form2 = soup2.find("form")
token2 = form2.find("input", {"name": "authenticity_token"}).get("value")

# Get a simpler photo
img_data = base64.b64encode(b'\xff\xd8\xff\xe0' + b'\x00' * 100 + b'\xff\xd9').decode()
simple_data_url = f"data:image/jpeg;base64,{img_data}"

# Prepare step 2 data - include BOTH form_variant values  
print("\n=== Step 2 ===")
# Let me try sending via tuples (allow duplicate keys)
data2_items = [
    ("authenticity_token", token2),
    ("dev_pack_form[proof_type]", "1. Dated school ID"),
    ("dev_pack_form[photo_proof]", "TEST_VALUE_123"),
    ("dev_pack_form[application_type]", "student"),
    ("dev_pack_form[browser_location]", "Yangon, Myanmar"),
    ("dev_pack_form[form_variant]", "initial_form"),
    ("dev_pack_form[latitude]", "16.8661"),
    ("dev_pack_form[location_shared]", "true"),
    ("dev_pack_form[longitude]", "96.1951"),
    ("dev_pack_form[school_email]", "thawkhant.1280@gmail.com"),
    ("dev_pack_form[school_name]", "SKT International College"),
    ("dev_pack_form[utm_content]", ""),
    ("dev_pack_form[utm_source]", ""),
    ("dev_pack_form[form_variant]", "upload_proof_form"),
    ("submit", "Submit Application"),
]

# Encode as form data manually to check
encoded = urlencode(data2_items)
print(f"Encoded body length: {len(encoded)} chars")
# Find proof_type in encoded
idx = encoded.find("proof_type")
print(f"proof_type in body: {encoded[idx:idx+100]}")

time.sleep(3)

# Use a PreparedRequest to inspect what's actually sent
from requests import Request
prep = Request(
    'POST',
    f"{c.BASE}/settings/education/developer_pack_applications",
    data=data2_items,
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/benefits",
    },
)
prepared = c.session.prepare_request(prep)
print(f"\nPrepared request:")
print(f"  URL: {prepared.url}")
print(f"  Method: {prepared.method}")
print(f"  Headers:")
for k, v in prepared.headers.items():
    print(f"    {k}: {v[:80]}")
print(f"  Body length: {len(prepared.body) if prepared.body else 0}")
if prepared.body:
    body_str = prepared.body if isinstance(prepared.body, str) else prepared.body.decode()
    # Find proof_type
    idx2 = body_str.find("proof_type")
    if idx2 >= 0:
        print(f"  proof_type in body: {body_str[idx2:idx2+100]}")
    idx3 = body_str.find("photo_proof")
    if idx3 >= 0:
        print(f"  photo_proof in body: {body_str[idx3:idx3+80]}")

# Send the request
resp3 = c.session.send(prepared)
print(f"\nStep 2 response: {resp3.status_code}")
print(f"Response headers:")
for k, v in resp3.headers.items():
    if k.lower() in ('content-type', 'location', 'x-request-id'):
        print(f"  {k}: {v}")

soup3 = BeautifulSoup(resp3.text, "html.parser")
# Check error
err = soup3.find(class_=re.compile(r"Banner--error|flash-error"))
if err:
    print(f"Error: {err.get_text(strip=True)[:200]}")

# Check returned values
form3 = soup3.find("form")
if form3:
    for inp in form3.find_all("input", {"name": re.compile(r"proof_type|photo_proof")}):
        name = inp.get("name")
        val = inp.get("value")
        has_attr = "value" in inp.attrs
        print(f"  {name}: value='{val}' has_value_attr={has_attr}")

# Check if the error is for proof_type or photo_proof specifically
print("\n=== Validation messages ===")
for el in soup3.find_all(True, class_=re.compile(r"FormControl-inlineValidation")):
    hidden = el.get("hidden")
    text = el.get_text(strip=True)[:100]
    # Find parent label
    parent = el.parent
    label = ""
    while parent:
        lbl = parent.find("label", class_="FormControl-label")
        if lbl:
            label = lbl.get_text(strip=True)[:50]
            break
        parent = parent.parent
    if text and hidden is None:
        print(f"  VISIBLE: label='{label}' text='{text}'")
    elif hidden is not None:
        pass  # hidden, no error
