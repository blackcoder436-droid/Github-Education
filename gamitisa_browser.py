#!/usr/bin/env python3
"""Generate student ID card using gamitisa.com browser automation."""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

def generate_id_card_gamitisa(
    student_name,
    school_name,
    class_num,
    roll_num,
    dob,
    issue_year,
    address,
    mobile,
    photo_path=None,
):
    """
    Generate student ID card using gamitisa.com web tool via Playwright.
    
    Args:
        student_name: Full name (e.g., "Lin Han")
        school_name: School name (e.g., "KMD COLLEGE")
        class_num: Class number (e.g., 123)
        roll_num: Roll number (e.g., 456789)
        dob: Date of birth (e.g., "1997-05-04")
        issue_year: Year issued (e.g., 2026)
        address: Address
        mobile: Phone number
        photo_path: Optional path to student photo
    
    Returns:
        tuple: (success: bool, image_path: Path or None)
    """
    
    print("\n" + "=" * 70)
    print("Generating ID Card via gamitisa.com")
    print("=" * 70)
    
    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)
    
    print(f"Student: {student_name}")
    print(f"School: {school_name}")
    print(f"Class: {class_num}, Roll: {roll_num}")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=False)  # Show browser for debugging
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            page = context.new_page()
            
            print("\n[1/5] Opening gamitisa.com...")
            page.goto("https://gamitisa.com/tools/student-idcard", timeout=30000)
            page.wait_for_load_state("networkidle", timeout=10000)
            
            # Wait for form to be visible
            print("[2/5] Waiting for form elements...")
            page.wait_for_selector("input[name*='name'], input[name*='school'], input[name*='class']", timeout=10000)
            
            print("[3/5] Filling form...")
            
            # Find and fill form fields (gamitisa.com structure may vary)
            # Try multiple possible selectors
            selectors_to_try = {
                "student_name": [
                    "input[name*='name']",
                    "input[placeholder*='name']",
                    "input[placeholder*='Name']",
                    "#student_name",
                    "input[type='text']:nth-of-type(1)",
                ],
                "school_name": [
                    "input[name*='school']",
                    "input[placeholder*='school']",
                    "input[placeholder*='School']",
                    "#school_name",
                ],
                "class_num": [
                    "input[name*='class']",
                    "input[placeholder*='class']",
                    "input[placeholder*='Class']",
                    "#class",
                ],
                "roll_num": [
                    "input[name*='roll']",
                    "input[placeholder*='roll']",
                    "input[placeholder*='Roll']",
                    "#roll",
                ],
            }
            
            # Fill student name
            filled_count = 0
            for selector in selectors_to_try["student_name"]:
                try:
                    input_elem = page.query_selector(selector)
                    if input_elem and input_elem.is_visible():
                        input_elem.fill(student_name)
                        print(f"  ✓ Filled student name: {selector}")
                        filled_count += 1
                        break
                except:
                    pass
            
            if filled_count == 0:
                print(f"  ⚠ Could not find student name field")
            
            # Fill school name
            for selector in selectors_to_try["school_name"]:
                try:
                    input_elem = page.query_selector(selector)
                    if input_elem and input_elem.is_visible():
                        input_elem.fill(school_name)
                        print(f"  ✓ Filled school name: {selector}")
                        filled_count += 1
                        break
                except:
                    pass
            
            # Fill class
            for selector in selectors_to_try["class_num"]:
                try:
                    input_elem = page.query_selector(selector)
                    if input_elem and input_elem.is_visible():
                        input_elem.fill(str(class_num))
                        print(f"  ✓ Filled class: {selector}")
                        filled_count += 1
                        break
                except:
                    pass
            
            # Fill roll number
            for selector in selectors_to_try["roll_num"]:
                try:
                    input_elem = page.query_selector(selector)
                    if input_elem and input_elem.is_visible():
                        input_elem.fill(str(roll_num))
                        print(f"  ✓ Filled roll: {selector}")
                        filled_count += 1
                        break
                except:
                    pass
            
            # Try to upload photo if provided
            if photo_path and Path(photo_path).exists():
                print(f"[4/5] Uploading photo...")
                try:
                    file_input = page.query_selector("input[type='file']")
                    if file_input:
                        file_input.set_input_files(str(photo_path))
                        print(f"  ✓ Photo uploaded: {photo_path}")
                        time.sleep(2)
                except Exception as e:
                    print(f"  ⚠ Could not upload photo: {e}")
            
            # Look for generate/submit button
            print("[5/5] Submitting form...")
            
            button_selectors = [
                "button:has-text('Generate')",
                "button:has-text('Submit')",
                "button:has-text('Create')",
                "button[type='submit']",
                "button:nth-of-type(1)",
            ]
            
            for selector in button_selectors:
                try:
                    button = page.query_selector(selector)
                    if button and button.is_visible():
                        button.click()
                        print(f"  ✓ Clicked button: {selector}")
                        page.wait_for_timeout(3000)
                        break
                except:
                    pass
            
            # Wait and try to capture screenshot or find download link
            print("\n[Result] Waiting for generation...")
            page.wait_for_timeout(5000)
            
            # Take screenshot of result
            screenshot_path = output_dir / "gamitisa_result.png"
            page.screenshot(path=str(screenshot_path))
            print(f"  ✓ Screenshot saved: {screenshot_path}")
            
            # Try to find and download the generated image
            try:
                # Look for img tag with the generated ID
                img_selector = "img[src*='data:image'], img[src*='blob:'], img.result, img#preview"
                img_elem = page.query_selector(img_selector)
                if img_elem:
                    # Get image src
                    src = img_elem.get_attribute("src")
                    print(f"  ✓ Found generated image")
                    
                    # If it's a data URL, extract and save
                    if src and src.startswith("data:image"):
                        import base64
                        # Parse data URL
                        if "," in src:
                            header, data = src.split(",", 1)
                            img_bytes = base64.b64decode(data)
                            output_path = output_dir / "gamitisa_idcard.png"
                            with open(output_path, "wb") as f:
                                f.write(img_bytes)
                            print(f"  ✓ ID card saved: {output_path}")
                            return True, output_path
            except Exception as e:
                print(f"  ⚠ Could not extract image: {e}")
            
            print("\n  Note: Please manually download or check the screenshot")
            print(f"  Screenshot: {screenshot_path}")
            
            # Keep browser open for user to check
            print("\n  Browser is open - examine the generated ID card")
            print("  Press Enter to continue...")
            input()
            
            return False, None
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
            return False, None
        
        finally:
            try:
                browser.close()
            except:
                pass


if __name__ == "__main__":
    # Test with sample data
    success, path = generate_id_card_gamitisa(
        student_name="Lin Han Win",
        school_name="KMD COLLEGE",
        class_num=101,
        roll_num=123456,
        dob="1997-05-04",
        issue_year=2026,
        address="No 331, Pyay Road, Yangon",
        mobile="09123456789",
    )
    
    if success:
        print(f"\n✓ Success: {path}")
    else:
        print(f"\n⚠ Manual intervention needed")
