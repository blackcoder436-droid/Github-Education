"""Generate student ID card image using PIL."""

import io
import random
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import requests


def generate_random_dob(min_age=20, max_age=30):
    """Generate random date of birth within age range."""
    today = datetime.now()
    max_dob = today - timedelta(days=min_age * 365)
    min_dob = today - timedelta(days=max_age * 365)
    random_dob = min_dob + timedelta(days=random.randint(0, (max_dob - min_dob).days))
    return random_dob.strftime("%Y-%m-%d")


def generate_myanmar_phone():
    """Generate random Myanmar phone number."""
    prefixes = ["09", "08"]
    prefix = random.choice(prefixes)
    number = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return prefix + number


def generate_id_card(
    name,
    photo_bytes,
    logo_bytes=None,
    school_name="KMD COLLEGE",
    class_num=None,
    roll_num=None,
    dob=None,
    issue_year=2026,
    address=None,
    mobile=None,
    width=400,
    height=600,
):
    """
    Generate student ID card image.
    
    Args:
        name: Full name (e.g., "Min Ko")
        photo_bytes: Photo image bytes (JPEG/PNG)
        logo_bytes: Logo image bytes (optional)
        school_name: School name
        class_num: Class number (random 3-digit if None)
        roll_num: Roll number (random 6-digit if None)
        dob: Date of birth (random if None)
        issue_year: Year issued
        address: Address
        mobile: Mobile number (random Myanmar if None)
        width: Card width in pixels
        height: Card height in pixels
    
    Returns:
        PIL Image object
    """
    class_num = class_num or random.randint(100, 999)
    roll_num = roll_num or random.randint(100000, 999999)
    dob = dob or generate_random_dob()
    mobile = mobile or generate_myanmar_phone()
    address = address or "Yangon, Myanmar"

    # Create card background
    card = Image.new("RGB", (width, height), color=(240, 240, 245))
    draw = ImageDraw.Draw(card)

    # Try to use basic fonts (fallback to default)
    try:
        title_font = ImageFont.truetype("arial.ttf", 20)
        name_font = ImageFont.truetype("arial.ttf", 16)
        label_font = ImageFont.truetype("arial.ttf", 12)
        small_font = ImageFont.truetype("arial.ttf", 10)
    except:
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Draw header with school name
    draw.rectangle([(0, 0), (width, 60)], fill=(25, 118, 210))  # Blue header
    draw.text((width // 2, 20), school_name, fill=(255, 255, 255), font=title_font, anchor="mm")

    y_offset = 80

    # Logo (if provided)
    if logo_bytes:
        try:
            logo = Image.open(io.BytesIO(logo_bytes))
            logo.thumbnail((60, 60), Image.Resampling.LANCZOS)
            card.paste(logo, (20, y_offset))
        except:
            pass

    # Photo
    if photo_bytes:
        try:
            photo = Image.open(io.BytesIO(photo_bytes))
            photo.thumbnail((120, 150), Image.Resampling.LANCZOS)
            photo_x = (width - 120) // 2
            card.paste(photo, (photo_x, y_offset + 10))
        except:
            pass

    y_offset += 170

    # Student info
    draw.text((20, y_offset), f"Name:", fill=(0, 0, 0), font=label_font)
    draw.text((100, y_offset), name, fill=(0, 0, 0), font=name_font)
    y_offset += 30

    draw.text((20, y_offset), f"Class:", fill=(0, 0, 0), font=label_font)
    draw.text((100, y_offset), f"Class {class_num}", fill=(0, 0, 0), font=name_font)
    y_offset += 30

    draw.text((20, y_offset), f"Roll:", fill=(0, 0, 0), font=label_font)
    draw.text((100, y_offset), str(roll_num), fill=(0, 0, 0), font=name_font)
    y_offset += 30

    draw.text((20, y_offset), f"Date of Birth:", fill=(0, 0, 0), font=label_font)
    draw.text((140, y_offset), dob, fill=(0, 0, 0), font=name_font)
    y_offset += 30

    draw.text((20, y_offset), f"Year:", fill=(0, 0, 0), font=label_font)
    draw.text((100, y_offset), str(issue_year), fill=(0, 0, 0), font=name_font)
    y_offset += 40

    # Footer section
    draw.rectangle([(0, y_offset), (width, height)], fill=(25, 118, 210))  # Blue footer
    draw.text((20, y_offset + 10), f"Address: {address}", fill=(255, 255, 255), font=small_font)
    draw.text((20, y_offset + 30), f"Mobile: {mobile}", fill=(255, 255, 255), font=small_font)

    return card


def card_to_bytes(card_image, format="PNG"):
    """Convert PIL Image to bytes."""
    buf = io.BytesIO()
    card_image.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


def card_to_data_url(card_image, format="PNG"):
    """Convert PIL Image to data URL."""
    import base64
    card_bytes = card_to_bytes(card_image, format=format)
    b64 = base64.b64encode(card_bytes).decode("utf-8")
    mime = f"image/{format.lower()}"
    return f"data:{mime};base64,{b64}"


if __name__ == "__main__":
    # Example usage
    print("ID card generator module loaded.")
