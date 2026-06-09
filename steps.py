"""GitHub profile update steps: Name, Avatar, Billing, 2FA, Education."""

import re
import os
import time
import random
import requests
import pyotp
from bs4 import BeautifulSoup
from data import generate_profile


def _delay(lo=3.0, hi=7.0):
    """Human-like random delay."""
    time.sleep(random.uniform(lo, hi))


def _warmup(client):
    """Visit a random settings page to simulate natural browsing."""
    pages = [
        "/settings/profile",
        "/settings/appearance",
        "/settings/accessibility",
        "/settings/notifications",
    ]
    page = random.choice(pages)
    client.get(page)
    _delay(2.0, 5.0)


class ProfileUpdater:
    """Updates GitHub profile name, avatar photo, billing info, 2FA, and education."""

    def __init__(self, client):
        self.client = client
        self.profile = generate_profile()
        self.totp_secret = None
        self.recovery_codes = []

    def run(self):
        # Warm up — visit a couple of pages first
        print("Preparing...")
        self.client.get("/")
        _delay(3.0, 6.0)
        self.client.get("/settings/profile")
        _delay(4.0, 8.0)

        steps = [
            ("Profile Name", self.step_profile),
            ("Profile Photo", self.step_avatar),
            ("Billing Info", self.step_billing),
            ("Two-Factor Auth", self.step_2fa),
            ("Education Benefits", self.step_education),
        ]

        total = len(steps)
        for i, (name, func) in enumerate(steps, 1):
            if i > 1:
                _warmup(self.client)
                _delay(5.0, 12.0)
            print(f"({i}/{total}) {name}")
            try:
                ok = func()
            except Exception as e:
                print(f"  x Error: {e}")
                ok = False

            if not ok:
                print(f"  x {name} Failed!")
                return False
            print()

        return True

    # ── Step 1 : Profile Name ───────────────────────────────────

    def _get_billing_name(self):
        """Fetch current billing name to keep profile and billing in sync."""
        resp = self.client.get("/settings/billing/payment_information")
        if "/login" in resp.url:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        for form in soup.find_all("form"):
            if form.find("input", {"name": re.compile(r"billing_contact")}):
                data = self.client.extract_form_data(form)
                first = (data.get("billing_contact[first_name]") or "").strip()
                last = (data.get("billing_contact[last_name]") or "").strip()
                if first or last:
                    return f"{first} {last}".strip()
        return None

    def _sync_name(self, full_name):
        """Update self.profile name fields from a full name string."""
        parts = full_name.split(None, 1)
        self.profile["full_name"] = full_name
        self.profile["first_name"] = parts[0]
        self.profile["last_name"] = parts[1] if len(parts) > 1 else ""

    def step_profile(self):
        p = self.profile

        resp = self.client.get("/settings/profile")
        if "/login" in resp.url:
            print("  x Session expired")
            return False

        html = resp.text
        form_tag = self.client.find_profile_form(html)
        if not form_tag:
            print("  x Profile form not found")
            return False

        data = self.client.extract_form_data(form_tag)
        current_name = (data.get("user[profile_name]") or "").strip()

        # Check billing name — billing takes priority since it's harder to change
        billing_name = self._get_billing_name()
        if billing_name:
            self._sync_name(billing_name)
            if current_name == billing_name:
                print(f"  Already set: {current_name}")
                print("  Skipped")
                return True
            # Profile differs from billing — update profile to match
        elif current_name:
            # No billing name yet, but profile has name — skip
            self._sync_name(current_name)
            print(f"  Already set: {current_name}")
            print("  Skipped")
            return True

        p = self.profile
        print(f"  {p['full_name']}")
        print(f"  {p['location']}")

        action = form_tag.get("action", "")
        if not action:
            username = self.client.extract_username(html)
            action = f"/users/{username}" if username else "/settings/profile"

        token = data.get("authenticity_token") or self.client.extract_token(html)
        data["authenticity_token"] = token
        data["user[profile_name]"] = p["full_name"]
        data["user[profile_bio]"] = p["bio"]
        data["user[profile_location]"] = p["location"]

        # Fix timezone: if display is on but name is empty, turn it off
        if data.get("user[profile_display_local_time_zone]") and not data.get("user[profile_local_time_zone_name]"):
            data.pop("user[profile_display_local_time_zone]", None)

        _delay(5.0, 10.0)
        resp = self.client.post(action, data=data)

        if resp.status_code == 422:
            resp2 = self.client.get("/settings/profile")
            form_tag2 = self.client.find_profile_form(resp2.text)
            if form_tag2:
                data2 = self.client.extract_form_data(form_tag2)
                action2 = form_tag2.get("action", action)
                data2["authenticity_token"] = self.client.extract_token(resp2.text)
                data2["user[profile_name]"] = p["full_name"]
                data2["user[profile_bio]"] = p["bio"]
                data2["user[profile_location]"] = p["location"]
                resp = self.client.post(action2, data=data2)

        if resp.status_code < 400:
            print("  Profile Updated")
            return True

        err = self.client.check_flash_error(resp.text)
        print(f"  x {err or resp.status_code}")
        return False

    # ── Step 2 : Profile Photo (Avatar) ─────────────────────────

    def step_avatar(self):
        # Get profile page
        resp = self.client.get("/settings/profile")
        soup = BeautifulSoup(resp.text, "html.parser")

        print("  Downloading avatar...")

        # Download a random portrait photo matching gender
        gender = "men" if self.profile.get("gender", "male") == "male" else "women"
        num = random.randint(1, 99)
        avatar_url = f"https://randomuser.me/api/portraits/{gender}/{num}.jpg"

        try:
            img_resp = requests.get(avatar_url, timeout=15)
            if img_resp.status_code != 200 or len(img_resp.content) < 100:
                print("  x Avatar download failed")
                return False
        except Exception as e:
            print(f"  x Avatar download error: {e}")
            return False

        img_data = img_resp.content
        img_name = "avatar.jpg"

        fa = soup.find("file-attachment", class_="js-upload-avatar-image")
        if not fa:
            print("  x Avatar upload element not found")
            return False

        owner_id = fa.get("data-alambic-owner-id")
        owner_type = fa.get("data-alambic-owner-type")
        policy_url = fa.get("data-upload-policy-url")
        csrf_input = fa.find("input", class_="js-data-upload-policy-url-csrf")
        policy_csrf = csrf_input["value"] if csrf_input else None

        if not all([owner_id, policy_url, policy_csrf]):
            print("  x Missing upload params")
            return False

        # Step 1: Get upload policy
        print("  Getting upload policy...")
        _delay(3.0, 6.0)
        policy_resp = self.client.session.post(
            f"{self.client.BASE}{policy_url}?owner_id={owner_id}&owner_type={owner_type}",
            data={
                "name": img_name,
                "size": str(len(img_data)),
                "content_type": "image/jpeg",
                "authenticity_token": policy_csrf,
                "owner_type": owner_type,
                "owner_id": owner_id,
            },
            headers={
                "Accept": "application/json",
                "GitHub-Verified-Fetch": "true",
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Origin": self.client.BASE,
                "Referer": f"{self.client.BASE}/settings/profile",
            },
        )
        if policy_resp.status_code != 201:
            print(f"  x Policy failed: {policy_resp.status_code}")
            return False

        policy = policy_resp.json()

        # Step 2: Upload to storage
        print("  Uploading to storage...")
        _delay(2.0, 5.0)
        files_data = {}
        for k, v in policy.get("form", {}).items():
            files_data[k] = (None, v)
        if policy.get("same_origin") and policy.get("upload_authenticity_token"):
            files_data["authenticity_token"] = (None, policy["upload_authenticity_token"])
        files_data["file"] = (img_name, img_data, "image/jpeg")

        upload_headers = dict(policy.get("header", {}) or {})
        upload_headers["Accept"] = "application/json"
        upload_headers["GitHub-Verified-Fetch"] = "true"

        storage_resp = self.client.session.post(
            policy["upload_url"],
            files=files_data,
            headers=upload_headers,
        )
        if storage_resp.status_code != 201:
            print(f"  x Storage upload failed: {storage_resp.status_code}")
            return False

        asset_id = storage_resp.json().get("id")
        if not asset_id:
            print("  x No asset ID returned")
            return False

        # Step 3: Fetch crop dialog and submit
        print("  Setting avatar...")
        _delay(3.0, 6.0)
        crop_resp = self.client.session.get(
            f"{self.client.BASE}/settings/avatars/{asset_id}",
            headers={
                "Accept": "text/html",
                "GitHub-Verified-Fetch": "true",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Referer": f"{self.client.BASE}/settings/profile",
            },
        )
        if crop_resp.status_code != 200:
            print(f"  x Crop dialog failed: {crop_resp.status_code}")
            return False

        crop_soup = BeautifulSoup(crop_resp.text, "html.parser")
        crop_form = crop_soup.find("form", id="avatar-crop-form") or crop_soup.find("form")
        if not crop_form:
            print("  x Crop form not found")
            return False

        form_data = {}
        for inp in crop_form.find_all("input"):
            name = inp.get("name")
            if name and inp.get("type") != "file":
                form_data[name] = inp.get("value", "")

        action = crop_form.get("action", f"/settings/avatars/{asset_id}")

        scoped_csrf = None
        csrf_el = crop_soup.find(class_="js-avatar-post-csrf")
        if csrf_el:
            scoped_csrf = csrf_el.get("value")

        save_headers = {
            "Origin": self.client.BASE,
            "Referer": f"{self.client.BASE}/settings/profile",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "GitHub-Verified-Fetch": "true",
            "Accept": "*/*",
        }
        if scoped_csrf:
            save_headers["Scoped-CSRF-Token"] = scoped_csrf

        _delay(3.0, 6.0)
        save_resp = self.client.session.post(
            f"{self.client.BASE}{action}" if not action.startswith("http") else action,
            data=form_data,
            headers=save_headers,
        )

        if save_resp.status_code < 400:
            print("  Avatar Updated")
            return True

        print(f"  x Avatar save failed: {save_resp.status_code}")
        return False

    # ── Step 3 : Billing Info ───────────────────────────────────

    def step_billing(self):
        p = self.profile

        resp = self.client.get("/settings/billing/payment_information")
        if "/login" in resp.url:
            print("  x Session expired")
            return False

        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        billing_form = None
        for form in soup.find_all("form"):
            if form.find("input", {"name": re.compile(r"billing_contact")}):
                billing_form = form
                break

        if not billing_form:
            print("  Billing form not available")
            print("  Skipped")
            return True

        data = self.client.extract_form_data(billing_form)

        # Skip if billing name matches profile name
        current_first = (data.get("billing_contact[first_name]") or "").strip()
        current_last = (data.get("billing_contact[last_name]") or "").strip()
        billing_name = f"{current_first} {current_last}".strip()
        if billing_name == p["full_name"] and current_first:
            print(f"  Already set: {billing_name}")
            print("  Skipped")
            return True

        print(f"  {p['first_name']} {p['last_name']}, {p['city']}")

        action = billing_form.get("action", "/account/contact")
        token = data.get("authenticity_token") or self.client.extract_token(html)

        data.update({
            "authenticity_token": token,
            "billing_contact[first_name]": p["first_name"],
            "billing_contact[last_name]": p["last_name"],
            "billing_contact[address1]": p["address1"],
            "billing_contact[address2]": p["address2"],
            "billing_contact[city]": p["city"],
            "billing_contact[region]": p["state"],
            "billing_contact[postal_code]": p["postal_code"],
            "billing_contact[country_code]": p["country"],
        })

        _delay(5.0, 10.0)
        resp = self.client.session.post(
            f"{self.client.BASE}{action}",
            data=data,
            headers={
                "Origin": self.client.BASE,
                "Referer": f"{self.client.BASE}/settings/billing/payment_information",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-User": "?1",
            },
            allow_redirects=False,
        )

        # 302 redirect to billing page = success
        if resp.status_code in (200, 302):
            print("  Billing Updated")
            return True

        err = self.client.check_flash_error(resp.text)
        print(f"  x {err or resp.status_code}")
        return False

    # ── Step 4 : Two-Factor Authentication ──────────────────────

    def step_2fa(self):
        # Check if 2FA is already enabled
        resp = self.client.get("/settings/security")
        if "/login" in resp.url:
            print("  x Session expired")
            return False

        if "Two-factor authentication is not enabled yet" not in resp.text:
            print("  2FA already enabled")
            print("  Skipped")
            return True

        # Visit the 2FA setup intro page
        _delay(2.0, 5.0)
        resp = self.client.get("/settings/two_factor_authentication/setup/intro")
        if resp.status_code != 200 or "/login" in resp.url:
            print("  x Cannot access 2FA setup page")
            return False

        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract initiate form
        init_form = soup.find(
            "form",
            {"action": "/settings/two_factor_authentication/setup/initiate"},
        )
        if not init_form:
            print("  x Initiate form not found")
            return False

        init_data = {}
        for inp in init_form.find_all("input"):
            name = inp.get("name")
            if name:
                init_data[name] = inp.get("value", "")
        init_data["type"] = "app"

        # Extract verify form (app type)
        verify_data = {}
        for form in soup.find_all(
            "form",
            {"action": "/settings/two_factor_authentication/setup/verify"},
        ):
            type_inp = form.find("input", {"name": "type"})
            if type_inp and type_inp.get("value") == "app":
                for inp in form.find_all("input"):
                    name = inp.get("name")
                    if name:
                        verify_data[name] = inp.get("value", "")
                break

        if not verify_data:
            print("  x Verify form not found")
            return False

        # Extract recovery download form
        dl_form = soup.find(
            "form",
            {"action": "/settings/two_factor_authentication/setup/recovery_download"},
        )
        dl_data = {}
        if dl_form:
            for inp in dl_form.find_all("input"):
                name = inp.get("name")
                if name:
                    dl_data[name] = inp.get("value", "")

        # Extract enable form
        enable_form = soup.find(
            "form",
            {"action": "/settings/two_factor_authentication/setup/enable"},
        )
        enable_data = {}
        if enable_form:
            for inp in enable_form.find_all("input"):
                name = inp.get("name")
                if name:
                    enable_data[name] = inp.get("value", "")

        json_headers = {
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": self.client.BASE,
            "Referer": f"{self.client.BASE}/settings/two_factor_authentication/setup/intro",
        }

        # Step 1: POST initiate to get TOTP secret
        _delay(3.0, 6.0)
        resp2 = self.client.session.post(
            f"{self.client.BASE}/settings/two_factor_authentication/setup/initiate",
            data=init_data,
            headers={**self.client.HEADERS, **json_headers},
        )
        if resp2.status_code != 200:
            print(f"  x Initiate failed: {resp2.status_code}")
            return False

        try:
            payload = resp2.json()
        except Exception:
            print("  x Invalid initiate response")
            return False

        secret = payload.get("mashed_secret", "")
        recovery = payload.get("formatted_recovery_codes", [])
        if not secret:
            print("  x No TOTP secret returned")
            return False

        self.totp_secret = secret
        self.recovery_codes = recovery

        # Step 2: Generate TOTP code and verify
        _delay(2.0, 4.0)
        totp = pyotp.TOTP(secret)
        code = totp.now()
        verify_data["otp"] = code
        resp3 = self.client.session.post(
            f"{self.client.BASE}/settings/two_factor_authentication/setup/verify",
            data=verify_data,
            headers={**self.client.HEADERS, **json_headers},
        )
        if resp3.status_code != 200:
            print(f"  x Verify failed: {resp3.status_code}")
            return False

        # Step 3: Download recovery codes
        _delay(1.0, 2.0)
        if dl_data:
            self.client.session.post(
                f"{self.client.BASE}/settings/two_factor_authentication/setup/recovery_download",
                data=dl_data,
                headers={
                    **self.client.HEADERS,
                    "Accept": "text/plain,*/*",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": self.client.BASE,
                    "Referer": f"{self.client.BASE}/settings/two_factor_authentication/setup/intro",
                },
            )

        # Step 4: Enable 2FA
        _delay(1.0, 2.0)
        enable_data["type"] = "app"
        resp5 = self.client.session.post(
            f"{self.client.BASE}/settings/two_factor_authentication/setup/enable",
            data=enable_data,
            headers={**self.client.HEADERS, **json_headers},
        )
        if resp5.status_code != 200:
            print(f"  x Enable failed: {resp5.status_code}")
            return False

        print(f"  TOTP Secret: {secret}")
        print(f"  Recovery Codes: {len(recovery)}")
        for rc in recovery:
            print(f"    {rc}")
        print("  2FA Enabled")
        return True

    # ── Step 5 : Education Benefits ────────────────────────────

    def _generate_photo_proof_js(self, school_name):
        """Return JS code that generates a photo_proof JSON string via canvas."""
        import json
        p = self.profile
        # Escape strings for JS
        name_js = json.dumps(p["full_name"])
        school_js = json.dumps(school_name)
        reg_no = f"STU-2024-{random.randint(1000, 9999)}"
        return f'''(() => {{
            const c = document.createElement('canvas');
            c.width = 640; c.height = 480;
            const ctx = c.getContext('2d');
            ctx.fillStyle = '#2563eb'; ctx.fillRect(0, 0, 640, 480);
            ctx.fillStyle = '#fff'; ctx.font = '24px sans-serif';
            ctx.fillText('Student ID - ' + {school_js}, 30, 50);
            ctx.fillText('Academic Year 2024-2025', 30, 90);
            ctx.fillText('Student Name: ' + {name_js}, 30, 130);
            ctx.fillText('Reg No: {reg_no}', 30, 170);
            const url = c.toDataURL('image/jpeg', 0.8);
            return JSON.stringify({{
                image: url,
                metadata: {{filename: null, type: null, mimeType: "image/jpeg", deviceLabel: null}}
            }});
        }})()'''

    def step_education(self):
        from playwright.sync_api import sync_playwright
        import json

        school_name = os.environ.get("GITHUB_EDU_SCHOOL_NAME", "Yangon Technological University").strip()
        school_email = os.environ.get("GITHUB_EDU_SCHOOL_EMAIL", "thawkhant.1280@gmail.com").strip()
        latitude = os.environ.get("GITHUB_EDU_LATITUDE", "16.8661").strip()
        longitude = os.environ.get("GITHUB_EDU_LONGITUDE", "96.1951").strip()
        proof_type = os.environ.get(
            "GITHUB_EDU_PROOF_TYPE",
            "2. Dated official/unofficial transcript",
        ).strip()

        print(f"  School: {school_name}")

        # Transfer session cookies to Playwright browser
        cookies_for_pw = []
        for c in self.client.session.cookies:
            entry = {
                "name": c.name,
                "value": c.value,
                "path": c.path or "/",
            }
            domain = c.domain or ".github.com"
            if domain.startswith("."):
                entry["domain"] = domain
            else:
                entry["url"] = f"https://{domain}{c.path or '/'}"
            if c.secure is not None:
                entry["secure"] = bool(c.secure)
            cookies_for_pw.append(entry)

        photo_js = self._generate_photo_proof_js(school_name)
        school_name_js = json.dumps(school_name)
        school_email_js = json.dumps(school_email)
        proof_type_js = json.dumps(proof_type)

        js_code = '''async () => {
            const log = [];

            // === STEP 1: School info ===
            const r1 = await fetch("/settings/education/developer_pack_applications/new", {
                headers: {"Accept": "text/html", "Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
            });
            const formHtml = await r1.text();

            // Check if already submitted
            const low = formHtml.toLowerCase();
            if (low.includes('review') && (low.includes('pending') || low.includes('approved'))) {
                return {skipped: true, reason: "already submitted/under review"};
            }

            const doc = new DOMParser().parseFromString(formHtml, 'text/html');
            const form = doc.querySelector('form');
            if (!form) return {error: "no form for step 1"};

            const fd1 = new FormData();
            const token1 = form.querySelector('input[name="authenticity_token"]');
            if (token1) fd1.set('authenticity_token', token1.value);
            fd1.set('dev_pack_form[application_type]', 'student');
            fd1.set('dev_pack_form[school_name]', SCHOOL_NAME);
            fd1.set('dev_pack_form[school_email]', SCHOOL_EMAIL);
            fd1.set('dev_pack_form[latitude]', 'LATITUDE');
            fd1.set('dev_pack_form[longitude]', 'LONGITUDE');
            fd1.set('dev_pack_form[location_shared]', 'true');
            fd1.set('dev_pack_form[form_variant]', 'initial_form');
            fd1.set('dev_pack_form[browser_location]', '');
            fd1.set('dev_pack_form[utm_source]', '');
            fd1.set('dev_pack_form[utm_content]', '');
            fd1.set('continue', 'Continue');

            const s1 = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {"Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
                body: fd1,
            });
            const s1Text = await s1.text();
            if (!s1Text.includes('proof_type')) {
                const errDoc = new DOMParser().parseFromString(s1Text, 'text/html');
                const errEl = errDoc.querySelector('.Banner-title');
                return {error: "step 1 failed", detail: errEl ? errEl.textContent.trim() : s1Text.substring(0, 200)};
            }
            log.push("Step 1 OK");

            // Parse step 2 form
            let s2Html = s1Text;
            if (s1Text.includes('<turbo-stream')) {
                const tmp = new DOMParser().parseFromString(s1Text, 'text/html');
                const tmpl = tmp.querySelector('template');
                if (tmpl) {
                    const c = document.createElement('div');
                    c.appendChild(tmpl.content.cloneNode(true));
                    s2Html = c.innerHTML;
                }
            }
            const doc2 = new DOMParser().parseFromString(s2Html, 'text/html');
            const token2 = doc2.querySelector('input[name="authenticity_token"]');

            // === STEP 2: Photo proof ===
            const photoJson = PHOTO_JS;

            const fd2 = new FormData();
            if (token2) fd2.set('authenticity_token', token2.value);
            doc2.querySelectorAll('input[type="hidden"]').forEach(el => {
                if (el.name && el.name !== 'authenticity_token')
                    fd2.set(el.name, el.value || '');
            });
            fd2.set('dev_pack_form[proof_type]', PROOF_TYPE);
            fd2.set('dev_pack_form[photo_proof]', photoJson);
            fd2.set('dev_pack_form[form_variant]', 'upload_proof_form');
            fd2.set('continue', 'Process my application');

            const s2 = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {"Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
                body: fd2,
            });
            const s2Text = await s2.text();

            const hasCampus = s2Text.includes('not on campus') || s2Text.includes('far_from_campus');
            const hasSuccess2 = ['thank', 'submitted', 'pending', 'approved'].some(w => s2Text.toLowerCase().includes(w));
            const hasError2 = s2Text.includes('Banner--error') || s2Text.includes('flash-error');

            if (hasError2 && !hasCampus) {
                const errDoc = new DOMParser().parseFromString(s2Text, 'text/html');
                const errEl = errDoc.querySelector('.Banner-title');
                return {error: "step 2 failed", detail: errEl ? errEl.textContent.trim() : ''};
            }

            if (hasSuccess2) {
                log.push("Step 2 OK - submitted");
                return {success: true, steps: 2, log};
            }

            if (!hasCampus) {
                return {error: "unexpected response after step 2"};
            }
            log.push("Step 2 OK - campus question");

            // === STEP 3: Campus reason ===
            let s3Html = s2Text;
            if (s2Text.includes('<turbo-stream')) {
                const tmp = new DOMParser().parseFromString(s2Text, 'text/html');
                const tmpl = tmp.querySelector('template');
                if (tmpl) {
                    const c = document.createElement('div');
                    c.appendChild(tmpl.content.cloneNode(true));
                    s3Html = c.innerHTML;
                }
            }
            const doc3 = new DOMParser().parseFromString(s3Html, 'text/html');
            const token3 = doc3.querySelector('input[name="authenticity_token"]');

            const fd3 = new FormData();
            if (token3) fd3.set('authenticity_token', token3.value);
            doc3.querySelectorAll('input[type="hidden"]').forEach(el => {
                if (el.name && el.name !== 'authenticity_token')
                    fd3.set(el.name, el.value || '');
            });

            // Pick distance option
            const radios = [];
            doc3.querySelectorAll('input[type="radio"]').forEach(el => {
                const lbl = doc3.querySelector('label[for="' + el.id + '"]');
                radios.push({name: el.name, value: el.value, label: lbl ? lbl.textContent.trim().toLowerCase() : ''});
            });
            const distOpt = radios.find(o => o.label.includes('distance') || o.value.includes('distant'));
            const chosen = distOpt || radios[0];
            if (chosen) fd3.set(chosen.name, chosen.value);

            fd3.set('continue', 'Submit Application');

            const s3 = await fetch("/settings/education/developer_pack_applications", {
                method: "POST",
                headers: {"Turbo-Frame": "dev-pack-form"},
                credentials: "same-origin",
                body: fd3,
            });
            const s3Text = await s3.text();

            const hasError3 = s3Text.includes('Banner--error') || s3Text.includes('flash-error');
            if (hasError3) {
                const errDoc = new DOMParser().parseFromString(s3Text, 'text/html');
                const errEl = errDoc.querySelector('.Banner-title');
                return {error: "step 3 failed", detail: errEl ? errEl.textContent.trim() : ''};
            }

            log.push("Step 3 OK");
            return {success: true, steps: 3, log};
        }'''

        # Inject config values into JS
        js_code = js_code.replace("SCHOOL_NAME", school_name_js)
        js_code = js_code.replace("SCHOOL_EMAIL", school_email_js)
        js_code = js_code.replace("'LATITUDE'", json.dumps(latitude))
        js_code = js_code.replace("'LONGITUDE'", json.dumps(longitude))
        js_code = js_code.replace("PROOF_TYPE", proof_type_js)
        js_code = js_code.replace("PHOTO_JS", photo_js)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/134.0.0.0 Safari/537.36"
                ),
            )
            try:
                context.add_cookies(cookies_for_pw)
                page = context.new_page()

                # Navigate to GitHub to establish context for fetch()
                page.goto("https://github.com/settings/profile", timeout=30000, wait_until="load")
                page.wait_for_timeout(2000)

                if "login" in page.url:
                    print("  x Session expired (Playwright)")
                    return False

                _delay(1.0, 2.0)
                result = page.evaluate(js_code)

                if result.get("skipped"):
                    print(f"  Application already submitted / under review")
                    print("  Skipped")
                    return True

                if result.get("error"):
                    detail = result.get("detail", "")
                    print(f"  x {result['error']}: {detail}")
                    return False

                if result.get("success"):
                    steps = result.get("steps", "?")
                    for msg in result.get("log", []):
                        print(f"  {msg}")
                    print("  Education Submitted")
                    return True

                print("  x Unexpected result from education flow")
                return False
            finally:
                browser.close()
