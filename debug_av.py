#!/usr/bin/env python3
"""Debug avatar upload — full 3-step policy flow with crop dialog."""
import os
import re
import requests
from dotenv import load_dotenv
load_dotenv()

from client import GitHubClient
from bs4 import BeautifulSoup

client = GitHubClient()
username = os.environ.get("GITHUB_USERNAME", "")
password = os.environ.get("GITHUB_PASSWORD", "")

print(f"Logging in as {username}...")
if not client.login(username, password):
    exit(1)
print("Logged in\n")

# ── Step 0 : Get profile page to extract upload params ──
resp = client.get("/settings/profile")
html = resp.text
soup = BeautifulSoup(html, "html.parser")

fa = soup.find("file-attachment", class_="js-upload-avatar-image")
if not fa:
    print("x file-attachment not found"); exit(1)

owner_id = fa.get("data-alambic-owner-id")
owner_type = fa.get("data-alambic-owner-type")
policy_url = fa.get("data-upload-policy-url")
csrf_input = fa.find("input", class_="js-data-upload-policy-url-csrf")
policy_csrf = csrf_input["value"] if csrf_input else None

print(f"owner_id={owner_id} owner_type={owner_type}")
print(f"policy_url={policy_url}")
print(f"policy_csrf={policy_csrf[:20]}...")

# ── Step 0.5 : Download test avatar image ──
print("\nDownloading test avatar...")
img_resp = requests.get(
    "https://ui-avatars.com/api/?name=AB&size=256&background=0D8ABC&color=fff&bold=true&format=png",
    timeout=15
)
img_data = img_resp.content
img_name = "avatar_test.png"
print(f"  Image: {len(img_data)} bytes")

# ── Step 1 : Get upload policy ──
print("\n=== Step 1: Policy ===")
policy_full_url = f"{policy_url}?owner_id={owner_id}&owner_type={owner_type}"
policy_data = {
    "name": img_name,
    "size": str(len(img_data)),
    "content_type": "image/png",
    "authenticity_token": policy_csrf,
    "owner_type": owner_type,
    "owner_id": owner_id,
}

policy_resp = client.session.post(
    f"{client.BASE}{policy_full_url}",
    data=policy_data,
    headers={
        "Accept": "application/json",
        "GitHub-Verified-Fetch": "true",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Origin": client.BASE,
        "Referer": f"{client.BASE}/settings/profile",
    },
)
print(f"  Status: {policy_resp.status_code}")
if policy_resp.status_code != 201:
    print(f"  Body: {policy_resp.text[:500]}")
    exit(1)

policy = policy_resp.json()
print(f"  Policy keys: {list(policy.keys())}")
print(f"  upload_url: {policy['upload_url']}")
print(f"  asset: {policy.get('asset', {})}")
print(f"  same_origin: {policy.get('same_origin')}")
print(f"  form keys: {list(policy.get('form', {}).keys())}")
print(f"  header: {policy.get('header', {})}")

# ── Step 2 : Upload to storage ──
print("\n=== Step 2: Storage Upload ===")
upload_url = policy["upload_url"]
form_fields = policy.get("form", {})
upload_token = policy.get("upload_authenticity_token", "")

# Build multipart
files_data = {}
for k, v in form_fields.items():
    files_data[k] = (None, v)

if policy.get("same_origin") and upload_token:
    files_data["authenticity_token"] = (None, upload_token)

files_data["file"] = (img_name, img_data, "image/png")

# Build headers from policy
upload_headers = {}
for k, v in (policy.get("header", {}) or {}).items():
    upload_headers[k] = v
upload_headers["Accept"] = "application/json"
upload_headers["GitHub-Verified-Fetch"] = "true"

storage_resp = client.session.post(
    upload_url,
    files=files_data,
    headers=upload_headers,
)
print(f"  Status: {storage_resp.status_code}")
if storage_resp.status_code != 201:
    print(f"  Body: {storage_resp.text[:500]}")
    exit(1)

asset_info = storage_resp.json()
asset_id = asset_info.get("id") or policy["asset"]["id"]
print(f"  asset id: {asset_id}")
print(f"  dimensions: {asset_info.get('width')}x{asset_info.get('height')}")

# ── Step 3 : Fetch crop dialog ──
print(f"\n=== Step 3: Fetch Crop Dialog (/settings/avatars/{asset_id}) ===")
crop_resp = client.session.get(
    f"{client.BASE}/settings/avatars/{asset_id}",
    headers={
        "Accept": "text/html",
        "GitHub-Verified-Fetch": "true",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Referer": f"{client.BASE}/settings/profile",
        "X-Requested-With": "XMLHttpRequest",
    },
)
print(f"  Status: {crop_resp.status_code}")
print(f"  Content-Type: {crop_resp.headers.get('Content-Type', '?')}")
print(f"  Body length: {len(crop_resp.text)}")

if crop_resp.status_code != 200:
    print(f"  Body: {crop_resp.text[:1000]}")
    exit(1)

# Save and parse the crop dialog HTML
crop_html = crop_resp.text
with open("crop_dialog.html", "w", encoding="utf-8") as f:
    f.write(crop_html)
print("  Saved to crop_dialog.html")

crop_soup = BeautifulSoup(crop_html, "html.parser")

# Find the crop form
crop_form = crop_soup.find("form", id="avatar-crop-form") or crop_soup.find("form")
if crop_form:
    print(f"\n  Form found: action='{crop_form.get('action', '?')}' method='{crop_form.get('method', '?')}'")
    print(f"  data-alambic-avatar-id='{crop_form.get('data-alambic-avatar-id', '?')}'")

    # Extract all fields
    all_fields = {}
    for inp in crop_form.find_all("input"):
        name = inp.get("name")
        if name:
            all_fields[name] = inp.get("value", "")[:80]
    print(f"\n  Form fields:")
    for k, v in all_fields.items():
        print(f"    {k} = {v}")
else:
    print("  x No form found in crop dialog")
    for form in crop_soup.find_all("form"):
        print(f"  Form: action={form.get('action')} id={form.get('id')}")

# Show buttons
print("\n  Buttons/submits in crop dialog:")
for btn in crop_soup.find_all(["button", "input"]):
    if btn.get("type") in ("submit", "button") or btn.name == "button":
        print(f"    <{btn.name}> type={btn.get('type')} value='{btn.get('value', '')}' text='{btn.get_text(strip=True)[:60]}'")

# ── Step 4 : Submit the crop form ──
if crop_form:
    print(f"\n=== Step 4: Submit Crop Form ===")
    action = crop_form.get("action", "")
    method = crop_form.get("method", "post").upper()

    # Get all hidden fields
    form_data = {}
    for inp in crop_form.find_all("input"):
        name = inp.get("name")
        if name and inp.get("type") != "file":
            form_data[name] = inp.get("value", "")

    # Set crop coordinates (full image, no real cropping needed)
    form_data.setdefault("cropped_x", "0")
    form_data.setdefault("cropped_y", "0")
    form_data.setdefault("cropped_width", "256")
    form_data.setdefault("cropped_height", "256")

    print(f"  POST {action}")
    print(f"  Fields: {form_data}")

    # Check for Scoped-CSRF-Token
    scoped_csrf = None
    csrf_el = crop_soup.find(class_="js-avatar-post-csrf")
    if csrf_el:
        scoped_csrf = csrf_el.get("value")
        print(f"  Scoped-CSRF-Token: {scoped_csrf[:20]}...")

    save_headers = {
        "Origin": client.BASE,
        "Referer": f"{client.BASE}/settings/profile",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "GitHub-Verified-Fetch": "true",
        "Accept": "*/*",
    }
    if scoped_csrf:
        save_headers["Scoped-CSRF-Token"] = scoped_csrf

    save_resp = client.session.post(
        f"{client.BASE}{action}" if not action.startswith("http") else action,
        data=form_data,
        headers=save_headers,
    )
    print(f"  Status: {save_resp.status_code}")
    print(f"  Body: {save_resp.text[:500]}")

    # Verify by checking avatar hash
    print("\n=== Verification ===")
    verify_resp = client.get("/settings/profile")
    verify_soup = BeautifulSoup(verify_resp.text, "html.parser")
    for img in verify_soup.find_all("img"):
        src = img.get("src", "")
        if "avatar" in src.lower():
            print(f"  Avatar img: {src[:120]}")
            break
