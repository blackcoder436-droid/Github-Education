"""Test step 2 without step 1 to check session state, and try alternative approaches."""
import os, re, json, time, base64
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
import requests as req
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {'OK' if ok else 'FAIL'}")

time.sleep(2)

# Get CSRF token from the education page
resp0 = c.get("/settings/education/benefits")
soup0 = BeautifulSoup(resp0.text, "html.parser")
meta_csrf = soup0.find("meta", {"name": "csrf-token"})
csrf_token = ""
if meta_csrf:
    csrf_token = meta_csrf.get("content", "")
    print(f"CSRF from meta: {csrf_token[:20]}...")
else:
    # Extract from a form on the page
    form0 = soup0.find("form")
    if form0:
        tok = form0.find("input", {"name": "authenticity_token"})
        if tok:
            csrf_token = tok.get("value", "")
            print(f"CSRF from form: {csrf_token[:20]}...")
    if not csrf_token:
        print("No CSRF token found!")
        exit(1)

# Test 1: Submit step 2 directly without step 1
print("\n=== Test 1: Step 2 without step 1 ===")
time.sleep(2)
resp1 = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data={
        "authenticity_token": csrf_token,
        "dev_pack_form[proof_type]": "1. Dated school ID",
        "dev_pack_form[photo_proof]": "test_data",
        "dev_pack_form[application_type]": "student",
        "dev_pack_form[browser_location]": "Yangon, Myanmar",
        "dev_pack_form[form_variant]": "upload_proof_form",
        "dev_pack_form[latitude]": "16.8661",
        "dev_pack_form[location_shared]": "true",
        "dev_pack_form[longitude]": "96.1951",
        "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
        "dev_pack_form[school_name]": "SKT International College",
        "submit": "Submit Application",
    },
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/benefits",
    },
)
print(f"Status: {resp1.status_code}")
soup1 = BeautifulSoup(resp1.text, "html.parser")
for err in soup1.find_all(class_=re.compile(r"Banner")):
    text = err.get_text(strip=True)[:200]
    if text:
        print(f"  Banner: {text}")
# Check if form returned
form1 = soup1.find("form")
if form1:
    for inp in form1.find_all("input", {"name": re.compile(r"proof_type|photo_proof")}):
        val = inp.get("value")
        has = "value" in inp.attrs
        print(f"  {inp.get('name')}: value='{val}' has_attr={has}")

# Test 2: Try PUT method (maybe step 2 is an update)
print("\n=== Test 2: PUT method ===")
time.sleep(2)
# First do step 1
resp_s1 = c.get("/settings/education/developer_pack_applications/new")
soup_s1 = BeautifulSoup(resp_s1.text, "html.parser")
form_s1 = soup_s1.find("form", {"action": "/settings/education/developer_pack_applications"})
token_s1 = form_s1.find("input", {"name": "authenticity_token"}).get("value")
time.sleep(2)
resp_s1b = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data={
        "authenticity_token": token_s1,
        "dev_pack_form[application_type]": "student",
        "dev_pack_form[school_name]": "SKT International College",
        "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
        "dev_pack_form[latitude]": "16.8661",
        "dev_pack_form[longitude]": "96.1951",
        "dev_pack_form[location_shared]": "true",
        "dev_pack_form[form_variant]": "initial_form",
        "dev_pack_form[browser_location]": "Yangon, Myanmar",
        "continue": "Continue",
    },
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new",
    },
)
print(f"Step 1: {resp_s1b.status_code}")
soup_s1b = BeautifulSoup(resp_s1b.text, "html.parser")
form_s1b = soup_s1b.find("form")
token_s1b = form_s1b.find("input", {"name": "authenticity_token"}).get("value") if form_s1b else ""

# Check if there's an application ID in the response or URL
# Maybe the form action changes to include an ID
if form_s1b:
    action = form_s1b.get("action", "")
    print(f"Step 2 form action: {action}")
    method = form_s1b.get("method", "")
    print(f"Step 2 form method: {method}")
    # Check for _method input
    method_inp = form_s1b.find("input", {"name": "_method"})
    if method_inp:
        print(f"_method: {method_inp.get('value')}")

# Test 3: Check if there's a numbered endpoint (like /1/edit)
print("\n=== Test 3: Check for redirect after step 1 ===")
time.sleep(2)
# Re-do step 1 without turbo (regular redirect)
resp_s1c = c.get("/settings/education/developer_pack_applications/new")
soup_s1c = BeautifulSoup(resp_s1c.text, "html.parser")
form_s1c = soup_s1c.find("form", {"action": "/settings/education/developer_pack_applications"})
token_s1c = form_s1c.find("input", {"name": "authenticity_token"}).get("value")
time.sleep(2)
resp_s1d = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data={
        "authenticity_token": token_s1c,
        "dev_pack_form[application_type]": "student",
        "dev_pack_form[school_name]": "SKT International College",
        "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
        "dev_pack_form[latitude]": "16.8661",
        "dev_pack_form[longitude]": "96.1951",
        "dev_pack_form[location_shared]": "true",
        "dev_pack_form[form_variant]": "initial_form",
        "dev_pack_form[browser_location]": "Yangon, Myanmar",
        "continue": "Continue",
    },
    headers={**c.HEADERS, "Origin": c.BASE, "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new"},
    allow_redirects=False,
)
print(f"Step 1 (no redirect): {resp_s1d.status_code}")
print(f"Location: {resp_s1d.headers.get('Location', 'none')}")
if resp_s1d.status_code == 200:
    # Check URL and response
    soup_s1d = BeautifulSoup(resp_s1d.text, "html.parser")
    form_s1d = soup_s1d.find("form", action=re.compile(r"developer_pack"))
    if form_s1d:
        print(f"Form action: {form_s1d.get('action')}")
        # Look for any ID in the form
        for inp in form_s1d.find_all("input", type="hidden"):
            name = inp.get("name", "")
            val = inp.get("value", "")
            if "id" in name.lower() or val.isdigit():
                print(f"  ID field? {name} = {val}")

# Test 4: Try sending proof_type/photo_proof as top-level params (not nested)
print("\n=== Test 4: Top-level params ===")
time.sleep(2)
# Re-do step 1
resp_t4a = c.get("/settings/education/developer_pack_applications/new")
soup_t4a = BeautifulSoup(resp_t4a.text, "html.parser")
form_t4a = soup_t4a.find("form", {"action": "/settings/education/developer_pack_applications"})
token_t4a = form_t4a.find("input", {"name": "authenticity_token"}).get("value")
time.sleep(2)
resp_t4b = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data={
        "authenticity_token": token_t4a,
        "dev_pack_form[application_type]": "student",
        "dev_pack_form[school_name]": "SKT International College",
        "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
        "dev_pack_form[latitude]": "16.8661",
        "dev_pack_form[longitude]": "96.1951",
        "dev_pack_form[location_shared]": "true",
        "dev_pack_form[form_variant]": "initial_form",
        "dev_pack_form[browser_location]": "Yangon, Myanmar",
        "continue": "Continue",
    },
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new",
    },
)
soup_t4b = BeautifulSoup(resp_t4b.text, "html.parser")
form_t4b = soup_t4b.find("form")
token_t4b = form_t4b.find("input", {"name": "authenticity_token"}).get("value") if form_t4b else ""

# Try with proof_type and photo_proof as separate top-level params
time.sleep(3)
resp_t4c = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data={
        "authenticity_token": token_t4b,
        "proof_type": "1. Dated school ID",
        "photo_proof": "test_value",
        "dev_pack_form[proof_type]": "1. Dated school ID",
        "dev_pack_form[photo_proof]": "test_value",
        "dev_pack_form[application_type]": "student",
        "dev_pack_form[browser_location]": "Yangon, Myanmar",
        "dev_pack_form[form_variant]": "upload_proof_form",
        "dev_pack_form[latitude]": "16.8661",
        "dev_pack_form[location_shared]": "true",
        "dev_pack_form[longitude]": "96.1951",
        "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
        "dev_pack_form[school_name]": "SKT International College",
        "submit": "Submit Application",
    },
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/benefits",
    },
)
print(f"Status: {resp_t4c.status_code}")
soup_t4c = BeautifulSoup(resp_t4c.text, "html.parser")
for err in soup_t4c.find_all(class_=re.compile(r"Banner")):
    text = err.get_text(strip=True)[:200]
    if text:
        print(f"  Banner: {text}")

# Check returned form values
form_t4c = soup_t4c.find("form")
if form_t4c:
    for inp in form_t4c.find_all("input", {"name": re.compile(r"proof_type|photo_proof")}):
        val = inp.get("value")
        has = "value" in inp.attrs
        print(f"  {inp.get('name')}: value='{val}' has_attr={has}")
