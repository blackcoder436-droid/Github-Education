"""Use Playwright to automate the education form and capture the real request.

Strategy:
1. Login via cookies transferred from requests session
2. Navigate to education form
3. Interact with step 1 form  
4. On step 2: use JS to select proof_type and set photo_proof
5. Intercept the form POST to see what the browser actually sends
6. Submit and check result
"""
import os, time, json
from dotenv import load_dotenv
from client import GitHubClient
from playwright.sync_api import sync_playwright
load_dotenv()

# First login with requests to get session cookies
print("Logging in via requests...")
c = GitHubClient()
ok = c.login(os.environ['GITHUB_USERNAME'], os.environ['GITHUB_PASSWORD'], totp_secret="SFDHLAA7MDH2S7TN")
print(f"Login: {ok}")

# Get cookies from requests session
cookies = []
for cookie in c.session.cookies:
    cookies.append({
        "name": cookie.name,
        "value": cookie.value,
        "domain": cookie.domain or ".github.com",
        "path": cookie.path or "/",
        "secure": cookie.secure,
    })
print(f"Got {len(cookies)} cookies")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    )
    
    # Set cookies
    context.add_cookies(cookies)
    
    page = context.new_page()
    
    # Set up request interception to capture POST data
    captured_requests = []
    def on_request(request):
        if request.method == "POST" and "developer_pack_applications" in request.url:
            captured_requests.append({
                "url": request.url,
                "method": request.method,
                "headers": dict(request.headers),
                "post_data": request.post_data,
            })
            print(f"\n  CAPTURED POST: {request.url}")
            print(f"  Content-Type: {request.headers.get('content-type', 'N/A')}")
            post = request.post_data or ""
            # Show proof-related parts
            for part in post.split("&"):
                if "proof" in part.lower() or "variant" in part.lower() or "submit" in part.lower():
                    print(f"  FIELD: {part[:200]}")
    
    page.on("request", on_request)
    
    # Navigate to education form
    print("\nNavigating to education form...")
    page.goto("https://github.com/settings/education/developer_pack_applications/new", timeout=30000)
    page.wait_for_load_state("networkidle")
    
    # Check if logged in
    title = page.title()
    print(f"Page title: {title}")
    
    # Check for turbo-frame
    frame = page.query_selector("turbo-frame#dev-pack-form")
    if not frame:
        print("ERROR: No turbo-frame found!")
        with open("pw_page.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        browser.close()
        exit(1)
    
    # Fill step 1: select Student radio
    print("\nStep 1: Selecting student...")
    student_radio = page.query_selector('input[value="student"]')
    if student_radio:
        student_radio.click()
        time.sleep(1)
    
    # Type school name and select from autocomplete
    print("Typing school name...")
    school_input = page.query_selector('#js-school-name-search')
    if school_input:
        school_input.fill("SKT")
        time.sleep(2)
        
        # Wait for autocomplete results
        page.wait_for_timeout(3000)
        
        # Look for autocomplete results
        results = page.query_selector_all('#js-school-name-list li, [role="option"]')
        print(f"Autocomplete results: {len(results)}")
        
        if results:
            # Click the first result that matches
            for r in results:
                text = r.inner_text()
                if "SKT" in text:
                    print(f"  Clicking: {text}")
                    r.click()
                    time.sleep(1)
                    break
    
    # Share location (set hidden fields)
    page.evaluate('''
        document.querySelector('#js-developer-pack-application-latitude-input').value = "16.8661";
        document.querySelector('#js-developer-pack-application-longitude-input').value = "96.1951";
        document.querySelector('#js-developer-pack-application-location-shared-input').value = "true";
    ''')
    
    # Wait for Continue button to be enabled
    page.wait_for_timeout(2000)
    
    continue_btn = page.query_selector('button[name="continue"]')
    if continue_btn:
        is_disabled = continue_btn.get_attribute("disabled")
        print(f"Continue button disabled: {is_disabled}")
        
        if is_disabled:
            # Try enabling it
            page.evaluate('document.querySelector(\'button[name="continue"]\').disabled = false')
        
        print("Clicking Continue...")
        continue_btn.click()
        page.wait_for_timeout(5000)
    else:
        print("ERROR: No continue button found!")
    
    # Check if step 2 appeared
    print("\nChecking for step 2 form...")
    proof_type_el = page.query_selector('input[name="dev_pack_form[proof_type]"]')
    photo_proof_el = page.query_selector('#photo_proof')
    
    if not proof_type_el:
        print("WARNING: proof_type input not found on page")
        with open("pw_step1_result.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        
        # Maybe turbo-stream update happened
        page.wait_for_timeout(3000)
        proof_type_el = page.query_selector('input[name="dev_pack_form[proof_type]"]')
        photo_proof_el = page.query_selector('#photo_proof')
        
        if not proof_type_el:
            print("Still no proof_type. Saving page and exiting.")
            with open("pw_no_step2.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            browser.close()
            exit(1)
    
    print(f"Step 2 form found! proof_type: {proof_type_el is not None}, photo_proof: {photo_proof_el is not None}")
    
    # Step 2: Select proof type via action-menu
    # Click the action-menu button to open dropdown
    print("\nOpening proof type dropdown...")
    menu_btn = page.query_selector('action-menu button[type="button"]')
    if menu_btn:
        menu_btn.click()
        page.wait_for_timeout(1000)
        
        # Click "2. Dated official/unofficial transcript"
        items = page.query_selector_all('action-menu button[role="menuitemradio"]')
        print(f"Menu items: {len(items)}")
        for item in items:
            val = item.get_attribute("data-value")
            if val and "official" in val.lower():
                print(f"  Clicking: {val}")
                item.click()
                page.wait_for_timeout(1000)
                break
    
    # Check what proof_type value was set
    proof_val = page.evaluate('document.querySelector(\'input[name="dev_pack_form[proof_type]"]\').value')
    print(f"proof_type value after selection: {proof_val!r}")
    
    # Set photo_proof value (mock webcam capture)
    print("\nSetting photo_proof...")
    page.evaluate('''
        var photoInput = document.getElementById("photo_proof");
        if (photoInput) {
            photoInput.value = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDABsSFBcUERsXFhceHBsgKEIrKCUlKFE6PTBCYFVlZF9VXVtq";
        }
    ''')
    
    photo_val = page.evaluate('document.getElementById("photo_proof") ? document.getElementById("photo_proof").value : "NOT FOUND"')
    print(f"photo_proof value: {photo_val[:60]}...")
    
    # Set form_variant to upload_proof_form
    page.evaluate('''
        var variants = document.querySelectorAll('input[name="dev_pack_form[form_variant]"]');
        variants.forEach(v => v.value = "upload_proof_form");
    ''')
    
    # Click Submit button
    print("\nSubmitting form...")
    submit_btn = page.query_selector('button[name="submit"]')
    if submit_btn:
        is_disabled = submit_btn.get_attribute("disabled")
        print(f"Submit button disabled: {is_disabled}")
        if is_disabled:
            page.evaluate('document.querySelector(\'button[name="submit"]\').disabled = false')
        
        submit_btn.click()
        page.wait_for_timeout(5000)
    
    # Check result
    print(f"\nCaptured {len(captured_requests)} POST requests")
    for i, req in enumerate(captured_requests):
        print(f"\n--- Request {i} ---")
        print(f"URL: {req['url']}")
        print(f"Content-Type: {req['headers'].get('content-type', 'N/A')}")
        post = req.get('post_data', '') or ''
        # Show each field
        if post:
            for field in post.split("&"):
                decoded = field
                print(f"  {decoded[:200]}")
    
    # Save final page
    with open("pw_result.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    
    # Check for success/error
    content = page.content()
    if "cannot be reviewed" in content:
        print("\n*** FAILED: validation error ***")
        # Check proof_type value in result 
        proof_result = page.evaluate('''
            var inp = document.querySelector('input[name="dev_pack_form[proof_type]"]');
            inp ? inp.value : "NOT FOUND";
        ''')
        print(f"proof_type in result: {proof_result!r}")
    elif "Thank" in content or "submitted" in content.lower():
        print("\n*** SUCCESS! ***")
    else:
        print("\nUnknown result. Check pw_result.html")
    
    browser.close()

print("\nDone!")
