"""Debug step 3 - use Playwright page.evaluate for step 3 only."""
import os, json, re, base64, io, random
os.environ.setdefault("GITHUB_EDU_SCHOOL_NAME", "Yangon Technological University")
os.environ.setdefault("GITHUB_EDU_SCHOOL_EMAIL", "thawkhant.1280@gmail.com")

from client import GitHubClient
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
import pyotp

USERNAME = "thawkhant1280-00"
PASSWORD = "Mka&Omk@2016"
TOTP_SECRET = "SFDHLAA7MDH2S7TN"

client = GitHubClient()
print("Logging in (requests)...")
if not client.login(USERNAME, PASSWORD, totp_secret=TOTP_SECRET):
    print("x Login failed!"); exit(1)
print("Logged in")

EDU_URL = "/settings/education/developer_pack_applications"

def extract_turbo(html):
    if "<turbo-stream" not in html:
        return html
    m = re.search(r"<template[^>]*>(.*)</template>", html, re.DOTALL)
    return m.group(1) if m else html

# Step 1 (requests)
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

# Step 2 (requests)
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

# Step 3 - use Playwright with cookies from requests session
s3_html = extract_turbo(resp3.text)
soup3 = BeautifulSoup(s3_html, "html.parser")
token3 = client.extract_token(s3_html)

# Collect step 3 hidden fields
hidden_fields = {}
if token3: hidden_fields["authenticity_token"] = token3
for inp in soup3.find_all("input", {"type": "hidden"}):
    name = inp.get("name")
    if name and name != "authenticity_token":
        hidden_fields[name] = inp.get("value", "")

print(f"\n=== Step 3: Using Playwright fetch ===")

# Transfer cookies to Playwright
cookies_for_pw = []
for cookie in client.session.cookies:
    cookies_for_pw.append({
        "name": cookie.name,
        "value": cookie.value,
        "domain": cookie.domain or ".github.com",
        "path": cookie.path or "/",
    })

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    )
    context.add_cookies(cookies_for_pw)
    page = context.new_page()
    page.goto("https://github.com/settings/profile", timeout=30000, wait_until="load")
    page.wait_for_timeout(2000)
    print(f"Page URL: {page.url}")

    # Use page.evaluate to do fetch with FormData
    result = page.evaluate('''async (hiddenFields) => {
        const fd = new FormData();
        for (const [k, v] of Object.entries(hiddenFields)) {
            fd.set(k, v);
        }
        fd.set('dev_pack_form[far_from_campus_reason]', 'distant_course_work');
        fd.set('continue', 'Submit Application');

        // Log what we're sending
        const sent = {};
        for (const [k, v] of fd.entries()) {
            if (k !== 'authenticity_token' && k !== 'dev_pack_form[photo_proof]')
                sent[k] = typeof v === 'string' ? v.substring(0, 80) : v.name;
        }

        const resp = await fetch("/settings/education/developer_pack_applications", {
            method: "POST",
            headers: {"Turbo-Frame": "dev-pack-form"},
            credentials: "same-origin",
            body: fd,
        });
        const text = await resp.text();
        const hasError = text.includes('Banner--error') || text.includes('flash-error');
        const hasSuccess = text.toLowerCase().includes('thank') ||
                          text.toLowerCase().includes('submitted') ||
                          text.toLowerCase().includes('pending');
        const doc = new DOMParser().parseFromString(text, 'text/html');
        const errEl = doc.querySelector('.Banner-title');

        return {
            status: resp.status,
            hasError,
            hasSuccess,
            error: errEl ? errEl.textContent.trim().substring(0, 200) : null,
            sent,
            bodyText: doc.body?.textContent?.trim()?.substring(0, 500) || '',
        };
    }''', hidden_fields)

    print(f"Status: {result['status']}")
    print(f"hasError: {result['hasError']}, hasSuccess: {result['hasSuccess']}")
    if result.get('error'):
        print(f"Error: {result['error']}")
    print(f"Sent: {json.dumps(result.get('sent', {}), indent=2)}")
    print(f"Body: {result.get('bodyText', '')[:300]}")

    browser.close()
print("\nDone!")
