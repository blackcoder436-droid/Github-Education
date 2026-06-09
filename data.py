"""Random Myanmar profile data generator for GitHub Copilot applications."""

import random

MALE_FIRST_NAMES = [
    "Aung", "Maung", "Min", "Tun", "Than",
    "Wai", "Phyo", "Thiha", "Zaw", "Hein",
    "Kyaw", "Naing", "Htun", "Win", "Myo",
    "Zin", "Lin", "Htet", "Ye", "Soe",
]

FEMALE_FIRST_NAMES = [
    "Aye", "Nwe", "Thin", "Su", "Ei",
    "Hla", "May", "Khin", "Wai", "Phyu",
    "Hnin", "Myat", "Zin", "Nilar", "Thiri",
    "Su Su", "Yadanar", "Thandar", "Pwint", "Nang",
]

MALE_LAST_NAMES = [
    "Ko Ko", "Min Oo", "Lin Htet", "Zin Maung", "Win Naing",
    "Myat Thu", "Khan Zaw", "Han Win", "Kyaw Zin", "Htet Aung",
    "Thura", "Paing", "Lwin", "Oo", "Htike",
]

FEMALE_LAST_NAMES = [
    "Lwin", "Oo", "Htike", "Mon", "Nwe",
    "Thin Zar", "Mar Lar", "Phyo", "Wai Yan", "Myat Noe",
    "Thida", "San", "Yi", "Htet", "Cho",
]

TOWNSHIPS = [
    "Hlaing", "Kamayut", "Sanchaung", "Tamwe",
    "Thingangyun", "Mayangone", "Bahan", "Insein",
]

STREETS = [
    "Pyay Road", "Kabar Aye Pagoda Road", "Inya Road",
    "Bogyoke Street", "Anawrahta Road",
]

POSTAL_CODES = ["11041", "11052", "11061", "11071", "11211", "11221"]

BIOS = [
    "Developer based in Yangon",
    "Software engineer from Myanmar",
    "Full-stack developer",
    "Open source enthusiast",
    "CS student at University of Computer Studies",
]


def generate_profile():
    """Generate a randomized Myanmar profile."""
    gender = random.choice(["male", "female"])

    if gender == "male":
        first = random.choice(MALE_FIRST_NAMES)
        last = random.choice(MALE_LAST_NAMES)
    else:
        first = random.choice(FEMALE_FIRST_NAMES)
        last = random.choice(FEMALE_LAST_NAMES)

    full_name = f"{first} {last}"
    township = random.choice(TOWNSHIPS)
    street = random.choice(STREETS)
    house = random.randint(1, 220)
    postal = random.choice(POSTAL_CODES)

    return {
        "full_name": full_name,
        "first_name": first,
        "last_name": last,
        "bio": random.choice(BIOS),
        "location": "Yangon, Myanmar",
        "address1": f"No.{house}, {street}",
        "address2": f"{township}, Yangon",
        "city": "Yangon",
        "state": "Yangon",
        "postal_code": postal,
        "country": "MM",
        "phone": f"+9591{random.randint(10000000, 99999999)}",
        "gender": gender,
    }
