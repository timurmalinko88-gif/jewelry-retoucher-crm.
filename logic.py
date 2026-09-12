"""Business logic for Retoucher CRM.

Implements cultural cadences, financial calculations, and JSON parsing with deduplication.
"""

from datetime import date, datetime, timedelta
import json
import re
from typing import Any, Dict, List, Optional, Tuple, Union
import urllib.parse

from db import execute_query, fetch_all, get_connection

# ==========================================
# 1. Cultural Cadence Logic
# ==========================================

# Intervals (in days) between consecutive touches
CADENCE_SCHEDULE: Dict[str, List[int]] = {
    "aggressive": [3, 4, 7, 7],   # Touch 1->2 (+3d), 2->3 (+4d), 3->4 (+7d), 4->Breakup (+7d)
    "standard": [4, 7, 14],       # Touch 1->2 (+4d), 2->3 (+7d), 3->Breakup (+14d)
    "patient": [7, 10, 18],       # Touch 1->2 (+7d), 2->3 (+10d), 3->Breakup (+18d)
    "slow": [10, 14, 21],         # Touch 1->2 (+10d), 2->3 (+14d), 3->Breakup (+21d)
}

COUNTRY_TO_PROFILE: Dict[str, str] = {
    # aggressive: US/IL/NL
    "US": "aggressive",
    "USA": "aggressive",
    "UNITED STATES": "aggressive",
    "IL": "aggressive",
    "ISRAEL": "aggressive",
    "NL": "aggressive",
    "NETHERLANDS": "aggressive",
    # standard: GB/PL/RO/Baltics/CZ/AU/BE
    "GB": "standard",
    "UK": "standard",
    "UNITED KINGDOM": "standard",
    "PL": "standard",
    "POLAND": "standard",
    "RO": "standard",
    "ROMANIA": "standard",
    "EE": "standard",
    "ESTONIA": "standard",
    "LV": "standard",
    "LATVIA": "standard",
    "LT": "standard",
    "LITHUANIA": "standard",
    "CZ": "standard",
    "CZECH REPUBLIC": "standard",
    "AU": "standard",
    "AUSTRALIA": "standard",
    "BE": "standard",
    "BELGIUM": "standard",
    # patient: DE/IT/ES/PT/Nordics/GR/Balkans
    "DE": "patient",
    "GERMANY": "patient",
    "IT": "patient",
    "ITALY": "patient",
    "ES": "patient",
    "SPAIN": "patient",
    "PT": "patient",
    "PORTUGAL": "patient",
    "SE": "patient",
    "SWEDEN": "patient",
    "NO": "patient",
    "NORWAY": "patient",
    "DK": "patient",
    "DENMARK": "patient",
    "FI": "patient",
    "FINLAND": "patient",
    "GR": "patient",
    "GREECE": "patient",
    "RS": "patient",
    "HR": "patient",
    "BG": "patient",
    # slow: FR/CH/AE
    "FR": "slow",
    "FRANCE": "slow",
    "CH": "slow",
    "SWITZERLAND": "slow",
    "AE": "slow",
    "UAE": "slow",
    "UNITED ARAB EMIRATES": "slow",
}


def detect_cultural_profile(country: Optional[str]) -> str:
    """Infer cultural profile from country code or name. Defaults to 'standard'."""
    if not country:
        return "standard"
    cleaned = country.strip().upper()
    return COUNTRY_TO_PROFILE.get(cleaned, "standard")


def calculate_next_action_date(
    cultural_profile: str,
    last_touch_date: Union[date, str, datetime],
    touch_number: int = 1,
) -> Optional[date]:
    """Calculate the next scheduled action date based on cultural profile and touch count.

    Args:
        cultural_profile: One of 'aggressive', 'standard', 'patient', 'slow'.
        last_touch_date: Date of the most recent touch (date, datetime, or 'YYYY-MM-DD').
        touch_number: 1 for next action after 1st touch, 2 for after 2nd, etc.

    Returns:
        date of next action, or None if cadence is exhausted.
    """
    profile = (cultural_profile or "standard").lower().strip()
    intervals = CADENCE_SCHEDULE.get(profile, CADENCE_SCHEDULE["standard"])

    idx = max(0, touch_number - 1)
    if idx >= len(intervals):
        return None

    if isinstance(last_touch_date, str):
        # Parse YYYY-MM-DD
        dt = datetime.strptime(last_touch_date[:10], "%Y-%m-%d").date()
    elif isinstance(last_touch_date, datetime):
        dt = last_touch_date.date()
    elif isinstance(last_touch_date, date):
        dt = last_touch_date
    else:
        dt = date.today()

    return dt + timedelta(days=intervals[idx])


def get_contact_touch_count(contact_id: int) -> int:
    """Return how many touches have been logged for this contact."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM touches WHERE contact_id = ?", (contact_id,))
        row = cursor.fetchone()
        return row[0] if row else 0


# ==========================================
# 2. Financial Calculations
# ==========================================


def calculate_payment_breakdown(
    gross_usd: float,
    platform_fee_percent: float = 0.0,
    withdrawal_fee: float = 0.0,
    usd_uah_rate: float = 41.0,
    tax_rate: float = 0.195,
) -> Dict[str, float]:
    """Calculate net proceeds and tax reserve according to Ukrainian tax rules.

    Formulas:
        platform_fee_usd = gross_usd * (platform_fee_percent / 100)
        net_usd = gross_usd - platform_fee_usd - withdrawal_fee
        net_uah = net_usd * usd_uah_rate
        tax_reserved_uah = net_uah * tax_rate (default 19.5% = 18% PIT + 1.5% Military Tax)
    """
    gross_usd = max(0.0, float(gross_usd or 0.0))
    platform_fee_percent = max(0.0, float(platform_fee_percent or 0.0))
    withdrawal_fee = max(0.0, float(withdrawal_fee or 0.0))
    usd_uah_rate = max(0.0, float(usd_uah_rate or 0.0))
    tax_rate = max(0.0, float(tax_rate or 0.195))

    platform_fee_usd = round(gross_usd * (platform_fee_percent / 100.0), 2)
    net_usd = round(gross_usd - platform_fee_usd - withdrawal_fee, 2)
    net_uah = round(net_usd * usd_uah_rate, 2)
    tax_reserved_uah = round(net_uah * tax_rate, 2)

    return {
        "gross_usd": round(gross_usd, 2),
        "platform_fee_percent": round(platform_fee_percent, 2),
        "platform_fee_usd": platform_fee_usd,
        "withdrawal_fee": round(withdrawal_fee, 2),
        "net_usd": net_usd,
        "usd_uah_rate": round(usd_uah_rate, 2),
        "net_uah": net_uah,
        "tax_rate": round(tax_rate, 4),
        "tax_reserved_uah": tax_reserved_uah,
    }


# ==========================================
# 3. Normalization & Deduplication
# ==========================================


def normalize_domain(url_or_domain: Optional[str]) -> str:
    """Normalize website domain for reliable deduplication."""
    if not url_or_domain:
        return ""
    text = str(url_or_domain).strip().lower()
    # Strip protocol
    text = re.sub(r"^https?://", "", text)
    # Strip www
    text = re.sub(r"^www\.", "", text)
    # Strip path, query, trailing slashes
    text = text.split("/")[0].split("?")[0].strip()
    return text


def normalize_email(email: Optional[str]) -> str:
    """Normalize email address."""
    if not email:
        return ""
    return str(email).strip().lower()


def get_existing_signatures() -> Tuple[set, set]:
    """Retrieve sets of existing emails and domains from the database."""
    rows = fetch_all("SELECT email, website FROM contacts")
    existing_emails = set()
    existing_domains = set()
    for row in rows:
        em = normalize_email(row["email"])
        if em:
            existing_emails.add(em)
        dom = normalize_domain(row["website"])
        if dom:
            existing_domains.add(dom)
    return existing_emails, existing_domains


# ==========================================
# 4. JSON Import & Parsing
# ==========================================


def parse_and_import_contacts_json(
    json_data: Union[str, list, dict],
    default_source: str = "JSON Import",
) -> Dict[str, Any]:
    """Parse JSON (nested like global_master.json or flat) and import new contacts.

    Performs deduplication by normalized email and domain against existing database records.
    """
    if isinstance(json_data, str):
        try:
            records = json.loads(json_data)
        except Exception as e:
            return {
                "success": False,
                "error": f"JSON syntax error: {str(e)}",
                "imported": 0,
                "duplicates": 0,
            }
    elif isinstance(json_data, dict):
        records = [json_data]
    elif isinstance(json_data, list):
        records = json_data
    else:
        return {"success": False, "error": "Invalid input type", "imported": 0, "duplicates": 0}

    existing_emails, existing_domains = get_existing_signatures()

    seen_emails_in_batch = set()
    seen_domains_in_batch = set()

    imported_count = 0
    duplicate_count = 0
    errors = []

    with get_connection() as conn:
        cursor = conn.cursor()

        for idx, item in enumerate(records, start=1):
            if not isinstance(item, dict):
                continue

            # 1. Brand name
            brand_name = item.get("brand_name") or item.get("name") or item.get("brand")
            if not brand_name:
                continue

            # 2. Country & cultural profile
            country = item.get("country", "")
            cultural_profile = item.get("cultural_profile") or detect_cultural_profile(country)

            # 3. Website
            website_raw = item.get("website", "")
            if isinstance(website_raw, dict):
                website = website_raw.get("url") or website_raw.get("clean_domain") or ""
            else:
                website = str(website_raw or "")
            domain = normalize_domain(website)

            # 4. Contacts & Email
            contacts_sub = item.get("contacts", {})
            if isinstance(contacts_sub, dict):
                email = contacts_sub.get("email", "")
                email_status = contacts_sub.get("email_status", "unverified")
                decision_maker = contacts_sub.get("decision_maker") or contacts_sub.get("name", "")
            else:
                email = item.get("email", "")
                email_status = item.get("email_status", "unverified")
                decision_maker = item.get("decision_maker", "")

            email_clean = normalize_email(email)

            # 5. Instagram
            insta_raw = item.get("instagram", "")
            if isinstance(insta_raw, dict):
                instagram = insta_raw.get("handle") or insta_raw.get("url") or ""
            else:
                instagram = str(insta_raw or "")

            # Deduplication check
            is_dup = False
            if email_clean and (email_clean in existing_emails or email_clean in seen_emails_in_batch):
                is_dup = True
            if domain and (domain in existing_domains or domain in seen_domains_in_batch):
                is_dup = True

            if is_dup:
                duplicate_count += 1
                continue

            # Priority mapping
            priority_raw = str(item.get("retouch_priority") or item.get("priority", "medium")).lower()
            if priority_raw in ("a", "high"):
                priority = "high"
            elif priority_raw in ("b", "medium"):
                priority = "medium"
            elif priority_raw in ("c", "low"):
                priority = "low"
            else:
                priority = "medium"

            # Catalog & Photo signals
            catalog_size = str(item.get("catalog_size_estimate") or item.get("catalog_size", ""))
            photo_quality = str(item.get("photo_quality_signal") or item.get("photo_quality", ""))
            category = str(item.get("price_segment") or item.get("category", "Jewelry"))
            language = str(item.get("language", "en"))
            source_base = str(item.get("source_base") or default_source)
            pipeline_status = str(item.get("pipeline_status", "lead"))
            notes = str(item.get("notes", ""))

            try:
                cursor.execute(
                    """
                    INSERT INTO contacts (
                        brand_name, country, website, instagram, email, email_status,
                        decision_maker, language, category, priority, catalog_size,
                        photo_quality, cultural_profile, timezone_note, source_base,
                        pipeline_status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        brand_name,
                        country,
                        website,
                        instagram,
                        email_clean,
                        email_status,
                        decision_maker,
                        language,
                        category,
                        priority,
                        catalog_size,
                        photo_quality,
                        cultural_profile,
                        "",
                        source_base,
                        pipeline_status,
                        notes,
                    ),
                )
                imported_count += 1

                if email_clean:
                    seen_emails_in_batch.add(email_clean)
                    existing_emails.add(email_clean)
                if domain:
                    seen_domains_in_batch.add(domain)
                    existing_domains.add(domain)

            except Exception as ex:
                errors.append(f"Row {idx} ({brand_name}): {str(ex)}")

        conn.commit()

    return {
        "success": True,
        "imported": imported_count,
        "duplicates": duplicate_count,
        "errors": errors,
    }
