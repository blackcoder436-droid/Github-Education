"""Debug step 3 - print exactly what data3 contains before sending."""
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

# === STEP 3 DEBUG ===
s3_html = extract_turbo(resp3.text)
soup3 = BeautifulSoup(s3_html, "html.parser")
token3 = client.extract_token(s3_html)

data3 = {}
if token3: data3["authenticity_token"] = token3

print(f"\n=== Hidden fields collected ===")
for inp in soup3.find_all("input", {"type": "hidden"}):
    name = inp.get("name")
    if name and name != "authenticity_token":
        val = inp.get("value", "")
        data3[name] = val
        short_val = val[:80] if len(val) < 80 else val[:80] + "..."
        print(f"  {name} = {short_val}")

print(f"\n=== Radio detection ===")
radios = soup3.find_all("input", {"type": "radio"})
print(f"Radios found: {len(radios)}")
chosen = None
for radio in radios:
    val = (radio.get("value") or "").lower()
    rid = radio.get("id", "")
    lbl_el = soup3.find("label", {"for": rid}) if rid else None
    label = lbl_el.get_text(strip=True).lower() if lbl_el else ""
    dist_in_val = "distant" in val or "distance" in val
    dist_in_lbl = "distant" in label or "distance" in label
    print(f"  value={val}, id={rid}")
    print(f"    label='{label}'")
    print(f"    'distant' in val={dist_in_val}, 'distance' in label={dist_in_lbl}")
    if dist_in_val or dist_in_lbl:
        chosen = radio
        break
if not chosen and radios:
    chosen = radios[0]
    print(f"  Fallback to first radio")

if chosen:
    data3[chosen["name"]] = chosen["value"]
    print(f"  CHOSEN: {chosen['name']} = {chosen['value']}")
else:
    print(f"  NO RADIO CHOSEN!")

# Submit button
submit_btn = soup3.find("button", {"type": "submit"})
if submit_btn:
    btn_name = submit_btn.get("name", "submit")
    btn_val = submit_btn.get("value", "Submit Application")
    data3[btn_name] = btn_val
    print(f"\nSubmit button: {btn_name} = {btn_val}")
else:
    data3["submit"] = "Submit Application"
    print(f"\nNo submit button found, using default")

print(f"\n=== Final data3 keys (excluding token) ===")
for k, v in data3.items():
    if k == "authenticity_token": continue
    short_v = v[:80] if len(v) < 80 else v[:80] + "..."
    print(f"  {k} = {short_v}")

# Actually submit
print(f"\n=== Submitting step 3 ===")
resp4 = client.session.post(
    f"{client.BASE}{EDU_URL}",
    files=[(k, (None, v)) for k, v in data3.items()],
    headers=post_headers,
)
print(f"Status: {resp4.status_code}")
print(f"Has error: {'banner--error' in resp4.text.lower() or 'flash-error' in resp4.text.lower()}")

# Parse error
errsoup = BeautifulSoup(resp4.text, "html.parser")
for cls in ("Banner-title", "flash-error"):
    el = errsoup.find(class_=cls)
    if el: print(f"Error: {el.get_text(strip=True)[:300]}")

# Check for success
low = resp4.text.lower()
for w in ("thank", "submitted", "pending", "approved", "review"):
    if w in low: print(f"Found success word: {w}")

print(f"\nResponse body (first 1000 chars):")
body = errsoup.body
if body:
    print(body.get_text(strip=True)[:1000])
else:
    print(resp4.text[:1000])
