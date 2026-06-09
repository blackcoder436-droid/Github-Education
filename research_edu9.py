"""Debug education form - check exact fields and submission."""
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

# Get form via turbo frame (the actual form loads in turbo-frame)
time.sleep(2)

# First try the /new page
resp = c.get("/settings/education/developer_pack_applications/new")
print(f"\nNew page: {resp.status_code}")
soup = BeautifulSoup(resp.text, "html.parser")

form = soup.find("form", {"action": "/settings/education/developer_pack_applications"})
if form:
    print("\n=== Form found ===")
    print(f"Method: {form.get('method')}")
    print(f"Action: {form.get('action')}")
    print(f"Enctype: {form.get('enctype')}")
    
    print("\nAll inputs:")
    for inp in form.find_all(["input", "select", "textarea"]):
        name = inp.get("name", "")
        val = inp.get("value", "")
        typ = inp.get("type", inp.name)
        checked = inp.get("checked")
        disabled = inp.get("disabled")
        required = inp.get("required")
        placeholder = inp.get("placeholder", "")
        data_attrs = {k:v for k,v in inp.attrs.items() if k.startswith("data-")}
        if name:
            extra = ""
            if checked is not None: extra += " [CHECKED]"
            if disabled is not None: extra += " [DISABLED]"
            if required is not None: extra += " [REQUIRED]"
            if placeholder: extra += f" placeholder='{placeholder}'"
            if data_attrs: extra += f" data={data_attrs}"
            print(f"  {typ}: name='{name}' value='{val[:80]}'{extra}")
    
    # Check for radio buttons
    print("\nRadio buttons:")
    for radio in form.find_all("input", type="radio"):
        name = radio.get("name")
        val = radio.get("value")
        checked = radio.get("checked")
        print(f"  {name} = {val} {'[CHECKED]' if checked is not None else ''}")
    
    # Check labels
    print("\nLabels:")
    for label in form.find_all("label"):
        label_for = label.get("for", "")
        text = label.get_text(strip=True)[:100]
        if text:
            print(f"  for='{label_for}': {text}")
    
    # Autocomplete elements
    print("\nAuto-complete:")
    for ac in form.find_all("auto-complete"):
        src = ac.get("src", "")
        print(f"  src={src}")
        for inp in ac.find_all("input"):
            print(f"    input: name={inp.get('name')} value={inp.get('value')} type={inp.get('type')}")
    
    # Error/flash messages in response
    print("\nFlash messages on page:")
    for flash in soup.find_all(class_=re.compile(r"flash|error|alert|notice")):
        text = flash.get_text(strip=True)[:200]
        if text:
            print(f"  {text}")

    # Now build data exactly from form
    data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        typ = inp.get("type", "text")
        if not name or typ in ("submit", "button"):
            continue
        if typ == "radio":
            if inp.get("checked") is not None:
                data[name] = inp.get("value", "")
        elif typ == "checkbox":
            if inp.get("checked") is not None:
                data[name] = inp.get("value", "on")
        else:
            if name not in data:
                data[name] = inp.get("value", "")
    
    for sel in form.find_all("select"):
        name = sel.get("name")
        if name:
            selected = sel.find("option", selected=True)
            if selected:
                data[name] = selected.get("value", "")
    
    print(f"\nExtracted form data ({len(data)} fields):")
    for k,v in data.items():
        print(f"  {k} = {v[:80]}")
    
    # Fill in our values
    data["dev_pack_form[application_type]"] = "student"
    data["dev_pack_form[school_name]"] = "SKT International College"
    data["dev_pack_form[school_email]"] = "thawkhant.1280@gmail.com"
    data["dev_pack_form[latitude]"] = "16.8661"
    data["dev_pack_form[longitude]"] = "96.1951"
    data["dev_pack_form[location_shared]"] = "true"
    data["dev_pack_form[form_variant]"] = "initial_form"
    
    print(f"\nFinal data to submit:")
    for k,v in data.items():
        print(f"  {k} = {v[:80]}")
    
    print("\nSubmitting...")
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
    print(f"Response: {resp2.status_code}")
    
    with open("edu_step2_debug.html", "w", encoding="utf-8") as f:
        f.write(resp2.text)
    
    soup2 = BeautifulSoup(resp2.text, "html.parser")
    
    # Check for errors
    for err in soup2.find_all(class_=re.compile(r"error|flash|alert")):
        text = err.get_text(strip=True)[:200]
        if text:
            print(f"  ERROR: {text}")
    
    text = soup2.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    print(f"\nResponse text ({len(lines)} lines):")
    for line in lines[:40]:
        print(f"  {line[:150]}")
else:
    print("No form found!")
    with open("edu_new_debug.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    # Check for turbo-frame
    tf = soup.find("turbo-frame")
    if tf:
        print(f"Turbo-frame: id={tf.get('id')} src={tf.get('src')}")
