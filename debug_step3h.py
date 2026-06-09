"""Debug step 3 - manually construct multipart body without filename."""
import os, json, re, base64, io, random, uuid
os.environ.setdefault("GITHUB_EDU_SCHOOL_NAME", "Yangon Technological University")

from client import GitHubClient
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
import requests as req

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

# Step 3 - manually construct multipart body
s3_html = extract_turbo(resp3.text)
soup3 = BeautifulSoup(s3_html, "html.parser")
token3 = client.extract_token(s3_html)

data3 = {}
if token3: data3["authenticity_token"] = token3
for inp in soup3.find_all("input", {"type": "hidden"}):
    name = inp.get("name")
    if name and name != "authenticity_token":
        data3[name] = inp.get("value", "")
data3["dev_pack_form[far_from_campus_reason]"] = "distant_course_work"
data3["continue"] = "Submit Application"

# Build manual multipart body WITHOUT filename=""
boundary = uuid.uuid4().hex
body_parts = []
for k, v in data3.items():
    body_parts.append(
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="{k}"\r\n'
        f'\r\n'
        f'{v}'
    )
body = '\r\n'.join(body_parts) + f'\r\n--{boundary}--\r\n'

manual_headers = {
    "Content-Type": f"multipart/form-data; boundary={boundary}",
    "Turbo-Frame": "dev-pack-form",
    "Origin": "https://github.com",
    "Referer": f"https://github.com{EDU_URL}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
}

print(f"\n=== Step 3: manual multipart (no filename) ===")
resp4 = client.session.post(
    f"{client.BASE}{EDU_URL}",
    data=body.encode('utf-8'),
    headers=manual_headers,
)
print(f"Status: {resp4.status_code}")
has_error = "banner--error" in resp4.text.lower() or "flash-error" in resp4.text.lower()
has_success = any(w in resp4.text.lower() for w in ("thank", "submitted", "pending", "approved"))
print(f"has_error={has_error}, has_success={has_success}")
if has_error:
    errsoup = BeautifulSoup(resp4.text, "html.parser")
    el = errsoup.find(class_="Banner-title")
    if el: print(f"Error: {el.get_text(strip=True)[:300]}")
if not has_error and not has_success:
    body_text = BeautifulSoup(resp4.text, "html.parser").get_text(strip=True)[:300]
    print(f"Body: {body_text}")
if has_success:
    print("SUCCESS!")
