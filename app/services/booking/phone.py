import re


def normalize_phone(phone: str) -> str:
    """Normalize RU phone to +7XXXXXXXXXX."""
    if not phone:
        return ""
    clean = re.sub(r"[^\d+]", "", str(phone).strip())
    if clean.startswith("8") and len(clean) >= 11:
        clean = "+7" + clean[1:]
    elif clean.startswith("7") and not clean.startswith("+") and len(clean) >= 11:
        clean = "+" + clean
    elif clean and not clean.startswith("+"):
        clean = "+7" + clean
    return clean
