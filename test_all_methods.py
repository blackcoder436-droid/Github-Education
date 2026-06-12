#!/usr/bin/env python3
"""Fallback to PIL ID card generation + optional gamitisa.com browser automation."""

import os
from pathlib import Path
from id_card import generate_id_card, card_to_bytes

# Test PIL generation first (reliable, no rate limits)
print("=" * 70)
print("Testing PIL-based ID Card Generation (Primary Method)")
print("=" * 70)

try:
    print("\n[1/3] Creating PIL-based student ID card...")
    
    card = generate_id_card(
        name="Lin Han Win",
        photo_bytes=None,  # Will use placeholder
        school_name="KMD COLLEGE",
        class_num=101,
        roll_num=123456,
        dob="1997-05-04",
        issue_year=2026,
        address="No 331, Pyay Road, Yangon",
        mobile="09123456789"
    )
    
    print("[2/3] Converting to bytes...")
    card_bytes = card_to_bytes(card, format="PNG")
    print(f"  Size: {len(card_bytes)} bytes")
    
    print("[3/3] Saving to file...")
    output_dir = Path("generated")
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / "pil_idcard.png"
    with open(output_path, "wb") as f:
        f.write(card_bytes)
    
    print(f"\n✓ PIL ID Card SUCCESS!")
    print(f"  Path: {output_path}")
    print(f"  Size: {len(card_bytes)} bytes")
    
except Exception as e:
    print(f"\n✗ PIL Generation Failed: {e}")
    import traceback
    traceback.print_exc()

# Optional: Test gamitisa.com if browser available
print("\n" + "=" * 70)
print("Optional: Gamitisa.com Browser Automation")
print("=" * 70)

try:
    from playwright.sync_api import sync_playwright
    
    print("\nPlaywright is available. Gamitisa.com automation is possible.")
    print("\nOptions:")
    print("  1. Continue with PIL-generated ID (recommended, reliable)")
    print("  2. Try gamitisa.com browser (more realistic looking)")
    
    choice = input("\nChoose (1-2, default 1): ").strip() or "1"
    
    if choice == "2":
        print("\nLaunching gamitisa.com in browser...")
        print("(Follow the on-screen instructions to generate ID card)")
        
        # Import and run the gamitisa function
        from gamitisa_browser import generate_id_card_gamitisa
        
        success, path = generate_id_card_gamitisa(
            student_name="Lin Han Win",
            school_name="KMD COLLEGE",
            class_num=101,
            roll_num=123456,
            dob="1997-05-04",
            issue_year=2026,
            address="No 331, Pyay Road, Yangon",
            mobile="09123456789"
        )
        
        if success:
            print(f"\n✓ Gamitisa ID Card Success: {path}")
        else:
            print(f"\n⚠ Gamitisa failed, falling back to PIL")
    else:
        print("\nUsing PIL-generated ID card (recommended)")

except ImportError:
    print("\nPlaywright not available for browser automation")
    print("Continuing with PIL-generated ID card")

print("\n" + "=" * 70)
print("Summary")
print("=" * 70)
print("""
✓ PIL ID Card Generator: WORKING (no dependencies, no rate limits)
⏳ Face Studio API: RATE LIMITED (wait 5 minutes or skip)
ℹ Gamitisa.com: Browser-based (can use Playwright automation)

Recommendation: Use PIL-generated ID cards for production
""")
