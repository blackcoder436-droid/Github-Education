"""Try submitting all fields at once, or with different proof_type formats."""
import os, time, re, sys
from dotenv import load_dotenv
from client import GitHubClient
from bs4 import BeautifulSoup
load_dotenv()

c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {ok}")
time.sleep(2)

def fresh_token():
    """Get a fresh CSRF token from the form page."""
    resp = c.get("/settings/education/developer_pack_applications/new")
    soup = BeautifulSoup(resp.text, "html.parser")
    frame = soup.find("turbo-frame", id="dev-pack-form")
    form = frame.find("form")
    return form.find("input", attrs={"name": "authenticity_token"})["value"]

def test_submit(label, data, headers=None):
    """Submit and check result."""
    if headers is None:
        headers = {
            "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
            "Turbo-Frame": "dev-pack-form",
            "Origin": "https://github.com",
            "Referer": "https://github.com/settings/education/developer_pack_applications/new",
            "Sec-Fetch-Mode": "same-origin",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Site": "same-origin",
        }
    resp = c.session.post(
        "https://github.com/settings/education/developer_pack_applications",
        data=data,
        headers=headers,
    )
    soup = BeautifulSoup(resp.text, "html.parser")
    banner = soup.find(class_="Banner-title")
    err = banner.get_text(strip=True) if banner else "(no banner)"
    
    proof = soup.find("input", attrs={"name": "dev_pack_form[proof_type]"})
    pval = proof.get("value", "(no attr)") if proof else "(not found)"
    
    # Check if it succeeded (redirected to applications page or thank you)
    success_indicators = ["thank", "submitted", "review", "Your application"]
    success = any(s in resp.text.lower() for s in success_indicators)
    
    print(f"\n  [{label}] {resp.status_code}, {len(resp.text)} bytes")
    print(f"    Banner: {err[:100]}")
    print(f"    proof_type value: {pval!r}")
    if "already" in resp.text.lower():
        print(f"    NOTE: 'already' found in response")
    
    with open(f"test_{label.replace(' ', '_')}.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    
    return resp

# ============================================================
# TEST 1: All fields at once with form_variant=upload_proof_form
# ============================================================
print("\n=== TEST 1: Single POST with all fields ===")
token = fresh_token()
time.sleep(2)

data1 = {
    "authenticity_token": token,
    "dev_pack_form[application_type]": "student",
    "dev_pack_form[school_name]": "SKT International College",
    "dev_pack_form[school_email]": "thawkhant.1280@gmail.com",
    "dev_pack_form[latitude]": "16.8661",
    "dev_pack_form[longitude]": "96.1951",
    "dev_pack_form[location_shared]": "true",
    "dev_pack_form[browser_location]": "",
    "dev_pack_form[utm_source]": "",
    "dev_pack_form[utm_content]": "",
    "dev_pack_form[proof_type]": "2. Dated official/unofficial transcript",
    "dev_pack_form[photo_proof]": "data:image/jpeg;base64,/9j/4AAQ==",
    "dev_pack_form[form_variant]": "upload_proof_form",
    "submit": "Submit Application",
}
test_submit("single_post", data1)

# ============================================================
# TEST 2: Try different proof_type formats
# ============================================================
proof_formats = [
    "2",
    "dated_official_unofficial_transcript",
    "Dated official/unofficial transcript",
    "official_transcript",
]

for fmt in proof_formats:
    time.sleep(3)
    
    # Step 1 first
    token = fresh_token()
    time.sleep(1)
    
    step1 = {
        "authenticity_token": token,
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
    
    resp1 = c.session.post(
        "https://github.com/settings/education/developer_pack_applications",
        data=step1,
        headers={
            "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
            "Turbo-Frame": "dev-pack-form",
            "Origin": "https://github.com",
            "Referer": "https://github.com/settings/education/developer_pack_applications/new",
            "Sec-Fetch-Mode": "same-origin",
            "Sec-Fetch-Dest": "empty",
        },
    )
    
    if "proof_type" not in resp1.text:
        print(f"\n  [{fmt}] Step 1 failed!")
        continue
    
    soup1 = BeautifulSoup(resp1.text, "html.parser")
    form1 = soup1.find("form")
    token1 = form1.find("input", attrs={"name": "authenticity_token"})["value"]
    
    step2 = {}
    for inp in form1.find_all("input", type="hidden"):
        name = inp.get("name", "")
        value = inp.get("value", "")
        if name:
            step2[name] = value
    
    step2["dev_pack_form[proof_type]"] = fmt
    step2["dev_pack_form[photo_proof]"] = "data:image/jpeg;base64,/9j/4AAQ=="
    step2["dev_pack_form[form_variant]"] = "upload_proof_form"
    step2["submit"] = "Submit Application"
    
    time.sleep(1)
    test_submit(f"format_{fmt[:20]}", step2)

# ============================================================
# TEST 3: Send with unencoded brackets in body (raw post)
# ============================================================
print("\n\n=== TEST 3: Raw POST body with unencoded brackets ===")
time.sleep(3)

token = fresh_token()
time.sleep(1)

step1_raw = {
    "authenticity_token": token,
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

resp1_raw = c.session.post(
    "https://github.com/settings/education/developer_pack_applications",
    data=step1_raw,
    headers={
        "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
        "Turbo-Frame": "dev-pack-form",
        "Origin": "https://github.com",
        "Referer": "https://github.com/settings/education/developer_pack_applications/new",
        "Sec-Fetch-Mode": "same-origin",
        "Sec-Fetch-Dest": "empty",
    },
)

if "proof_type" in resp1_raw.text:
    soup1_raw = BeautifulSoup(resp1_raw.text, "html.parser")
    form1_raw = soup1_raw.find("form")
    token1_raw = form1_raw.find("input", attrs={"name": "authenticity_token"})["value"]
    
    # Build raw body with unencoded brackets
    from urllib.parse import quote
    parts = []
    fields = [
        ("authenticity_token", token1_raw),
        ("dev_pack_form[proof_type]", "2. Dated official/unofficial transcript"),
        ("dev_pack_form[photo_proof]", "data:image/jpeg;base64,/9j/4AAQ=="),
        ("dev_pack_form[application_type]", "student"),
        ("dev_pack_form[browser_location]", ""),
        ("dev_pack_form[form_variant]", "upload_proof_form"),
        ("dev_pack_form[latitude]", "16.8661"),
        ("dev_pack_form[location_shared]", "true"),
        ("dev_pack_form[longitude]", "96.1951"),
        ("dev_pack_form[school_email]", "thawkhant.1280@gmail.com"),
        ("dev_pack_form[school_name]", "SKT International College"),
        ("dev_pack_form[utm_content]", ""),
        ("dev_pack_form[utm_source]", ""),
        ("submit", "Submit Application"),
    ]
    
    # Don't encode brackets - send as raw body
    raw_parts = []
    for name, value in fields:
        # Only encode value, keep brackets in name unencoded
        enc_value = quote(value, safe='')
        raw_parts.append(f"{name}={enc_value}")
    
    raw_body = "&".join(raw_parts)
    print(f"  Raw body (first 200): {raw_body[:200]}")
    
    time.sleep(1)
    resp2_raw = c.session.post(
        "https://github.com/settings/education/developer_pack_applications",
        data=raw_body.encode('utf-8'),
        headers={
            "Accept": "text/vnd.turbo-stream.html, text/html, application/xhtml+xml",
            "Turbo-Frame": "dev-pack-form",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://github.com",
            "Referer": "https://github.com/settings/education/developer_pack_applications/new",
            "Sec-Fetch-Mode": "same-origin",
            "Sec-Fetch-Dest": "empty",
        },
    )
    
    soup2_raw = BeautifulSoup(resp2_raw.text, "html.parser")
    banner_raw = soup2_raw.find(class_="Banner-title")
    err_raw = banner_raw.get_text(strip=True) if banner_raw else "(no banner)"
    proof_raw = soup2_raw.find("input", attrs={"name": "dev_pack_form[proof_type]"})
    pval_raw = proof_raw.get("value", "(no attr)") if proof_raw else "(not found)"
    
    print(f"  Result: {resp2_raw.status_code}, {len(resp2_raw.text)} bytes")
    print(f"  Banner: {err_raw[:100]}")
    print(f"  proof_type: {pval_raw!r}")
else:
    print("  Step 1 failed for raw test")
