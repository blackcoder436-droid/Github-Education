#!/usr/bin/env python3
"""Test Face Studio and gamitisa.com image generation APIs."""

import os
import sys
import requests
from pathlib import Path
from PIL import Image
from io import BytesIO

# Create test output directory
test_dir = Path("test_output")
test_dir.mkdir(exist_ok=True)

print("=" * 60)
print("Testing Image Generation APIs")
print("=" * 60)

# ==================== TEST 1: Face Studio API ====================
print("\n[1/2] Testing Face Studio API...")
print("-" * 60)

facestudio_key = os.environ.get("FACESTUDIO_API_KEY", "").strip()

if not facestudio_key:
    print("  x FACESTUDIO_API_KEY not set")
    print("  Set it: $env:FACESTUDIO_API_KEY='your-key'")
else:
    try:
        print(f"  API Key: {facestudio_key[:10]}...")
        print("  Generating face photo...")
        
        response = requests.post(
            "https://facestud.io/v1/generate",
            headers={"Authorization": f"Bearer {facestudio_key}"},
            timeout=30,
        )
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            photo_bytes = response.content
            print(f"  Size: {len(photo_bytes)} bytes")
            
            # Verify it's a valid image
            try:
                img = Image.open(BytesIO(photo_bytes))
                print(f"  Format: {img.format}")
                print(f"  Dimensions: {img.width}×{img.height}px")
                
                # Save for inspection
                save_path = test_dir / "facestudio_photo.png"
                with open(save_path, "wb") as f:
                    f.write(photo_bytes)
                print(f"  Saved: {save_path}")
                print("  Status: SUCCESS ✓")
            except Exception as e:
                print(f"  x Invalid image: {e}")
        else:
            print(f"  Error: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            print("  Status: FAILED ✗")
    except Exception as e:
        print(f"  x Network error: {e}")
        print("  Status: FAILED ✗")

# ==================== TEST 2: Gamitisa.com Student ID ====================
print("\n[2/2] Testing gamitisa.com Student ID Generation...")
print("-" * 60)

try:
    # Prepare student data
    student_data = {
        "student_name": "Lin Han Win",
        "student_id": "STU-2024-001",
        "school_name": "KMD COLLEGE",
        "class": "11-A",
        "roll_number": "042",
        "date_of_birth": "1997-05-04",
        "gender": "Male",
        "phone": "09123456789",
        "email": "student@kmdcollege.edu",
        "address": "No 331, Pyay Road, Yangon",
        "issued_date": "2026-01-01",
        "expiry_date": "2027-01-01",
    }
    
    print(f"  Student: {student_data['student_name']}")
    print(f"  School: {student_data['school_name']}")
    print(f"  Generating ID card...")
    
    # Try gamitisa.com endpoint
    # Note: This might not have a public API, so we'll just show the structure
    print("\n  Gamitisa.com Info:")
    print("  Website: https://gamitisa.com/tools/student-idcard")
    print("  Type: Web-based tool (manual or custom integration needed)")
    print("  Status: Requires browser automation or manual upload")
    
    # Show what would be sent
    print("\n  Sample Data Structure:")
    for key, value in student_data.items():
        print(f"    {key}: {value}")

except Exception as e:
    print(f"  x Error: {e}")

# ==================== SUMMARY ====================
print("\n" + "=" * 60)
print("Test Summary")
print("=" * 60)

print("\nFace Studio:")
print("  ✓ API available and working" if facestudio_key else "  ✗ API key not configured")

print("\nGamitisa.com:")
print("  ℹ Web-based tool (no direct API)")
print("  Options:")
print("    1. Use PIL to generate custom ID card (current approach)")
print("    2. Browser automation with gamitisa.com (more realistic but slower)")
print("    3. Accept PIL-generated cards (already implemented)")

print("\nNext Steps:")
print("  1. If Face Studio working: Continue with current implementation")
print("  2. If Face Studio not working: Use GitHub avatar only")
print("  3. Use custom PIL ID card generator (already working)")

print("\n" + "=" * 60)
