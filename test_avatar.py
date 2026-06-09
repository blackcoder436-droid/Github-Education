"""Force test avatar upload (ignoring skip check)"""
from client import GitHubClient
from bs4 import BeautifulSoup
from data import generate_profile
import requests, random, os
from dotenv import load_dotenv
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in")

p = generate_profile()
print(f"Name: {p['full_name']}")

# Download avatar
initials = "".join(w[0] for w in p["full_name"].split()[:2])
colors = ["0D8ABC", "2E86C1", "1ABC9C", "27AE60", "8E44AD", "E74C3C", "F39C12"]
bg = random.choice(colors)
avatar_url = f"https://ui-avatars.com/api/?name={initials}&size=256&background={bg}&color=fff&bold=true&format=png"
print(f"Downloading: {avatar_url}")
img_resp = requests.get(avatar_url, timeout=15)
print(f"Download: {img_resp.status_code}, {len(img_resp.content)} bytes")

img_data = img_resp.content
img_name = "avatar.png"

# Get profile page
resp = c.get("/settings/profile")
soup = BeautifulSoup(resp.text, "html.parser")

fa = soup.find("file-attachment", class_="js-upload-avatar-image")
if not fa:
    print("x file-attachment not found")
    exit(1)

owner_id = fa.get("data-alambic-owner-id")
owner_type = fa.get("data-alambic-owner-type")
policy_url = fa.get("data-upload-policy-url")
csrf_input = fa.find("input", class_="js-data-upload-policy-url-csrf")
policy_csrf = csrf_input["value"] if csrf_input else None
print(f"owner_id={owner_id}, policy_url={policy_url}, csrf={'yes' if policy_csrf else 'no'}")

# Step 1: Policy
print("\n1. Getting policy...")
policy_resp = c.session.post(
    f"{c.BASE}{policy_url}?owner_id={owner_id}&owner_type={owner_type}",
    data={
        "name": img_name,
        "size": str(len(img_data)),
        "content_type": "image/png",
        "authenticity_token": policy_csrf,
        "owner_type": owner_type,
        "owner_id": owner_id,
    },
    headers={
        "Accept": "application/json",
        "GitHub-Verified-Fetch": "true",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/profile",
    },
)
print(f"Policy: {policy_resp.status_code}")
if policy_resp.status_code != 201:
    print(policy_resp.text[:500])
    exit(1)
policy = policy_resp.json()

# Step 2: Storage upload
print("\n2. Uploading to storage...")
files_data = {}
for k, v in policy.get("form", {}).items():
    files_data[k] = (None, v)
if policy.get("same_origin") and policy.get("upload_authenticity_token"):
    files_data["authenticity_token"] = (None, policy["upload_authenticity_token"])
files_data["file"] = (img_name, img_data, "image/png")

upload_headers = dict(policy.get("header", {}) or {})
upload_headers["Accept"] = "application/json"
upload_headers["GitHub-Verified-Fetch"] = "true"

storage_resp = c.session.post(policy["upload_url"], files=files_data, headers=upload_headers)
print(f"Storage: {storage_resp.status_code}")
if storage_resp.status_code != 201:
    print(storage_resp.text[:500])
    exit(1)
asset_id = storage_resp.json().get("id")
print(f"Asset ID: {asset_id}")

# Step 3: Crop dialog
print("\n3. Fetching crop dialog...")
crop_resp = c.session.get(
    f"{c.BASE}/settings/avatars/{asset_id}",
    headers={
        "Accept": "text/html",
        "GitHub-Verified-Fetch": "true",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Referer": f"{c.BASE}/settings/profile",
    },
)
print(f"Crop dialog: {crop_resp.status_code}")
if crop_resp.status_code != 200:
    print(crop_resp.text[:500])
    exit(1)

crop_soup = BeautifulSoup(crop_resp.text, "html.parser")
crop_form = crop_soup.find("form", id="avatar-crop-form") or crop_soup.find("form")
if not crop_form:
    print("x Crop form not found")
    exit(1)

form_data = {}
for inp in crop_form.find_all("input"):
    name = inp.get("name")
    if name and inp.get("type") != "file":
        form_data[name] = inp.get("value", "")
action = crop_form.get("action", f"/settings/avatars/{asset_id}")

scoped_csrf = None
csrf_el = crop_soup.find(class_="js-avatar-post-csrf")
if csrf_el:
    scoped_csrf = csrf_el.get("value")
print(f"Form fields: {list(form_data.keys())}")
print(f"Scoped CSRF: {'yes' if scoped_csrf else 'no'}")

# Step 4: Submit crop
print("\n4. Submitting crop form...")
save_headers = {
    "Origin": c.BASE,
    "Referer": f"{c.BASE}/settings/profile",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "GitHub-Verified-Fetch": "true",
    "Accept": "*/*",
}
if scoped_csrf:
    save_headers["Scoped-CSRF-Token"] = scoped_csrf

save_resp = c.session.post(
    f"{c.BASE}{action}" if not action.startswith("http") else action,
    data=form_data,
    headers=save_headers,
)
print(f"Save: {save_resp.status_code}")
if save_resp.status_code < 400:
    print("Avatar Updated!")
else:
    print(f"Failed: {save_resp.text[:500]}")
