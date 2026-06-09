"""Re-analyze step 2 form HTML with detailed element inspection."""
import os, time, re
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup 
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {ok}")
time.sleep(2)

# Step 1: GET the education form page
resp = c.get("/settings/education/developer_pack_applications/new")
soup = BeautifulSoup(resp.text, "html.parser")
time.sleep(1)

# Extract turbo-frame form
frame = soup.find("turbo-frame", id="dev-pack-form")
if not frame:
    print("No turbo-frame found!")
    exit(1)

form = frame.find("form")
print(f"Form action: {form.get('action')}")
print(f"Form method: {form.get('method')}")

# Get all form inputs
inputs = form.find_all(["input", "select", "textarea", "button"])
print(f"\nForm elements ({len(inputs)}):")
for inp in inputs:
    tag = inp.name
    name = inp.get("name", "")
    type_ = inp.get("type", "")
    value = inp.get("value", "")[:80]
    print(f"  <{tag}> name={name!r} type={type_!r} value={value!r}")

# Now submit step 1
token = form.find("input", attrs={"name": "authenticity_token"}).get("value")
data = {}
for inp in form.find_all("input"):
    name = inp.get("name")
    val = inp.get("value", "")
    if name:
        data[name] = val

# Add school and step 1 specifics
data["dev_pack_form[school_name]"] = "SKT International College"
data["dev_pack_form[school_id]"] = "118171"
data["dev_pack_form[application_type]"] = "student"
data["dev_pack_form[form_variant]"] = "initial_form"
data["continue"] = "Continue"

print(f"\n=== Submitting step 1 ===")
time.sleep(2)
resp2 = c.post(
    "/settings/education/developer_pack_applications",
    data=data,
    headers={
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml"
    }
)
print(f"Step 1 response: {resp2.status_code}, {len(resp2.text)} bytes")

# Save full response
with open("step2_form_full.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)

# Parse step 2 form
soup2 = BeautifulSoup(resp2.text, "html.parser")

# Get ALL forms in response
forms = soup2.find_all("form")
print(f"\nForms in response: {len(forms)}")
for i, form in enumerate(forms):
    print(f"\n--- Form {i} ---")
    print(f"  action: {form.get('action')}")
    print(f"  method: {form.get('method')}")
    print(f"  class: {form.get('class')}")
    print(f"  id: {form.get('id')}")
    print(f"  data-turbo-frame: {form.get('data-turbo-frame')}")
    
    # All inputs including deeply nested
    all_inputs = form.find_all(["input", "select", "textarea", "button"])
    print(f"  Elements ({len(all_inputs)}):")
    for inp in all_inputs:
        tag = inp.name
        name = inp.get("name", "")
        type_ = inp.get("type", "")
        value = inp.get("value", "")[:100]
        id_ = inp.get("id", "")
        disabled = inp.get("disabled")
        readonly = inp.get("readonly")
        extra = ""
        if disabled: extra += " DISABLED"
        if readonly: extra += " READONLY"
        print(f"    <{tag}> name={name!r} type={type_!r} value={value!r} id={id_!r}{extra}")

# Also look for action-menu elements
action_menus = soup2.find_all("action-menu")
print(f"\nAction menus: {len(action_menus)}")
for am in action_menus:
    print(f"  Action menu: {am.get('class')}")
    # Look for inner inputs
    inner_inputs = am.find_all("input")
    for inp in inner_inputs:
        print(f"    Input: name={inp.get('name')!r} type={inp.get('type')!r} value={inp.get('value', '')!r}")
    # Look for button/items
    buttons = am.find_all("button")
    for btn in buttons:
        print(f"    Button: value={btn.get('value', '')!r} type={btn.get('type')!r} role={btn.get('role')!r}")
        # inner text
        text = btn.get_text(strip=True)[:80]
        print(f"             text: {text}")

# Look for react-partial elements
react_partials = soup2.find_all("react-partial")
print(f"\nReact partials: {len(react_partials)}")
for rp in react_partials:
    pname = rp.get("partial-name", "")
    print(f"  Partial: {pname}")
    # Find data script
    script = rp.find("script", type="application/json")
    if script:
        print(f"    Props: {script.string[:200] if script.string else 'empty'}")

# Look specifically for photo_proof
photo_proof = soup2.find(id="photo_proof")
if photo_proof:
    print(f"\n#photo_proof element:")
    print(f"  tag: {photo_proof.name}")
    print(f"  name: {photo_proof.get('name')}")
    print(f"  type: {photo_proof.get('type')}")
    print(f"  value: {photo_proof.get('value', '')[:100]}")
    print(f"  id: {photo_proof.get('id')}")
    # Check if it's inside a form
    parent_form = photo_proof.find_parent("form")
    if parent_form:
        print(f"  Parent form action: {parent_form.get('action')}")
    else:
        print(f"  *** NOT INSIDE ANY FORM ***")

# Look for proof_type inputs/selects
pt = soup2.find(attrs={"name": re.compile("proof_type")})
if pt:
    print(f"\nproof_type element:")
    print(f"  tag: {pt.name}")
    print(f"  name: {pt.get('name')}")
    print(f"  type: {pt.get('type')}")
    print(f"  value: {pt.get('value', '')[:100]}")
    parent_form = pt.find_parent("form")
    if parent_form:
        print(f"  Parent form action: {parent_form.get('action')}")
    else:
        print(f"  *** NOT INSIDE ANY FORM ***")

# Also print the raw HTML around proof_type and photo_proof
raw = resp2.text
for keyword in ['proof_type', 'photo_proof']:
    idx = raw.find(keyword)
    if idx >= 0:
        print(f"\n=== Raw HTML around '{keyword}' ===")
        start = max(0, idx - 300)
        end = min(len(raw), idx + 300)
        print(raw[start:end])
