"""GitHub HTTP Client — session/cookie management + HTML parsing"""

import re
import time
import random
import requests
import json
from datetime import datetime, timedelta
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

    # ── Account Validation ──────────────────────────────────────

    def get_account_created_date(self):
        """Fetch GitHub account creation date via HTML parsing (primary) or GraphQL (fallback)."""
        try:
            if not self.username:
                # Try to fetch from public profile page
                resp = self.get(f"/{self.username if self.username else 'user'}", timeout=10)
                if resp.status_code == 200:
                    self.username = self.extract_username(resp.text)
            
            if not self.username:
                print("  x Cannot determine username")
                return None
            
            # PRIMARY METHOD: Parse from profile page HTML (more reliable)
            print("  • Fetching account creation date...")
            try:
                resp = self.get(f"/{self.username}", timeout=15)
                if resp.status_code == 200:
                    created_at = self._parse_created_date_from_html(resp.text)
                    if created_at:
                        return created_at
            except Exception as e:
                print(f"  • HTML parsing failed, trying API...")
            
            # SECONDARY METHOD: Try GraphQL with timeout and retry
            created_at = self._try_graphql_creation_date()
            if created_at:
                return created_at
            
            print("  • All methods exhausted")
            return None
            
        except Exception as e:
            print(f"  • Error: {str(e)[:100]}")
            return None

    def _parse_created_date_from_html(self, html):
        """Extract creation date from profile page HTML."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Look for "Joined on" text in various elements
            for element in soup.find_all(["span", "p", "div"]):
                text = element.get_text(strip=True)
                if "Joined" in text and ("2023" in text or "2024" in text or "2025" in text or "2026" in text):
                    # Extract date portion
                    import re
                    match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}', text)
                    if match:
                        return match.group(0)
                    return text
            
            # Try to find in script tags with JSON data
            scripts = soup.find_all("script", {"type": "application/json"})
            for script in scripts:
                try:
                    if not script.string:
                        continue
                    data = json.loads(script.string)
                    created_at = self._find_in_json(data, "createdAt")
                    if created_at:
                        return created_at
                except:
                    pass
            
            # Look for data attributes
            for elem in soup.find_all(attrs={"data-created-at": True}):
                return elem.get("data-created-at")
            
            return None
        except Exception as e:
            return None

    def _find_in_json(self, obj, key, depth=0):
        """Recursively find value in JSON object."""
        if depth > 10:  # Prevent infinite recursion
            return None
            
        if isinstance(obj, dict):
            if key in obj:
                return obj[key]
            for v in obj.values():
                result = self._find_in_json(v, key, depth + 1)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = self._find_in_json(item, key, depth + 1)
                if result:
                    return result
        return None

    def _try_graphql_creation_date(self, max_retries=2):
        """Try to fetch creation date via GraphQL API with retry logic."""
        try:
            import requests
            
            graphql_query = {
                "query": f"""
                query {{
                  user(login: "{self.username}") {{
                    createdAt
                    login
                  }}
                }}
                """
            }
            
            for attempt in range(max_retries):
                try:
                    # Use shorter timeout for GraphQL
                    resp = requests.post(
                        "https://api.github.com/graphql",
                        json=graphql_query,
                        headers=self.HEADERS,
                        timeout=5,
                        allow_redirects=False
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("data") and data["data"].get("user"):
                            created_at = data["data"]["user"].get("createdAt")
                            if created_at:
                                return created_at
                    
                    # Stop retrying if not a timeout/connection error
                    if resp.status_code not in [408, 429, 503, 504]:
                        return None
                        
                except (requests.ConnectionError, requests.Timeout, requests.ConnectTimeout):
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                except Exception:
                    return None
            
            return None
        except Exception:
            return None

    def get_primary_email(self):
        """Try to fetch the account's primary email from settings pages."""
        try:
            resp = self.get("/settings/emails")
            if resp.status_code != 200:
                return None
            html = resp.text
            # Find any email addresses in the page
            import re
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', html)
            # Prefer non-github.com emails and unique list
            seen = []
            for e in emails:
                if e.lower().endswith("@github.com"):
                    continue
                if e not in seen:
                    seen.append(e)
            if seen:
                return seen[0]
            # Fallback: look for an email input value
            soup = BeautifulSoup(html, "html.parser")
            inp = soup.find("input", {"type": "email"})
            if inp and inp.get("value"):
                return inp.get("value")
            return None
        except Exception:
            return None

    def check_account_age(self, min_days=3):
        """Check if account is at least min_days old."""
        try:
            created_at_str = self.get_account_created_date()
            
            if not created_at_str:
                print(f"  ⚠ Cannot fetch account creation date - assuming account is old enough")
                # If we can't verify, allow it through (better UX)
                return True
            
            # Parse various datetime formats
            created_at = None
            date_str = str(created_at_str).strip()
            
            # Try ISO 8601 format first (e.g., "2024-01-15T10:30:00Z")
            if "T" in date_str:
                try:
                    created_at = datetime.fromisoformat(
                        date_str.replace("Z", "+00:00")
                    )
                except:
                    pass
            
            # Try common date formats
            if not created_at:
                date_formats = [
                    "%b %d, %Y",           # "Jan 15, 2024"
                    "%B %d, %Y",           # "January 15, 2024"
                    "%Y-%m-%d %H:%M:%S",   # "2024-01-15 10:30:00"
                    "%Y-%m-%d",            # "2024-01-15"
                    "%d/%m/%Y",            # "15/01/2024"
                    "%m/%d/%Y",            # "01/15/2024"
                ]
                
                for fmt in date_formats:
                    try:
                        created_at = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
            
            # Extract date from "Joined on Jan 15, 2024" format
            if not created_at:
                import re
                match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{4})', date_str)
                if match:
                    try:
                        month_str = match.group(1)
                        day = match.group(2)
                        year = match.group(3)
                        created_at = datetime.strptime(f"{month_str} {day}, {year}", "%b %d, %Y")
                    except:
                        pass
            
            if not created_at:
                print(f"  ⚠ Cannot parse date format: {date_str[:50]}")
                print(f"  ⚠ Assuming account is old enough (continuing...)")
                return True
            
            # Calculate account age
            try:
                now = datetime.now(created_at.tzinfo) if created_at.tzinfo else datetime.utcnow()
            except:
                now = datetime.utcnow()
            
            account_age = now - created_at
            days_old = account_age.days
            
            print(f"  • Account created: {created_at.strftime('%Y-%m-%d')}")
            print(f"  • Account age: {days_old} days")
            
            if days_old >= min_days:
                print(f"  ✓ Account meets minimum age requirement ({min_days} days)")
                return True
            else:
                days_needed = min_days - days_old
                print(f"  ✗ Account is too new! Need {days_needed} more day(s)")
                return False
                
        except Exception as e:
            print(f"  ⚠ Error checking account age (continuing anyway...): {str(e)[:50]}")
            # Allow through on error for better UX
            return True

    # ── Two-Factor Authentication ───────────────────────────────

    def check_2fa_enabled(self):
        """Check if 2FA is enabled on the account."""
        try:
            resp = self.get("/settings/security")
            if "/login" in resp.url:
                print("  x Session expired")
                return None
            
            # Check if 2FA is disabled
            if "Two-factor authentication is not enabled yet" in resp.text:
                print("  • 2FA is not enabled yet")
                return False
            elif "Two-factor authentication is enabled" in resp.text or \
                 "Disable two-factor authentication" in resp.text or \
                 "two-factor-enabled" in resp.text:
                print("  ✓ 2FA is already enabled")
                return True
            else:
                # HTML check - if we find disable button, 2FA is enabled
                return "Two-factor authentication is not enabled yet" not in resp.text
                
        except Exception as e:
            print(f"  ⚠ Error checking 2FA status: {str(e)[:50]}")
            return None

    def enable_2fa_and_get_secrets(self):
        """Enable 2FA on the account and return secret + recovery codes."""
        try:
            import pyotp
            
            # Step 1: Get 2FA setup intro page
            print("  • Accessing 2FA setup page...")
            resp = self.get("/settings/two_factor_authentication/setup/intro", timeout=10)
            if resp.status_code != 200 or "/login" in resp.url:
                print("  x Cannot access 2FA setup page")
                return None
            
            time.sleep(random.uniform(2.0, 4.0))
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Extract all forms on the page
            all_forms = soup.find_all("form")
            if not all_forms:
                print("  x No forms found on page")
                return None
            
            print(f"  • Found {len(all_forms)} forms on page")
            
            # Find initiate form - match on action URL containing 'initiate'
            init_data = None
            for form in all_forms:
                action = form.get("action", "").lower()
                if "initiate" in action:
                    init_data = {}
                    for inp in form.find_all("input"):
                        name = inp.get("name")
                        if name:
                            init_data[name] = inp.get("value", "")
                    if init_data:
                        print("  • Found initiate form")
                        break
            
            if not init_data:
                print("  x Initiate form not found")
                form_actions = [f.get('action', 'unknown')[:60] for f in all_forms]
                print(f"  Available forms: {form_actions}")
                return None
            
            init_data["type"] = "app"
            
            # Find verify form (app type) - match on action URL containing 'verify'
            verify_data = None
            for form in all_forms:
                action = form.get("action", "").lower()
                if "verify" in action:
                    type_inp = form.find("input", {"name": "type"})
                    if type_inp and type_inp.get("value") == "app":
                        verify_data = {}
                        for inp in form.find_all("input"):
                            name = inp.get("name")
                            if name:
                                verify_data[name] = inp.get("value", "")
                        if verify_data:
                            print("  • Found verify form")
                        break
            
            if not verify_data:
                print("  x Verify form not found")
                return None
            
            # Find enable form - match on action URL containing 'enable'
            enable_data = None
            for form in all_forms:
                action = form.get("action", "").lower()
                if "enable" in action:
                    enable_data = {}
                    for inp in form.find_all("input"):
                        name = inp.get("name")
                        if name:
                            enable_data[name] = inp.get("value", "")
                    if enable_data:
                        print("  • Found enable form")
                    break
            
            # Find recovery download form - match on action URL containing 'recovery'
            dl_data = None
            for form in all_forms:
                action = form.get("action", "").lower()
                if "recovery" in action:
                    dl_data = {}
                    for inp in form.find_all("input"):
                        name = inp.get("name")
                        if name:
                            dl_data[name] = inp.get("value", "")
                    if dl_data:
                        print("  • Found recovery form")
                    break
            
            json_headers = {
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": self.BASE,
                "Referer": f"{self.BASE}/settings/two_factor_authentication/setup/intro",
            }
            
            # Step 2: POST initiate to get TOTP secret
            print("  • Requesting TOTP secret...")
            time.sleep(random.uniform(3.0, 6.0))
            resp2 = self.session.post(
                f"{self.BASE}/settings/two_factor_authentication/setup/initiate",
                data=init_data,
                headers={**self.HEADERS, **json_headers},
                timeout=10
            )
            
            if resp2.status_code != 200:
                print(f"  x Initiate failed: {resp2.status_code}")
                return None
            
            try:
                payload = resp2.json()
            except Exception as e:
                print(f"  x Invalid initiate response: {str(e)[:50]}")
                return None
            
            secret = payload.get("mashed_secret", "")
            recovery = payload.get("formatted_recovery_codes", [])
            
            if not secret:
                print("  x No TOTP secret returned")
                return None
            
            print(f"  ✓ TOTP secret obtained")
            
            # Step 3: Generate TOTP code and verify
            print("  • Generating and verifying TOTP code...")
            time.sleep(random.uniform(2.0, 4.0))
            totp = pyotp.TOTP(secret)
            code = totp.now()
            verify_data["otp"] = code
            
            resp3 = self.session.post(
                f"{self.BASE}/settings/two_factor_authentication/setup/verify",
                data=verify_data,
                headers={**self.HEADERS, **json_headers},
                timeout=10
            )
            
            if resp3.status_code != 200:
                print(f"  x Verify failed: {resp3.status_code}")
                return None
            
            print(f"  ✓ TOTP verified")
            
            # Step 4: Download recovery codes
            print("  • Finalizing setup...")
            time.sleep(random.uniform(1.0, 2.0))
            if dl_data:
                self.session.post(
                    f"{self.BASE}/settings/two_factor_authentication/setup/recovery_download",
                    data=dl_data,
                    headers={
                        **self.HEADERS,
                        "Accept": "text/plain,*/*",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Origin": self.BASE,
                        "Referer": f"{self.BASE}/settings/two_factor_authentication/setup/intro",
                    },
                    timeout=10
                )
            
            # Step 5: Enable 2FA
            time.sleep(random.uniform(1.0, 2.0))
            if enable_data:
                enable_data["type"] = "app"
                resp5 = self.session.post(
                    f"{self.BASE}/settings/two_factor_authentication/setup/enable",
                    data=enable_data,
                    headers={**self.HEADERS, **json_headers},
                    timeout=10
                )
                
                if resp5.status_code != 200:
                    print(f"  x Enable failed: {resp5.status_code}")
                    return None
            
            print("  ✓ 2FA enabled successfully")
            return {
                "secret": secret,
                "recovery_codes": recovery
            }
            
        except ImportError:
            print("  x pyotp module not found - install with: pip install pyotp")
            return None
        except Exception as e:
            print(f"  x 2FA setup error: {str(e)[:100]}")
            import traceback
            traceback.print_exc()
            return None

    def save_account_details(self, account_info):
        """Save account details to a file."""
        try:
            filename = f"github_account_{self.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            details = {
                "username": self.username,
                "timestamp": datetime.now().isoformat(),
                "2fa_secret": account_info.get("secret", ""),
                "recovery_codes": account_info.get("recovery_codes", []),
                "account_check_date": datetime.now().isoformat(),
            }
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(details, f, ensure_ascii=False, indent=2)
            
            print(f"  ✓ Account details saved: {filename}")
            print(f"    - Username: {self.username}")
            print(f"    - 2FA Secret: {account_info.get('secret', 'N/A')}")
            print(f"    - Recovery Codes: {len(account_info.get('recovery_codes', []))}")
            
            return filename
            
        except Exception as e:
            print(f"  x Error saving account details: {str(e)[:100]}")
            return None
