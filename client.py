"""GitHub HTTP Client — session/cookie management + HTML parsing"""

import re
import time
import random
import requests
from bs4 import BeautifulSoup


class GitHubClient:
    BASE = "https://github.com"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/134.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8,my;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Sec-Ch-Ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.username = None

    # ── Authentication ──────────────────────────────────────────

    def set_cookies(self, raw_cookie):
        """Parse raw cookie string from browser DevTools and set on session."""
        raw = re.sub(
            r"^(cookie:\s*|github\s*cookie:\s*)", "", raw_cookie, flags=re.I
        ).strip()
        for pair in raw.split(";"):
            pair = pair.strip()
            if "=" in pair:
                name, value = pair.split("=", 1)
                self.session.cookies.set(
                    name.strip(), value.strip(), domain=".github.com"
                )

    def verify_session(self):
        """Check if current session is valid (not redirected to /login)."""
        try:
            resp = self.session.get(
                f"{self.BASE}/settings/profile", allow_redirects=True
            )
            if "/login" in resp.url:
                return False
            if resp.status_code == 200:
                self.username = self.extract_username(resp.text)
                return True
            return False
        except Exception:
            return False

    def login(self, username, password, totp_secret=None):
        """Login with username & password. Handles 2FA prompt."""
        try:
            # Visit homepage first like a real user
            self.session.get(f"{self.BASE}/")
            time.sleep(random.uniform(2.0, 4.0))

            resp = self.session.get(f"{self.BASE}/login")
            token = self.extract_token(resp.text)
            if not token:
                return False

            # Simulate reading the login page then typing
            time.sleep(random.uniform(3.0, 6.0))

            data = {
                "authenticity_token": token,
                "login": username,
                "password": password,
                "commit": "Sign in",
            }
            time.sleep(random.uniform(2.0, 4.0))
            resp = self.session.post(f"{self.BASE}/session", data=data)

            # 2FA handling
            if "two-factor" in resp.url or "two_factor" in resp.url:
                if totp_secret:
                    import pyotp
                    otp = pyotp.TOTP(totp_secret).now()
                else:
                    otp = input("  2FA Code: ").strip()
                token = self.extract_token(resp.text)
                resp = self.session.post(
                    f"{self.BASE}/sessions/two-factor",
                    data={"authenticity_token": token, "otp": otp},
                )

            # Check success
            cookies_str = str(self.session.cookies)
            if "logged_in" in cookies_str or "user_session" in cookies_str:
                self.username = username
                return True
            if "/login" not in resp.url and resp.status_code < 400:
                self.username = username
                return True
            return False
        except Exception as e:
            print(f"  Error: {e}")
            return False

    # ── HTTP Methods ────────────────────────────────────────────

    def get(self, path, **kwargs):
        url = path if path.startswith("http") else f"{self.BASE}{path}"
        return self.session.get(url, **kwargs)

    def post(self, path, data=None, **kwargs):
        url = path if path.startswith("http") else f"{self.BASE}{path}"
        headers = kwargs.pop("headers", {})
        headers.setdefault("Origin", self.BASE)
        headers.setdefault("Referer", url)
        headers.setdefault("Sec-Fetch-Site", "same-origin")
        headers.setdefault("Sec-Fetch-Mode", "navigate")
        headers.setdefault("Sec-Fetch-Dest", "document")
        return self.session.post(url, data=data, headers=headers, **kwargs)

    # ── HTML Parsing Helpers ────────────────────────────────────

    def extract_token(self, html):
        """Extract CSRF authenticity_token from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        tag = soup.find("input", {"name": "authenticity_token"})
        if tag and tag.get("value"):
            return tag["value"]

        meta = soup.find("meta", {"name": "csrf-token"})
        if meta and meta.get("content"):
            return meta["content"]

        m = re.search(r'authenticity_token["\s]*value="([^"]+)"', html)
        return m.group(1) if m else None

    def extract_hidden_inputs(self, html, form_attrs=None):
        """Extract all hidden <input> fields from form."""
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form", form_attrs) if form_attrs else soup
        if not form:
            return {}

        inputs = {}
        for tag in (form.find_all("input", {"type": "hidden"}) or []):
            name = tag.get("name")
            if name:
                inputs[name] = tag.get("value", "")
        return inputs

    def extract_form_fields(self, html, form_attrs=None):
        """Extract all form fields (input, textarea, select)."""
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form", form_attrs) if form_attrs else soup.find("form")
        if not form:
            return {}

        fields = {}
        for tag in form.find_all("input"):
            name = tag.get("name")
            if name and tag.get("type") not in ("submit", "button", "image"):
                fields[name] = tag.get("value", "")

        for tag in form.find_all("textarea"):
            name = tag.get("name")
            if name:
                fields[name] = tag.string or ""

        for tag in form.find_all("select"):
            name = tag.get("name")
            if name:
                sel = tag.find("option", selected=True)
                fields[name] = sel.get("value", "") if sel else ""
        return fields

    def extract_form_action(self, html, form_attrs=None):
        """Extract form action URL."""
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form", form_attrs) if form_attrs else soup.find("form")
        return form.get("action", "") if form else ""

    def find_profile_form(self, html):
        """Find the profile update form (the one containing user[profile_name])."""
        soup = BeautifulSoup(html, "html.parser")
        for form in soup.find_all("form"):
            if form.find("input", {"name": "user[profile_name]"}):
                return form
            if form.find("input", {"name": re.compile(r"user\[profile")}):
                return form
        return None

    def extract_form_data(self, form_tag):
        """Extract all fields (hidden + visible) from a BeautifulSoup form tag."""
        fields = {}
        for tag in form_tag.find_all("input"):
            name = tag.get("name")
            if name and tag.get("type") not in ("submit", "button", "image", "file"):
                fields[name] = tag.get("value", "")
        for tag in form_tag.find_all("textarea"):
            name = tag.get("name")
            if name:
                fields[name] = tag.string or ""
        for tag in form_tag.find_all("select"):
            name = tag.get("name")
            if name:
                sel = tag.find("option", selected=True)
                fields[name] = sel.get("value", "") if sel else ""
        return fields

    def extract_username(self, html):
        """Extract current username from profile page."""
        soup = BeautifulSoup(html, "html.parser")
        meta = soup.find("meta", {"name": "user-login"})
        if meta and meta.get("content"):
            return meta["content"]
        m = re.search(r'data-login="([^"]+)"', html)
        if m:
            return m.group(1)
        # From dotcom_user cookie
        return self.session.cookies.get("dotcom_user", "")

    def check_flash_error(self, html):
        """Check for flash/error messages on the page."""
        soup = BeautifulSoup(html, "html.parser")
        for cls in ("flash-error", "flash-warn", "error"):
            el = soup.find("div", class_=cls)
            if el:
                return el.get_text(strip=True)
        return None
