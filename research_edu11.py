"""Debug school autocomplete and form submission."""
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

time.sleep(2)

# School autocomplete - try different queries
for q in ["SKT", "SKT International", "skt", "International"]:
    print(f"\n=== School search: '{q}' ===")
    resp = c.session.get(
        f"{c.BASE}/settings/education/developer_pack_applications/schools",
        params={"q": q},
        headers={
            **c.HEADERS,
            "Accept": "text/fragment+html",
        },
    )
    print(f"Status: {resp.status_code} Len: {len(resp.text)}")
    print(f"Raw: {resp.text[:500]}")
    time.sleep(1)

# Now get the form and check the email warning more carefully
print("\n=== Full email section ===")
time.sleep(2)
resp2 = c.get("/settings/education/developer_pack_applications/new")
soup2 = BeautifulSoup(resp2.text, "html.parser")

# Find the banner/warning about emails
for banner in soup2.find_all(True, class_=re.compile(r"Banner|flash|FormControl-inlineValidation")):
    text = banner.get_text(separator=" ", strip=True)[:300]
    if "email" in text.lower() or "school" in text.lower():
        print(f"  Banner: {text}")
        # Also print the HTML structure
        links = banner.find_all("a")
        for a in links:
            print(f"    Link: {a.get('href')} text='{a.get_text(strip=True)}'")

# Try submitting with the gmail address but also check if we need school_id or other hidden params
print("\n=== Check for hidden school_id field ===")
form = soup2.find("form", {"action": "/settings/education/developer_pack_applications"})
if form:
    # Check all data-target, data-action attributes
    for el in form.find_all(True, attrs={"data-target": True}):
        print(f"  {el.name}: data-target={el.get('data-target')} name={el.get('name','')}")
    
    print("\nAll data attrs on form elements:")
    for el in form.find_all(True):
        data_attrs = {k:v for k,v in el.attrs.items() if k.startswith("data-")}
        if data_attrs and el.get("name"):
            print(f"  {el.name} name={el.get('name')}: {data_attrs}")

# Check if maybe we need to try with turbo-stream accept
print("\n=== Try submitting as regular POST ===")
time.sleep(3)

# Get fresh form
resp3 = c.get("/settings/education/developer_pack_applications/new")
soup3 = BeautifulSoup(resp3.text, "html.parser")
form = soup3.find("form", {"action": "/settings/education/developer_pack_applications"})

data = {}
for inp in form.find_all("input"):
    name = inp.get("name")
    typ = inp.get("type", "text")
    if not name or typ in ("submit", "button"):
        continue
    if typ == "radio":
        continue  # handle separately
    if name not in data:
        data[name] = inp.get("value", "")

# Set values
data["dev_pack_form[application_type]"] = "student"
data["dev_pack_form[school_name]"] = "SKT International College"
data["dev_pack_form[school_email]"] = "thawkhant.1280@gmail.com"
data["dev_pack_form[latitude]"] = "16.8661"
data["dev_pack_form[longitude]"] = "96.1951"
data["dev_pack_form[location_shared]"] = "true"
data["dev_pack_form[form_variant]"] = "initial_form"
data["dev_pack_form[browser_location]"] = "Yangon, Myanmar"

print(f"\nSubmitting ({len(data)} fields):")
for k,v in data.items():
    print(f"  {k} = {v[:80]}")

# Try without turbo frame first
resp4 = c.session.post(
    f"{c.BASE}/settings/education/developer_pack_applications",
    data=data,
    headers={
        **c.HEADERS,
        "Referer": f"{c.BASE}/settings/education/developer_pack_applications/new",
    },
)
print(f"\nRegular POST: {resp4.status_code} url={resp4.url}")
with open("edu_regular_post.html", "w", encoding="utf-8") as f:
    f.write(resp4.text)

soup4 = BeautifulSoup(resp4.text, "html.parser")
# Check for errors
for err in soup4.find_all(class_=re.compile(r"error|flash|alert|Banner")):
    text = err.get_text(strip=True)[:200]
    if text:
        print(f"  Error: {text}")

# Check for success indicators
title = soup4.find("title")
if title:
    print(f"  Title: {title.get_text(strip=True)[:100]}")

text = soup4.get_text(separator="\n", strip=True)
lines = [l for l in text.split("\n") if l.strip() and len(l.strip()) > 5]
for line in lines[:30]:
    print(f"  {line[:150]}")
