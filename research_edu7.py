"""Research Education form with 2FA enabled."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
import pyotp
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Handle 2FA during login if needed
# The login() in client.py already handles the 2FA prompt

# Check 2FA status
resp = c.get("/settings/security")
if "Two-factor authentication is not enabled yet" in resp.text:
    print("2FA NOT enabled - cannot proceed")
    exit(1)
else:
    print("2FA is enabled")

# Get the education form
print("\n=== Education form ===")
time.sleep(2)
resp = c.get("/settings/education/developer_pack_applications/new")
print(f"Status: {resp.status_code}")

soup = BeautifulSoup(resp.text, "html.parser")
form = soup.find("form", {"action": "/settings/education/developer_pack_applications"})
if not form:
    print("No form found!")
    # Save for analysis
    with open("edu_form_2fa.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 3]
    for line in lines[:30]:
        print(f"  {line[:120]}")
    exit(1)

# Extract all fields
data = {}
for inp in form.find_all("input"):
    name = inp.get("name")
    if name and inp.get("type") != "submit":
        if name not in data:
            data[name] = inp.get("value", "")
for sel in form.find_all("select"):
    name = sel.get("name")
    if name:
        opts = sel.find_all("option")
        data[name] = opts[0].get("value", "") if opts else ""

# Fill form
data["dev_pack_form[application_type]"] = "student"
data["dev_pack_form[school_name]"] = "SKT International College"
data["dev_pack_form[school_email]"] = "thawkhant.1280@gmail.com"
data["dev_pack_form[latitude]"] = "16.8661"
data["dev_pack_form[longitude]"] = "96.1951"
data["dev_pack_form[location_shared]"] = "true"
data["dev_pack_form[form_variant]"] = "initial_form"

print(f"\nSubmitting: {json.dumps({k:v for k,v in data.items() if 'token' not in k}, indent=2)}")

# Submit with turbo-frame
time.sleep(3)
resp2 = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data=data,
    headers={
        **c.HEADERS,
        "Turbo-Frame": "dev-pack-form",
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Origin": c.BASE,
        "Referer": f"{c.BASE}/settings/education/benefits",
    },
)
print(f"\nStatus: {resp2.status_code}")
print(f"CT: {resp2.headers.get('Content-Type', '')}")
print(f"Location: {resp2.headers.get('Location', 'none')}")

with open("edu_step2_2fa.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)
print("Saved edu_step2_2fa.html")

soup2 = BeautifulSoup(resp2.text, "html.parser")
text = soup2.get_text(separator="\n", strip=True)
lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 3]
print(f"\nResponse ({len(lines)} lines):")
for line in lines[:60]:
    print(f"  {line[:150]}")

# Find forms in response (step 2 form)
print("\n=== Forms in response ===")
forms = soup2.find_all("form")
for f2 in forms:
    action = f2.get("action", "")
    enc = f2.get("enctype", "")
    if action:
        print(f"\nForm: action={action} enctype={enc}")
        for inp in f2.find_all(["input", "select", "textarea"]):
            name = inp.get("name", "")
            val = inp.get("value", "")[:80]
            typ = inp.get("type", inp.name)
            if name:
                print(f"  {typ}: {name} = {val}")

# Look for file upload elements
print("\n=== File upload elements ===")
for fa in soup2.find_all("file-attachment"):
    print(f"  file-attachment: {fa.attrs}")
for inp in soup2.find_all("input", {"type": "file"}):
    print(f"  file input: name={inp.get('name')} accept={inp.get('accept')}")
