"""Debug step 3 — dump hidden fields and radio options from campus form."""
import os, json, re
os.environ.setdefault("GITHUB_EDU_SCHOOL_NAME", "Yangon Technological University")
os.environ.setdefault("GITHUB_EDU_SCHOOL_EMAIL", "thawkhant.1280@gmail.com")
os.environ.setdefault("GITHUB_EDU_LATITUDE", "16.8661")
os.environ.setdefault("GITHUB_EDU_LONGITUDE", "96.1951")

from client import GitHubClient
from steps import ProfileUpdater
from bs4 import BeautifulSoup
import base64, io, random
from PIL import Image, ImageDraw, ImageFont

USERNAME = "thawkhant1280-00"
PASSWORD = "Mka&Omk@2016"
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

client = GitHubClient()
print("Logging in...")
if not client.login(USERNAME, PASSWORD, totp_secret=TOTP_SECRET):
    print("x Login failed!")
    exit(1)
print("Logged in")

EDU_URL = "/settings/education/developer_pack_applications"

# Step 1
resp = client.session.get(
    f"{client.BASE}{EDU_URL}/new",
    headers={**client.HEADERS, "Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
)
token = client.extract_token(resp.text)
print(f"Token: {token[:20]}...")

data1 = {
    "authenticity_token": token,
    "dev_pack_form[application_type]": "student",
    "dev_pack_form[school_name]": "Yangon Technological University",
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

post_headers = {
    "Turbo-Frame": "dev-pack-form",
    "Origin": client.BASE,
    "Referer": f"{client.BASE}{EDU_URL}/new",
}

resp2 = client.session.post(
    f"{client.BASE}{EDU_URL}",
    files=[(k, (None, v)) for k, v in data1.items()],
    headers=post_headers,
)
print(f"Step 1 status: {resp2.status_code}, has proof_type: {'proof_type' in resp2.text}")

# Step 2 - parse and submit
def extract_turbo(html):
    if "<turbo-stream" not in html:
        return html
    m = re.search(r"<template[^>]*>(.*)</template>", html, re.DOTALL)
    return m.group(1) if m else html

s2_html = extract_turbo(resp2.text)
soup2 = BeautifulSoup(s2_html, "html.parser")
token2 = client.extract_token(s2_html)

data2 = {}
if token2:
    data2["authenticity_token"] = token2
for inp in soup2.find_all("input", {"type": "hidden"}):
    name = inp.get("name")
    if name and name != "authenticity_token":
        data2[name] = inp.get("value", "")

# Generate photo
img = Image.new("RGB", (640, 480), color=(37, 99, 235))
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("arial.ttf", 24)
except:
    font = ImageFont.load_default()
draw.text((30, 50), "Student ID - Yangon Technological University", fill="white", font=font)
draw.text((30, 90), "Academic Year 2024-2025", fill="white", font=font)
draw.text((30, 130), "Student Name: Test Student", fill="white", font=font)
buf = io.BytesIO()
img.save(buf, format="JPEG", quality=80)
data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
photo_json = json.dumps({"image": data_url, "metadata": {"filename": None, "type": None, "mimeType": "image/jpeg", "deviceLabel": None}})

data2["dev_pack_form[proof_type]"] = "2. Dated official/unofficial transcript"
data2["dev_pack_form[photo_proof]"] = photo_json
data2["dev_pack_form[form_variant]"] = "upload_proof_form"
data2["continue"] = "Process my application"

post_headers["Referer"] = f"{client.BASE}{EDU_URL}"

resp3 = client.session.post(
    f"{client.BASE}{EDU_URL}",
    files=[(k, (None, v)) for k, v in data2.items()],
    headers=post_headers,
)
print(f"Step 2 status: {resp3.status_code}")
print(f"Has campus: {'far_from_campus' in resp3.text or 'not on campus' in resp3.text}")

# === DEBUG STEP 3 FORM ===
s3_html = extract_turbo(resp3.text)
soup3 = BeautifulSoup(s3_html, "html.parser")

print("\n=== STEP 3 FORM DEBUG ===")

# All forms
forms = soup3.find_all("form")
print(f"Forms found: {len(forms)}")
for i, f in enumerate(forms):
    print(f"  Form {i}: action={f.get('action', '')} method={f.get('method', '')}")

# All inputs (not just hidden)
print("\n--- ALL INPUTS ---")
for inp in soup3.find_all("input"):
    print(f"  type={inp.get('type','')}, name={inp.get('name','')}, value={str(inp.get('value',''))[:80]}, id={inp.get('id','')}")

# Radio buttons
print("\n--- RADIO BUTTONS ---")
radios = soup3.find_all("input", {"type": "radio"})
print(f"Radio count: {len(radios)}")
for r in radios:
    lbl = soup3.find("label", {"for": r.get("id", "")}) if r.get("id") else None
    print(f"  name={r.get('name')}, value={r.get('value')}, id={r.get('id')}, label={lbl.get_text(strip=True) if lbl else 'N/A'}")

# Textareas
print("\n--- TEXTAREAS ---")
for ta in soup3.find_all("textarea"):
    print(f"  name={ta.get('name')}, id={ta.get('id')}")

# Select elements
print("\n--- SELECTS ---")
for sel in soup3.find_all("select"):
    print(f"  name={sel.get('name')}, id={sel.get('id')}")
    for opt in sel.find_all("option"):
        print(f"    value={opt.get('value','')}, text={opt.get_text(strip=True)[:60]}")

# Buttons
print("\n--- BUTTONS ---")
for btn in soup3.find_all("button"):
    print(f"  type={btn.get('type','')}, name={btn.get('name','')}, value={btn.get('value','')}, text={btn.get_text(strip=True)[:60]}")

# Raw HTML snippet
print(f"\n--- RAW HTML (first 3000 chars) ---")
print(s3_html[:3000])
