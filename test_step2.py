"""Clean step1 -> step2 education form submission.
Proof type: 2. Dated official/unofficial transcript
"""
import os, time, re, sys
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {ok}")
time.sleep(2)

# ============ STEP 0: GET the form page ============
print("\n=== Step 0: GET form page ===")
resp0 = c.get("/settings/education/developer_pack_applications/new")
soup0 = BeautifulSoup(resp0.text, "html.parser")
frame = soup0.find("turbo-frame", id="dev-pack-form")
form0 = frame.find("form")
token0 = form0.find("input", attrs={"name": "authenticity_token"})["value"]
print(f"Token: {token0[:40]}...")

# ============ STEP 1: Submit initial form ============
print("\n=== Step 1: Submit initial form ===")
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

resp1 = c.post(
    "/settings/education/developer_pack_applications",
    data=step1_data,
    headers={
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
    }
)
print(f"Step 1 response: {resp1.status_code}, {len(resp1.text)} bytes")
print(f"Content-Type: {resp1.headers.get('Content-Type')}")

# Check for error
if "this field is required" in resp1.text.lower() or "cannot be reviewed" in resp1.text.lower():
    # Check if it's step 2 form (has proof_type) or step 1 error
    has_proof = "proof_type" in resp1.text
    print(f"Has proof_type: {has_proof}")
    if not has_proof:
        print("ERROR: Step 1 failed!")
        # Save for debug
        with open("step1_error.html", "w", encoding="utf-8") as f:
            f.write(resp1.text)
        sys.exit(1)

# Save step 1 response
with open("step1_response.html", "w", encoding="utf-8") as f:
    f.write(resp1.text)

# ============ Parse step 2 form ============
print("\n=== Parsing step 2 form ===")
soup1 = BeautifulSoup(resp1.text, "html.parser")
form1 = soup1.find("form")
if not form1:
    print("ERROR: No form in step 1 response!")
    sys.exit(1)

# Extract new authenticity_token
token1 = form1.find("input", attrs={"name": "authenticity_token"})["value"]
print(f"Step 2 token: {token1[:40]}...")

# Extract ALL hidden inputs from step 2
hidden_inputs = {}
for inp in form1.find_all("input", type="hidden"):
    name = inp.get("name", "")
    value = inp.get("value", "")
    if name:
        # Keep last value for duplicate names
        hidden_inputs[name] = value

print(f"\nHidden inputs ({len(hidden_inputs)}):")
for k, v in hidden_inputs.items():
    print(f"  {k} = {v[:80]!r}")

# Check proof_type input location
proof_input = form1.find("input", attrs={"name": "dev_pack_form[proof_type]"})
if proof_input:
    print(f"\nproof_type input found:")
    print(f"  value attr: {proof_input.get('value', '(NO VALUE ATTR)')!r}")
    print(f"  type: {proof_input.get('type')}")
    # Check parent elements
    parent = proof_input.parent
    parents = []
    while parent and parent.name:
        parents.append(parent.name)
        if parent.name == "form":
            break
        parent = parent.parent
    print(f"  Parent chain: {' > '.join(parents)}")

# Check photo_proof input
photo_input = form1.find("input", attrs={"name": "dev_pack_form[photo_proof]"})
if photo_input:
    print(f"\nphoto_proof input found:")
    print(f"  value attr: {photo_input.get('value', '(NO VALUE ATTR)')!r}")
    print(f"  id: {photo_input.get('id')}")

# ============ STEP 2: Submit with proof ============
print("\n=== Step 2: Submit with proof selection ===")
time.sleep(2)

# Build step 2 data from hidden inputs
step2_data = dict(hidden_inputs)

# Set key values
step2_data["authenticity_token"] = token1
step2_data["dev_pack_form[proof_type]"] = "2. Dated official/unofficial transcript"
step2_data["dev_pack_form[photo_proof]"] = "TEST_PHOTO_DATA"
step2_data["dev_pack_form[form_variant]"] = "upload_proof_form"
step2_data["submit"] = "Submit Application"

# Remove 'continue' if present
step2_data.pop("continue", None)

print(f"\nStep 2 POST data ({len(step2_data)} keys):")
for k, v in step2_data.items():
    display = v[:60] if len(v) > 60 else v
    print(f"  {k} = {display!r}")

# Submit step 2 with Turbo headers
resp2 = c.post(
    "/settings/education/developer_pack_applications",
    data=step2_data,
    headers={
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
    }
)
print(f"\nStep 2 response: {resp2.status_code}, {len(resp2.text)} bytes")
print(f"Content-Type: {resp2.headers.get('Content-Type')}")

# Save response
with open("step2_response.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)

# Check result
if "cannot be reviewed" in resp2.text or "this field is required" in resp2.text:
    print("\n*** STEP 2 FAILED - validation error ***")
    # Extract error message
    soup2 = BeautifulSoup(resp2.text, "html.parser")
    banner = soup2.find("x-banner")
    if banner:
        print(f"Error: {banner.get_text(strip=True)}")
    
    # Check which fields are empty/error
    for field in ["proof_type", "photo_proof", "form_variant"]:
        inp = soup2.find("input", attrs={"name": f"dev_pack_form[{field}]"})
        if inp:
            print(f"  {field}: value={inp.get('value', '(no attr)')!r}")

elif "Thank" in resp2.text or "submitted" in resp2.text.lower() or "review" in resp2.text.lower():
    print("\n*** STEP 2 SUCCESS ***")
else:
    # Show first 500 chars of response
    print(f"\nResponse preview:\n{resp2.text[:500]}")

# Also try step 2 WITHOUT Turbo headers
print("\n\n=== Step 2 RETRY without Turbo headers ===")
time.sleep(2)

# Need fresh form - re-do step 0 and step 1
resp0b = c.get("/settings/education/developer_pack_applications/new")
soup0b = BeautifulSoup(resp0b.text, "html.parser")
frame0b = soup0b.find("turbo-frame", id="dev-pack-form")
form0b = frame0b.find("form")
token0b = form0b.find("input", attrs={"name": "authenticity_token"})["value"]
time.sleep(2)

step1b_data = dict(step1_data)
step1b_data["authenticity_token"] = token0b

resp1b = c.post(
    "/settings/education/developer_pack_applications",
    data=step1b_data,
    headers={
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
    }
)
print(f"Step 1b response: {resp1b.status_code}")

if "proof_type" not in resp1b.text:
    print("Step 1b failed to get step 2 form")
else:
    soup1b = BeautifulSoup(resp1b.text, "html.parser")
    form1b = soup1b.find("form")
    token1b = form1b.find("input", attrs={"name": "authenticity_token"})["value"]
    
    # Build step 2 data
    step2b_data = {}
    for inp in form1b.find_all("input", type="hidden"):
        name = inp.get("name", "")
        value = inp.get("value", "")
        if name:
            step2b_data[name] = value
    
    step2b_data["authenticity_token"] = token1b
    step2b_data["dev_pack_form[proof_type]"] = "2. Dated official/unofficial transcript"
    step2b_data["dev_pack_form[photo_proof]"] = "TEST_PHOTO_DATA"
    step2b_data["dev_pack_form[form_variant]"] = "upload_proof_form"
    step2b_data["submit"] = "Submit Application"
    step2b_data.pop("continue", None)
    
    # Submit WITHOUT turbo headers
    resp2b = c.post(
        "/settings/education/developer_pack_applications",
        data=step2b_data,
    )
    print(f"Step 2b response: {resp2b.status_code}, {len(resp2b.text)} bytes")
    
    with open("step2b_response.html", "w", encoding="utf-8") as f:
        f.write(resp2b.text)
    
    soup2b = BeautifulSoup(resp2b.text, "html.parser")
    banner = soup2b.find("x-banner")
    if banner:
        print(f"Error: {banner.get_text(strip=True)}")
    
    # Check proof_type value in response
    proof_input = soup2b.find("input", attrs={"name": "dev_pack_form[proof_type]"})
    if proof_input:
        print(f"proof_type in response: {proof_input.get('value', '(no attr)')!r}")
    
    photo_input = soup2b.find("input", attrs={"name": "dev_pack_form[photo_proof]"})
    if photo_input:
        print(f"photo_proof in response: {photo_input.get('value', '(no attr)')!r}")
    
    variant_inputs = soup2b.find_all("input", attrs={"name": "dev_pack_form[form_variant]"})
    for vi in variant_inputs:
        print(f"form_variant in response: {vi.get('value')!r}")
