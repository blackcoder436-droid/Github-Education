"""Test step 2 with exact Turbo fetch headers."""
import os, time, re, sys
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
import uuid
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {ok}")
time.sleep(2)

# Step 0: GET form page
resp0 = c.get("/settings/education/developer_pack_applications/new")
soup0 = BeautifulSoup(resp0.text, "html.parser")
frame = soup0.find("turbo-frame", id="dev-pack-form")
form0 = frame.find("form")
token0 = form0.find("input", attrs={"name": "authenticity_token"})["value"]
print(f"Step 0 OK")

# Step 1: Submit initial form
time.sleep(2)
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

# Use exact Turbo headers
turbo_headers = {
    "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
    "Turbo-Frame": "dev-pack-form",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "Sec-Fetch-Mode": "same-origin",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Site": "same-origin",
    "Origin": "https://github.com",
    "Referer": "https://github.com/settings/education/developer_pack_applications/new",
    "X-Requested-With": "XMLHttpRequest",
}

resp1 = c.session.post(
    "https://github.com/settings/education/developer_pack_applications",
    data=step1_data,
    headers=turbo_headers,
)
print(f"Step 1: {resp1.status_code}, {len(resp1.text)} bytes")
has_proof = "proof_type" in resp1.text
print(f"Has proof_type: {has_proof}")

if not has_proof:
    print("Step 1 FAILED")
    with open("turbo_step1_fail.html", "w", encoding="utf-8") as f:
        f.write(resp1.text)
    sys.exit(1)

# Parse step 2 form
soup1 = BeautifulSoup(resp1.text, "html.parser")
form1 = soup1.find("form")
token1 = form1.find("input", attrs={"name": "authenticity_token"})["value"]

# Collect all hidden inputs
hidden = {}
for inp in form1.find_all("input", type="hidden"):
    name = inp.get("name", "")
    value = inp.get("value", "")
    if name:
        hidden[name] = value

print(f"Step 2 form: {len(hidden)} hidden inputs, form_variant={hidden.get('dev_pack_form[form_variant]')}")

# Set step 2 values
step2_data = dict(hidden)
step2_data["authenticity_token"] = token1
step2_data["dev_pack_form[proof_type]"] = "2. Dated official/unofficial transcript"
step2_data["dev_pack_form[photo_proof]"] = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABsSFBcUERsXFhceHBsgKEIrKCUlKFE6PTBCYFVlZF9VXVtqeJmBanGQc1tdhbWGkJ6jq62rZ4C8ybqmx5moq6T/2wBDARweHigjKE4rK06kbl1upKSkpKSk/8AAEQgAAQABAwERAAIRAQMRAf/EABQAAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFAEBAAAAAAAAAAAAAAAAAAAAAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AE0A/9k="
step2_data["dev_pack_form[form_variant]"] = "upload_proof_form"
step2_data["submit"] = "Submit Application"
step2_data.pop("continue", None)

# Submit step 2 with exact Turbo headers
time.sleep(2)
turbo_headers2 = {
    "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
    "Turbo-Frame": "dev-pack-form",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "Sec-Fetch-Mode": "same-origin",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Site": "same-origin",
    "Origin": "https://github.com",
    "Referer": "https://github.com/settings/education/developer_pack_applications/new",
}

resp2 = c.session.post(
    "https://github.com/settings/education/developer_pack_applications",
    data=step2_data,
    headers=turbo_headers2,
)
print(f"\nStep 2 (Turbo headers): {resp2.status_code}, {len(resp2.text)} bytes")

soup2 = BeautifulSoup(resp2.text, "html.parser")
banner = soup2.find(class_="Banner-title")
if banner:
    print(f"Banner: {banner.get_text(strip=True)}")

proof_inp = soup2.find("input", attrs={"name": "dev_pack_form[proof_type]"})
if proof_inp:
    print(f"proof_type value: {proof_inp.get('value', '(no attr)')!r}")

photo_inp = soup2.find("input", attrs={"name": "dev_pack_form[photo_proof]"})
if photo_inp:
    print(f"photo_proof value: {photo_inp.get('value', '(no attr)')!r}")

with open("turbo_step2.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)

# ======= Test 2: Try with tuples (ordered data) =======
print("\n\n=== Test 2: Tuples with explicit Content-Type ===")
time.sleep(3)

# Fresh form
resp0c = c.get("/settings/education/developer_pack_applications/new")
soup0c = BeautifulSoup(resp0c.text, "html.parser")
frame0c = soup0c.find("turbo-frame", id="dev-pack-form")
form0c = frame0c.find("form")
token0c = form0c.find("input", attrs={"name": "authenticity_token"})["value"]
time.sleep(2)

step1c_data = dict(step1_data)
step1c_data["authenticity_token"] = token0c

resp1c = c.session.post(
    "https://github.com/settings/education/developer_pack_applications",
    data=step1c_data,
    headers=turbo_headers,
)

if "proof_type" not in resp1c.text:
    print("Step 1c failed")
    sys.exit(1)

soup1c = BeautifulSoup(resp1c.text, "html.parser")
form1c = soup1c.find("form")
token1c = form1c.find("input", attrs={"name": "authenticity_token"})["value"]

# Build step 2 as ordered tuples
step2_tuples = [
    ("authenticity_token", token1c),
    ("dev_pack_form[proof_type]", "2. Dated official/unofficial transcript"),
    ("dev_pack_form[photo_proof]", "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ=="),
    ("dev_pack_form[application_type]", "student"),
    ("dev_pack_form[browser_location]", ""),
    ("dev_pack_form[form_variant]", "upload_proof_form"),
    ("dev_pack_form[latitude]", "16.8661"),
    ("dev_pack_form[location_shared]", "true"),
    ("dev_pack_form[longitude]", "96.1951"),
    ("dev_pack_form[school_email]", "thawkhant.1280@gmail.com"),
    ("dev_pack_form[school_name]", "SKT International College"),
    ("dev_pack_form[utm_content]", ""),
    ("dev_pack_form[utm_source]", ""),
    ("submit", "Submit Application"),
]

time.sleep(2)
resp2c = c.session.post(
    "https://github.com/settings/education/developer_pack_applications",
    data=step2_tuples,
    headers=turbo_headers2,
)
print(f"Step 2 (tuples): {resp2c.status_code}, {len(resp2c.text)} bytes")

soup2c = BeautifulSoup(resp2c.text, "html.parser")
banner2c = soup2c.find(class_="Banner-title")
if banner2c:
    print(f"Banner: {banner2c.get_text(strip=True)}")

proof2c = soup2c.find("input", attrs={"name": "dev_pack_form[proof_type]"})
if proof2c:
    print(f"proof_type: {proof2c.get('value', '(no attr)')!r}")

# ======= Test 3: Try multipart with files param =======
print("\n\n=== Test 3: Multipart form-data ===")
time.sleep(3)

resp0d = c.get("/settings/education/developer_pack_applications/new")
soup0d = BeautifulSoup(resp0d.text, "html.parser")
frame0d = soup0d.find("turbo-frame", id="dev-pack-form")
form0d = frame0d.find("form")
token0d = form0d.find("input", attrs={"name": "authenticity_token"})["value"]
time.sleep(2)

step1d_data = dict(step1_data)
step1d_data["authenticity_token"] = token0d

resp1d = c.session.post(
    "https://github.com/settings/education/developer_pack_applications",
    data=step1d_data,
    headers=turbo_headers,
)

if "proof_type" not in resp1d.text:
    print("Step 1d failed")
    sys.exit(1)

soup1d = BeautifulSoup(resp1d.text, "html.parser")
form1d = soup1d.find("form")
token1d = form1d.find("input", attrs={"name": "authenticity_token"})["value"]

# Use files param for multipart encoding
multipart_fields = {
    "authenticity_token": (None, token1d),
    "dev_pack_form[proof_type]": (None, "2. Dated official/unofficial transcript"),
    "dev_pack_form[photo_proof]": (None, "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ=="),
    "dev_pack_form[application_type]": (None, "student"),
    "dev_pack_form[browser_location]": (None, ""),
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

multipart_headers = {
    "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
    "Turbo-Frame": "dev-pack-form",
    "Sec-Fetch-Mode": "same-origin",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Site": "same-origin",
    "Origin": "https://github.com",
    "Referer": "https://github.com/settings/education/developer_pack_applications/new",
}

time.sleep(2)
resp2d = c.session.post(
    "https://github.com/settings/education/developer_pack_applications",
    files=multipart_fields,
    headers=multipart_headers,
)
print(f"Step 2 (multipart): {resp2d.status_code}, {len(resp2d.text)} bytes")

soup2d = BeautifulSoup(resp2d.text, "html.parser")
banner2d = soup2d.find(class_="Banner-title")
if banner2d:
    print(f"Banner: {banner2d.get_text(strip=True)}")

proof2d = soup2d.find("input", attrs={"name": "dev_pack_form[proof_type]"})
if proof2d:
    print(f"proof_type: {proof2d.get('value', '(no attr)')!r}")

with open("multipart_step2.html", "w", encoding="utf-8") as f:
    f.write(resp2d.text)
