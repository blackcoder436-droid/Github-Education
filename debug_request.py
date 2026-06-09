"""Debug: inspect EXACT request bytes for step 2 submission."""
import os, time, re, sys
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
from urllib.parse import urlencode
import requests
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {ok}")
time.sleep(2)

# Get form
resp0 = c.get("/settings/education/developer_pack_applications/new")
soup0 = BeautifulSoup(resp0.text, "html.parser")
frame = soup0.find("turbo-frame", id="dev-pack-form")
form0 = frame.find("form")
token0 = form0.find("input", attrs={"name": "authenticity_token"})["value"]
time.sleep(2)

# Step 1
step1_data = {
    "authenticity_token": token0,
    "dev_pack_form[application_type]": "student",
    "dev_pack_form[school_name]": "SKT International College",
    "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
    "dev_pack_form[latitude]": "16.8661",
    "dev_pack_form[longitude]": "96.1951",
    "dev_pack_form[location_shared]": "true",
    "dev_pack_form[form_variant]": "initial_form",
    "dev_pack_form[browser_location]": "",
    "dev_pack_form[utm_source]": "",
    "dev_pack_form[utm_content]": "",
    "continue": "Continue",
}

turbo_h = {
    "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
    "Turbo-Frame": "dev-pack-form",
    "Sec-Fetch-Mode": "same-origin",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Site": "same-origin",
    "Origin": "https://github.com",
    "Referer": "https://github.com/settings/education/developer_pack_applications/new",
}

resp1 = c.session.post(
    "https://github.com/settings/education/developer_pack_applications",
    data=step1_data,
    headers=turbo_h,
)
print(f"Step 1: {resp1.status_code}, proof_type={'proof_type' in resp1.text}")

soup1 = BeautifulSoup(resp1.text, "html.parser")
form1 = soup1.find("form")
token1 = form1.find("input", attrs={"name": "authenticity_token"})["value"]

# Now build step 2 and inspect the request
step2_data = {}
for inp in form1.find_all("input", type="hidden"):
    name = inp.get("name", "")
    value = inp.get("value", "")
    if name:
        step2_data[name] = value

# Override values
step2_data["dev_pack_form[proof_type]"] = "2. Dated official/unofficial transcript"
step2_data["dev_pack_form[photo_proof]"] = "data:image/jpeg;base64,AAAA"
step2_data["dev_pack_form[form_variant]"] = "upload_proof_form"
step2_data["submit"] = "Submit Application"

# Create a PreparedRequest to see exact bytes
req = requests.Request(
    "POST",
    "https://github.com/settings/education/developer_pack_applications",
    data=step2_data,
    headers=turbo_h,
)
prepped = c.session.prepare_request(req)

print(f"\n=== Request Details ===")
print(f"URL: {prepped.url}")
print(f"Method: {prepped.method}")
print(f"\nHeaders:")
for k, v in prepped.headers.items():
    print(f"  {k}: {v}")

body = prepped.body
print(f"\nBody type: {type(body)}")
print(f"Body length: {len(body) if body else 0}")

if isinstance(body, str):
    body_str = body
elif isinstance(body, bytes):
    body_str = body.decode('utf-8', errors='replace')
else:
    body_str = str(body)

print(f"\nFull body:")
print(body_str)

# Now let me also manually build the URL-encoded body and compare
manual_body = urlencode(step2_data)
print(f"\n\n=== Manual urlencode ===")
print(f"Length: {len(manual_body)}")
print(f"Body:")
print(manual_body)

# Check each key-value pair
print(f"\n\n=== Individual key-value pairs in body ===")
for pair in body_str.split("&"):
    if "proof" in pair.lower() or "variant" in pair.lower():
        print(f"  IMPORTANT: {pair}")
    else:
        print(f"  {pair[:80]}")

# Also decode and show
from urllib.parse import parse_qs
parsed = parse_qs(body_str, keep_blank_values=True)
print(f"\n=== Parsed back ===")
for k, v in parsed.items():
    if "proof" in k.lower() or "variant" in k.lower():
        print(f"  IMPORTANT: {k} = {v}")
