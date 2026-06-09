"""Debug step 3 - try sending duplicate form_variant as tuples."""
import os, json, re, base64, io, random
os.environ.setdefault("GITHUB_EDU_SCHOOL_NAME", "Yangon Technological University")
os.environ.setdefault("GITHUB_EDU_SCHOOL_EMAIL", "thawkhant.1280@gmail.com")
os.environ.setdefault("GITHUB_EDU_LATITUDE", "16.8661")
os.environ.setdefault("GITHUB_EDU_LONGITUDE", "96.1951")

from client import GitHubClient
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

USERNAME = "thawkhant1280-00"
PASSWORD = "Mka&Omk@2016"
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

client = GitHubClient()
print("Logging in...")
if not client.login(USERNAME, PASSWORD, totp_secret=TOTP_SECRET):
    print("x Login failed!"); exit(1)
print("Logged in")

EDU_URL = "/settings/education/developer_pack_applications"

def extract_turbo(html):
    if "<turbo-stream" not in html:
        return html
    m = re.search(r"<template[^>]*>(.*)</template>", html, re.DOTALL)
    return m.group(1) if m else html

# Step 1
resp = client.session.get(
    f"{client.BASE}{EDU_URL}/new",
    headers={**client.HEADERS, "Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
)
token = client.extract_token(resp.text)

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
post_headers = {"Turbo-Frame": "dev-pack-form", "Origin": client.BASE, "Referer": f"{client.BASE}{EDU_URL}/new"}

resp2 = client.session.post(f"{client.BASE}{EDU_URL}", files=[(k, (None, v)) for k, v in data1.items()], headers=post_headers)
print(f"Step 1: {resp2.status_code}, proof_type={'proof_type' in resp2.text}")

# Step 2
s2_html = extract_turbo(resp2.text)
soup2 = BeautifulSoup(s2_html, "html.parser")
token2 = client.extract_token(s2_html)

data2 = {}
if token2: data2["authenticity_token"] = token2
for inp in soup2.find_all("input", {"type": "hidden"}):
    name = inp.get("name")
    if name and name != "authenticity_token":
        data2[name] = inp.get("value", "")

img = Image.new("RGB", (640, 480), color=(37, 99, 235))
draw = ImageDraw.Draw(img)
try: font = ImageFont.truetype("arial.ttf", 24)
except: font = ImageFont.load_default()
draw.text((30, 50), "Student ID", fill="white", font=font)
buf = io.BytesIO()
img.save(buf, format="JPEG", quality=80)
data_url = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
photo_json = json.dumps({"image": data_url, "metadata": {"filename": None, "type": None, "mimeType": "image/jpeg", "deviceLabel": None}})

data2["dev_pack_form[proof_type]"] = "2. Dated official/unofficial transcript"
data2["dev_pack_form[photo_proof]"] = photo_json
data2["dev_pack_form[form_variant]"] = "upload_proof_form"
data2["continue"] = "Process my application"
post_headers["Referer"] = f"{client.BASE}{EDU_URL}"

resp3 = client.session.post(f"{client.BASE}{EDU_URL}", files=[(k, (None, v)) for k, v in data2.items()], headers=post_headers)
print(f"Step 2: {resp3.status_code}, campus={'far_from_campus' in resp3.text}")

# === Step 3: Build as LIST OF TUPLES to preserve duplicate form_variant ===
s3_html = extract_turbo(resp3.text)
soup3 = BeautifulSoup(s3_html, "html.parser")
token3 = client.extract_token(s3_html)

# Build as tuple list, preserving ALL hidden fields including duplicates
data3_tuples = []
if token3:
    data3_tuples.append(("authenticity_token", token3))
for inp in soup3.find_all("input", {"type": "hidden"}):
    name = inp.get("name")
    if name and name != "authenticity_token":
        data3_tuples.append((name, inp.get("value", "")))

# Add radio
data3_tuples.append(("dev_pack_form[far_from_campus_reason]", "distant_course_work"))
# Add submit button
data3_tuples.append(("submit", "Submit Application"))

print(f"\n=== Step 3 tuples ({len(data3_tuples)} entries) ===")
for k, v in data3_tuples:
    short_v = v[:60] if len(v) < 60 else v[:60] + "..."
    print(f"  {k} = {short_v}")

# Test A: files= with tuples (multipart)
print(f"\n=== Test A: files= with tuples ===")
resp4a = client.session.post(
    f"{client.BASE}{EDU_URL}",
    files=[(k, (None, v)) for k, v in data3_tuples],
    headers=post_headers,
)
print(f"Status: {resp4a.status_code}")
has_error = "banner--error" in resp4a.text.lower() or "flash-error" in resp4a.text.lower()
has_success = any(w in resp4a.text.lower() for w in ("thank", "submitted", "pending", "approved"))
print(f"has_error={has_error}, has_success={has_success}")
if has_error:
    errsoup = BeautifulSoup(resp4a.text, "html.parser")
    el = errsoup.find(class_="Banner-title")
    if el: print(f"Error: {el.get_text(strip=True)[:200]}")

# If that didn't work, also try data= with tuples (URL-encoded)
if has_error:
    print(f"\n=== Test B: data= with tuples ===")
    # Need fresh form for step 3 since we used the token
    # Actually we can't re-use the same step - let me just report
    print("  (skipping - would need fresh token)")
