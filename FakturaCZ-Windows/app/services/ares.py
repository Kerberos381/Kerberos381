"""ARES (Czech Business Registry) API client."""

import requests

ARES_BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty"


class ARESError(Exception):
    pass


def fetch_subject(registration_no: str) -> dict:
    """
    Fetches subject data from ARES by registration number (IČO).

    Returns dict with keys: registration_no, name, street, city, zip, vat_no.
    """
    cleaned = registration_no.strip()
    if len(cleaned) != 8 or not cleaned.isdigit():
        raise ARESError("Neplatné IČO. IČO musí mít 8 číslic.")

    url = f"{ARES_BASE_URL}/{cleaned}"
    headers = {"Accept": "application/json"}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as e:
        raise ARESError(f"Chyba sítě: {e}") from e

    if resp.status_code == 404:
        raise ARESError("Subjekt nebyl nalezen v registru ARES.")
    if resp.status_code != 200:
        raise ARESError(f"Server ARES vrátil chybu: {resp.status_code}")

    try:
        data = resp.json()
    except ValueError as e:
        raise ARESError(f"Chyba zpracování odpovědi: {e}") from e

    sidlo = data.get("sidlo", {})
    street = _build_street(sidlo)

    return {
        "registration_no": cleaned,
        "name": data.get("obchodniJmeno", ""),
        "street": street,
        "city": sidlo.get("nazevObce", ""),
        "zip": str(sidlo.get("psc", "")),
        "vat_no": data.get("dic"),
    }


def _build_street(sidlo: dict) -> str:
    """Builds street address from ARES sidlo components."""
    full = sidlo.get("textovaAdresa", "")
    if full:
        return full

    parts = []
    street_name = sidlo.get("nazevUlice", "")
    if street_name:
        parts.append(street_name)

    domovni = sidlo.get("cisloDomovni")
    if domovni:
        orientacni = sidlo.get("cisloOrientacni")
        if orientacni:
            parts.append(f"{domovni}/{orientacni}")
        else:
            parts.append(str(domovni))

    return " ".join(parts)
