"""Research edu form - check 2FA status and add school_id."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'])
print("Logged in as:", c.username)

# Check if 2FA is enabled
resp = c.get("/settings/security")
if "Disable two-factor authentication" in resp.text:
    print("2FA: ENABLED")
else:
    print("2FA: NOT ENABLED - need to enable first")
    # Exit since we need 2FA for this school
    # For now, let's continue to see the form structure

# Get the form fresh
resp = c.get("/settings/education/developer_pack_applications/new")
soup = BeautifulSoup(resp.text, "html.parser")
form = soup.find("form", {"action": "/settings/education/developer_pack_applications"})

# Extract all fields
data = {}
for inp in form.find_all("input"):
    name = inp.get("name")
    if name and inp.get("type") != "submit":
        if name not in data:  # Don't override first value
            data[name] = inp.get("value", "")
for sel in form.find_all("select"):
    name = sel.get("name")
    if name:
        # Get first option value
        opts = sel.find_all("option")
        data[name] = opts[0].get("value", "") if opts else ""

# Set values
data["dev_pack_form[application_type]"] = "student"
data["dev_pack_form[school_name]"] = "SKT International College"
data["dev_pack_form[school_email]"] = "thawkhant.1280@gmail.com"
data["dev_pack_form[latitude]"] = "16.8661"
data["dev_pack_form[longitude]"] = "96.1951"  
data["dev_pack_form[location_shared]"] = "true"
data["dev_pack_form[form_variant]"] = "initial_form"

# Check what all hidden inputs exist 
print("\nAll form field names:")
for k, v in sorted(data.items()):
    print(f"  {k} = {v[:80]}")

# Check the full form HTML for any hidden school_id field or data we might be missing
print("\nLooking for school-related attributes in form:")
for tag in form.find_all(True):
    for attr, val in tag.attrs.items():
        if isinstance(val, str) and "school" in attr.lower():
            print(f"  <{tag.name}>[{attr}] = {val[:100]}")

# Submit
print("\n=== Submitting ===")
time.sleep(2)
resp2 = c.post("/settings/education/developer_pack_applications", data=data)
print(f"Status: {resp2.status_code}")

# Check response
soup2 = BeautifulSoup(resp2.text, "html.parser")
text = soup2.get_text(separator="\n", strip=True)
lines = [l for l in text.split("\n") if l.strip() and len(l.strip()) > 5]
print(f"\nResponse text:")
for line in lines[:20]:
    print(f"  {line[:150]}")

# Also try via turbo-frame headers
print("\n=== Try with Turbo-Frame header ===")
resp = c.get("/settings/education/developer_pack_applications/new")
soup = BeautifulSoup(resp.text, "html.parser")
form = soup.find("form", {"action": "/settings/education/developer_pack_applications"})
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

data["dev_pack_form[application_type]"] = "student"
data["dev_pack_form[school_name]"] = "SKT International College"
data["dev_pack_form[school_email]"] = "thawkhant.1280@gmail.com"
data["dev_pack_form[latitude]"] = "16.8661"
data["dev_pack_form[longitude]"] = "96.1951"
data["dev_pack_form[location_shared]"] = "true"
data["dev_pack_form[form_variant]"] = "initial_form"

time.sleep(2)
resp3 = c.session.post(
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
print(f"Status: {resp3.status_code}")
print(f"CT: {resp3.headers.get('Content-Type','')}")

with open("edu_submit_result.html", "w", encoding="utf-8") as f:
    f.write(resp3.text)
print("Saved edu_submit_result.html")

soup3 = BeautifulSoup(resp3.text, "html.parser")
text3 = soup3.get_text(separator="\n", strip=True)
lines3 = [l for l in text3.split("\n") if l.strip() and len(l.strip()) > 5]
print(f"\nResponse text ({len(lines3)} lines):")
for line in lines3[:40]:
    print(f"  {line[:150]}")

# Find forms in response
forms3 = soup3.find_all("form")
for f3 in forms3:
    action = f3.get("action", "")
    if action:
        enc = f3.get("enctype", "")
        print(f"\n  Form: action={action} enctype={enc}")
        for inp in f3.find_all(["input", "select", "textarea"]):
            name = inp.get("name", "")
            val = inp.get("value", "")[:80]
            typ = inp.get("type", inp.name)
            if name:
                print(f"    {typ}: {name} = {val}")
