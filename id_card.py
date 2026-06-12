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
    width=500,
    height=700,
):
    """
    Generate professional student ID card image.
    
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

    # Create card background (white)
    card = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(card)

    # Try to use better fonts
    try:
        title_font = ImageFont.truetype("arial.ttf", 28)
        heading_font = ImageFont.truetype("arial.ttf", 18)
        name_font = ImageFont.truetype("arial.ttf", 20)
        label_font = ImageFont.truetype("arial.ttf", 14)
        small_font = ImageFont.truetype("arial.ttf", 12)
    except:
        title_font = ImageFont.load_default()
        heading_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # === TOP HEADER SECTION ===
    draw.rectangle([(0, 0), (width, 80)], fill=(15, 75, 150))  # Dark blue header
    draw.text((width // 2, 25), school_name, fill=(255, 255, 255), font=title_font, anchor="mm")
    draw.text((width // 2, 60), "STUDENT IDENTIFICATION CARD", fill=(200, 220, 255), font=label_font, anchor="mm")

    # === PHOTO SECTION ===
    photo_x = 30
    photo_y = 110
    photo_size = 160

    # Placeholder or actual photo
    if photo_bytes:
        try:
            photo = Image.open(io.BytesIO(photo_bytes))
            photo = photo.convert("RGB")
            photo.thumbnail((photo_size, photo_size), Image.Resampling.LANCZOS)
            # Center photo
            paste_x = photo_x + (photo_size - photo.width) // 2
            paste_y = photo_y + (photo_size - photo.height) // 2
            card.paste(photo, (paste_x, paste_y))
        except Exception as e:
            # Gray placeholder if photo fails
            draw.rectangle([(photo_x, photo_y), (photo_x + photo_size, photo_y + photo_size)], fill=(220, 220, 220))
    else:
        # Gray placeholder
        draw.rectangle([(photo_x, photo_y), (photo_x + photo_size, photo_y + photo_size)], fill=(220, 220, 220))

    # Photo border
    draw.rectangle([(photo_x - 2, photo_y - 2), (photo_x + photo_size + 2, photo_y + photo_size + 2)], outline=(0, 0, 0), width=2)

    # === INFO SECTION (right of photo) ===
    info_x = photo_x + photo_size + 40
    info_y = photo_y

    # Name (prominent)
    draw.text((info_x, info_y), "Name:", fill=(15, 75, 150), font=label_font)
    draw.text((info_x, info_y + 28), name, fill=(0, 0, 0), font=name_font)
    
    info_y += 75

    # Student ID / Roll
    draw.text((info_x, info_y), "Roll No:", fill=(15, 75, 150), font=label_font)
    draw.text((info_x, info_y + 28), f"{roll_num:06d}", fill=(0, 0, 0), font=name_font)

    info_y += 75

    # Class
    draw.text((info_x, info_y), "Class:", fill=(15, 75, 150), font=label_font)
    draw.text((info_x, info_y + 28), f"{class_num}", fill=(0, 0, 0), font=name_font)

    # === BOTTOM SECTION ===
    y_offset = photo_y + photo_size + 30

    # Separator line
    draw.rectangle([(20, y_offset), (width - 20, y_offset + 2)], fill=(15, 75, 150))

    y_offset += 20

    # Details section (2 columns)
    left_x = 30
    right_x = width // 2 + 20

    # Left column
    draw.text((left_x, y_offset), "Date of Birth:", fill=(15, 75, 150), font=label_font)
    draw.text((left_x, y_offset + 25), dob, fill=(0, 0, 0), font=small_font)

    draw.text((left_x, y_offset + 55), "Issue Year:", fill=(15, 75, 150), font=label_font)
    draw.text((left_x, y_offset + 80), str(issue_year), fill=(0, 0, 0), font=small_font)

    # Right column
    draw.text((right_x, y_offset), "Address:", fill=(15, 75, 150), font=label_font)
    # Wrap address if too long
    addr_lines = [address[i:i+30] for i in range(0, len(address), 30)]
    addr_y = y_offset + 25
    for line in addr_lines:
        draw.text((right_x, addr_y), line, fill=(0, 0, 0), font=small_font)
        addr_y += 20

    draw.text((right_x, y_offset + 55), "Mobile:", fill=(15, 75, 150), font=label_font)
    draw.text((right_x, y_offset + 80), mobile, fill=(0, 0, 0), font=small_font)

    # === FOOTER ===
    y_offset += 130
    draw.rectangle([(0, y_offset), (width, height)], fill=(240, 245, 250))
    draw.line([(0, y_offset), (width, y_offset)], fill=(15, 75, 150), width=2)
    
    draw.text((width // 2, y_offset + 15), "Valid for Educational Purposes", fill=(100, 100, 100), font=small_font, anchor="mm")
    draw.text((width // 2, y_offset + 40), f"Issued: {issue_year}", fill=(100, 100, 100), font=small_font, anchor="mm")

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
