"""Unit and regression tests for Jewelry Retoucher CRM core.

Verifies database integrity, foreign keys, seeding, and business logic.
"""

import os
import sqlite3
import tempfile
import pytest
from datetime import date, timedelta

import db
import logic


@pytest.fixture
def temp_db():
    """Create an isolated temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    old_db_path = db.DB_PATH
    db.DB_PATH = path

    try:
        db.init_db()
        yield path
    finally:
        db.DB_PATH = old_db_path
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def test_seed_demo_data_foreign_key_integrity(temp_db):
    """Regression test: seed_demo_data must not raise sqlite3.IntegrityError."""
    # Ensure foreign keys are active
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys;")
        assert cursor.fetchone()[0] == 1

    # Execute seed_demo_data on fresh DB
    db.seed_demo_data()

    # Verify contacts seeded
    contacts = db.fetch_all("SELECT id, brand_name FROM contacts;")
    assert len(contacts) == 5

    # Verify touches seeded and point to valid contact_ids
    touches = db.fetch_all("SELECT id, contact_id FROM touches;")
    assert len(touches) == 3
    contact_ids = {c["id"] for c in contacts}
    for t in touches:
        assert t["contact_id"] in contact_ids

    # Verify deal seeded
    deals = db.fetch_all("SELECT id, contact_id, amount_usd FROM deals;")
    assert len(deals) == 1
    assert deals[0]["contact_id"] in contact_ids
    assert deals[0]["amount_usd"] == 750.0


def test_seed_demo_data_idempotent(temp_db):
    """Calling seed_demo_data multiple times should be safe and not duplicate."""
    db.seed_demo_data()
    db.seed_demo_data()
    contacts = db.fetch_all("SELECT id FROM contacts;")
    assert len(contacts) == 5


def test_detect_cultural_profile():
    """Verify cultural profile mapping rules."""
    assert logic.detect_cultural_profile("US") == "aggressive"
    assert logic.detect_cultural_profile("IL") == "aggressive"
    assert logic.detect_cultural_profile("GB") == "standard"
    assert logic.detect_cultural_profile("DE") == "patient"
    assert logic.detect_cultural_profile("FR") == "slow"
    assert logic.detect_cultural_profile("unknown_country") == "standard"
    assert logic.detect_cultural_profile("") == "standard"


def test_calculate_next_action_date():
    """Verify cultural cadence interval offsets."""
    base_date = date(2026, 9, 10)

    # Aggressive: [3, 4, 7, 7]
    next_d1 = logic.calculate_next_action_date("aggressive", base_date, touch_number=1)
    assert next_d1 == base_date + timedelta(days=3)

    next_d2 = logic.calculate_next_action_date("aggressive", base_date, touch_number=2)
    assert next_d2 == base_date + timedelta(days=4)

    # Standard: [4, 7, 14]
    next_s1 = logic.calculate_next_action_date("standard", base_date, touch_number=1)
    assert next_s1 == base_date + timedelta(days=4)

    # Slow: [10, 14, 21]
    next_sl1 = logic.calculate_next_action_date("slow", base_date, touch_number=1)
    assert next_sl1 == base_date + timedelta(days=10)


def test_calculate_payment_breakdown():
    """Verify 19.5% tax reserve and platform fee calculations."""
    # Gross: $1,000, Upwork fee: 10%, withdrawal: $2, rate: 41.0, tax: 19.5%
    calc = logic.calculate_payment_breakdown(
        gross_usd=1000.0,
        platform_fee_percent=10.0,
        withdrawal_fee=2.0,
        usd_uah_rate=41.0,
        tax_rate=0.195,
    )

    assert calc["gross_usd"] == 1000.0
    assert calc["platform_fee_usd"] == 100.0
    assert calc["withdrawal_fee"] == 2.0
    assert calc["net_usd"] == 898.0  # 1000 - 100 - 2
    assert calc["net_uah"] == round(898.0 * 41.0, 2)  # 36818.0
    assert calc["tax_reserved_uah"] == round(36818.0 * 0.195, 2)  # 7179.51


def test_normalize_domain():
    """Verify domain normalization for deduplication."""
    assert logic.normalize_domain("https://www.luminajewels.com/collection/rings?ref=ig") == "luminajewels.com"
    assert logic.normalize_domain("http://aethelgard.co.uk/") == "aethelgard.co.uk"
    assert logic.normalize_domain("WWW.MilanoOro.IT") == "milanooro.it"
    assert logic.normalize_domain(None) == ""


def test_luxury_bento_theme_palette_and_fonts():
    """Verify Haute Joaillerie Atelier Bento design tokens and typography."""
    import theme

    css = theme.LUXURY_BENTO_CSS

    # Brand color tokens
    assert "#07090E" in css  # Obsidian Canvas
    assert "#0E121B" in css  # Bento surface
    assert "#D4AF37" in css  # 18K Champagne Gold
    assert "#F3D079" in css  # Light Gold
    assert "#10B981" in css  # Gemstone Emerald
    assert "#F43F5E" in css  # Gemstone Ruby
    assert "#38BDF8" in css  # Gemstone Sapphire

    # Google fonts
    assert "Cinzel" in css
    assert "Plus Jakarta Sans" in css
    assert "JetBrains Mono" in css

    # Core component selectors
    assert '[data-testid="stMetric"]' in css
    assert '[data-testid="stVerticalBlockBorderWrapper"]' in css
    assert '[data-testid="stLayoutWrapper"]' in css
    assert '[data-testid="stForm"]' in css
    assert '[data-testid="stTabs"]' in css
    assert '[data-testid="stSidebar"]' in css
    assert '.stButton > button' in css


def test_render_atelier_header(monkeypatch):
    """Verify render_atelier_header produces valid Haute Joaillerie markup without Markdown indentation bugs."""
    import streamlit as st
    import theme

    captured_markdown = []
    monkeypatch.setattr(st, "markdown", lambda content, **kwargs: captured_markdown.append(content))

    # Test with default date
    theme.render_atelier_header()
    assert len(captured_markdown) == 1
    assert "HAUTE JOAILLERIE ATELIER" in captured_markdown[0]
    assert "RETOUCH OPERATIONAL CRM" in captured_markdown[0]
    assert "atelier-header-bento" in captured_markdown[0]

    # Critical regression check: No line starts with 4+ spaces (which Markdown parses as code block)
    for line in captured_markdown[0].splitlines():
        assert not line.startswith("    "), f"Indented line in header would be treated as code block: {line!r}"

    # Test with custom date
    captured_markdown.clear()
    theme.render_atelier_header(date_str="25.12.2026")
    assert len(captured_markdown) == 1
    assert "25.12.2026" in captured_markdown[0]


def test_render_horlogerie_clocks(monkeypatch):
    """Verify render_horlogerie_clocks renders clock cards without Markdown code block indentation and handles invalid timezones gracefully."""
    import streamlit as st
    import theme

    captured_markdown = []
    monkeypatch.setattr(st, "markdown", lambda content, **kwargs: captured_markdown.append(content))

    # Test with default timezones
    theme.render_horlogerie_clocks()
    assert len(captured_markdown) == 1
    assert "horlogerie-container" in captured_markdown[0]
    assert "horlogerie-card" in captured_markdown[0]
    assert "New York" in captured_markdown[0]
    assert "Tokyo" in captured_markdown[0]

    # Critical regression check: No line starts with 4+ spaces (which Markdown parses as code block)
    for line in captured_markdown[0].splitlines():
        assert not line.startswith("    "), f"Indented line in horlogerie clocks would be treated as code block: {line!r}"

    # Test with invalid timezone in list (should not crash)
    captured_markdown.clear()
    targets = [
        ("🇺🇸 Valid NY", "America/New_York"),
        ("👽 Invalid City", "NonExistent/Timezone_1234"),
    ]
    theme.render_horlogerie_clocks(targets)
    assert len(captured_markdown) == 1
    assert "Valid NY" in captured_markdown[0]
    assert "Invalid City" not in captured_markdown[0]


def test_inject_luxury_theme(monkeypatch):
    """Verify inject_luxury_theme injects style tags."""
    import streamlit as st
    import theme

    captured = []
    monkeypatch.setattr(st, "markdown", lambda content, **kwargs: captured.append((content, kwargs)))

    theme.inject_luxury_theme()
    assert len(captured) == 1
    content, kwargs = captured[0]
    assert content.startswith("<style>")
    assert content.endswith("</style>")
    assert kwargs.get("unsafe_allow_html") is True

