"""Research education form with auto-2FA login."""
import os, re, json, time
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
ok = c.login(
    os.environ['GITHUB_USERNAME'], 
    os.environ['GITHUB_PASSWORD'],
    totp_secret="SFDHLAA7MDH2S7TN",
)
print(f"Login: {'OK' if ok else 'FAIL'} as {c.username}")
if not ok:
    exit(1)

# Verify session
resp = c.get("/settings/profile")
print(f"Profile: {resp.status_code} login_redir={'yes' if '/login' in resp.url else 'no'}")

# Get education form
print("\n=== Education form ===")
time.sleep(2)
resp = c.get("/settings/education/developer_pack_applications/new")
print(f"Status: {resp.status_code} URL: {resp.url}")

if "/login" in resp.url:
    print("Redirected to login - session issue")
    exit(1)

soup = BeautifulSoup(resp.text, "html.parser")
form = soup.find("form", {"action": "/settings/education/developer_pack_applications"})
if not form:
    print("No form!")
    with open("edu_debug.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 5]
    for line in lines[:20]:
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

print(f"\nSubmitting initial form...")
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
print(f"Status: {resp2.status_code}")

with open("edu_step2_result.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)
print("Saved edu_step2_result.html")

soup2 = BeautifulSoup(resp2.text, "html.parser")
text = soup2.get_text(separator="\n", strip=True)
lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 3]
print(f"\nResponse ({len(lines)} lines):")
for line in lines[:60]:
    print(f"  {line[:150]}")

# Find forms
print("\n=== Forms ===")
forms = soup2.find_all("form")
for f2 in forms:
    action = f2.get("action", "")
    enc = f2.get("enctype", "")
    method = f2.get("method", "")
    if action:
        print(f"\nForm: action={action} method={method} enctype={enc}")
        for inp in f2.find_all(["input", "select", "textarea"]):
            name = inp.get("name", "")
            val = inp.get("value", "")[:80]
            typ = inp.get("type", inp.name)
            if name:
                print(f"  {typ}: {name} = {val}")

# File uploads
print("\n=== File uploads ===")
for fa in soup2.find_all("file-attachment"):
    print(f"  file-attachment: {dict(fa.attrs)}")
    csrf = fa.find("input", class_="js-data-upload-policy-url-csrf")
    if csrf:
        print(f"    csrf: {csrf.get('value','')[:60]}")
