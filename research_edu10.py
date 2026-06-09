"""Check email options and school autocomplete details."""
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
print(f"Login: {'OK' if ok else 'FAIL'}")
if not ok:
    exit(1)

time.sleep(2)

# 1. Check account emails
print("\n=== Account Emails ===")
resp = c.get("/settings/emails")
print(f"Status: {resp.status_code}")
soup = BeautifulSoup(resp.text, "html.parser")
# Find email list
for email_item in soup.find_all(class_=re.compile(r"email")):
    text = email_item.get_text(strip=True)[:200]
    if "@" in text:
        print(f"  {text}")

# Also find verified emails
for li in soup.find_all("li"):
    text = li.get_text(strip=True)
    if "@" in text and len(text) < 200:
        print(f"  li: {text}")

time.sleep(2)

# 2. Get education form and check email select
print("\n=== Education Form Emails ===")
resp2 = c.get("/settings/education/developer_pack_applications/new")
soup2 = BeautifulSoup(resp2.text, "html.parser")

# Find the select element
sel = soup2.find("select", {"name": "dev_pack_form[school_email]"})
if sel:
    print(f"Select found:")
    for opt in sel.find_all("option"):
        val = opt.get("value", "")
        text = opt.get_text(strip=True)
        print(f"  option: value='{val}' text='{text}'")
else:
    print("No select found for school_email")

# Find all elements with 'email' in name/id  
print("\nEmail-related elements:")
for el in soup2.find_all(attrs={"name": re.compile(r"email", re.I)}):
    print(f"  {el.name}: name={el.get('name')} value={el.get('value','')}")
for el in soup2.find_all(attrs={"id": re.compile(r"email", re.I)}):
    print(f"  {el.name}: id={el.get('id')}")

# 3. Check the flash/notice messages on the form page
print("\n=== Page messages ===")
for msg in soup2.find_all(class_=re.compile(r"flash|notice|warning|Banner")):
    text = msg.get_text(strip=True)[:200]
    if text:
        print(f"  {text}")

# 4. Check what school name autocomplete returns for SKT
print("\n=== School autocomplete ===")
time.sleep(2)
resp3 = c.session.get(
    f"{c.BASE}/settings/education/developer_pack_applications/schools",
    params={"q": "SKT"},
    headers={
        **c.HEADERS,
        "Accept": "text/fragment+html",
    },
)
print(f"Status: {resp3.status_code}")
soup3 = BeautifulSoup(resp3.text, "html.parser")
for li in soup3.find_all("li"):
    data = {k:v for k,v in li.attrs.items() if k.startswith("data-")}
    text = li.get_text(strip=True)
    print(f"  {text}: {data}")

# 5. Save form HTML for analysis
with open("edu_form_debug.html", "w", encoding="utf-8") as f:
    f.write(resp2.text)
print("\nSaved edu_form_debug.html")

# 6. Check the select area in detail
print("\n=== Email section HTML ===")
container = soup2.find(id=re.compile(r"email", re.I))
if container:
    print(str(container)[:1000])
else:
    # Find the label for email
    for label in soup2.find_all("label"):
        text = label.get_text(strip=True)
        if "email" in text.lower():
            parent = label.parent
            print(f"Label: {text}")
            print(str(parent)[:1000])
            break
