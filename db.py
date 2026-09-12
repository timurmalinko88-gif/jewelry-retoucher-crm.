"""Database layer for Retoucher CRM.

Handles SQLite connection, schema initialization, and demo seeding.
"""

from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

DB_PATH = Path(__file__).resolve().parent / "crm.db"


def get_connection() -> sqlite3.Connection:
    """Create and return thread-safe SQLite connection."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initialize all 5 tables and required indexes."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. contacts
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL,
                country TEXT,
                website TEXT,
                instagram TEXT,
                email TEXT,
                email_status TEXT DEFAULT 'unverified',
                decision_maker TEXT,
                language TEXT DEFAULT 'en',
                category TEXT,
                priority TEXT DEFAULT 'medium',
                catalog_size TEXT,
                photo_quality TEXT,
                cultural_profile TEXT DEFAULT 'standard',
                timezone_note TEXT,
                source_base TEXT,
                pipeline_status TEXT DEFAULT 'lead',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # 2. touches
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS touches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                channel TEXT,
                template_type TEXT,
                subject TEXT,
                sent_date TEXT,
                status TEXT DEFAULT 'sent',
                next_action_date TEXT,
                notes TEXT,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
            );
        """
        )

        # 3. deals
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                deal_type TEXT DEFAULT 'one-off',
                description TEXT,
                amount_usd REAL DEFAULT 0.0,
                payment_method TEXT,
                upwork_contract_url TEXT,
                status TEXT DEFAULT 'in_progress',
                created_date TEXT,
                delivered_date TEXT,
                paid_date TEXT,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
            );
        """
        )

        # 4. payments
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id INTEGER NOT NULL,
                gross_usd REAL DEFAULT 0.0,
                platform_fee_percent REAL DEFAULT 0.0,
                platform_fee_usd REAL DEFAULT 0.0,
                withdrawal_fee REAL DEFAULT 0.0,
                net_usd REAL DEFAULT 0.0,
                usd_uah_rate REAL DEFAULT 0.0,
                net_uah REAL DEFAULT 0.0,
                tax_rate REAL DEFAULT 0.195,
                tax_reserved_uah REAL DEFAULT 0.0,
                date_received TEXT,
                date_withdrawn TEXT,
                declaration_month TEXT,
                FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE
            );
        """
        )

        # 5. retainers
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS retainers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id INTEGER NOT NULL,
                monthly_amount_usd REAL DEFAULT 0.0,
                images_per_month INTEGER DEFAULT 0,
                start_month TEXT,
                status TEXT DEFAULT 'active',
                next_contract_ping_date TEXT,
                notes TEXT,
                FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
            );
        """
        )

        # Indexes for fast querying
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_contacts_pipeline ON contacts(pipeline_status);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_touches_next_action ON touches(next_action_date);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_touches_contact ON touches(contact_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_deals_contact ON deals(contact_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_retainers_ping ON retainers(next_contract_ping_date);"
        )
        conn.commit()


def seed_demo_data() -> None:
    """Populate database with demo dataset if contacts table is empty."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contacts;")
        if cursor.fetchone()[0] > 0:
            return  # Already seeded

        # Seed 5 Contacts
        contacts_data = [
            (
                "Lumina Fine Jewels",
                "US",
                "https://luminajewels.com",
                "@luminajewels",
                "sarah@luminajewels.com",
                "valid",
                "Sarah Jenkins (Creative Director)",
                "en",
                "Fine Jewelry",
                "high",
                "250 items",
                "Mid (needs metal smoothing and diamond brilliance)",
                "aggressive",
                "EST (UTC-5)",
                "Instagram Outreach",
                "contacted",
                "Interested in clean white background and editorial renders.",
            ),
            (
                "Aethelgard Silver",
                "GB",
                "https://aethelgard.co.uk",
                "@aethelgard_uk",
                "edward@aethelgard.co.uk",
                "valid",
                "Edward Vance (Founder)",
                "en",
                "Silver & Gothic",
                "medium",
                "80 items",
                "Raw studio photos with heavy shadows",
                "standard",
                "GMT (UTC+0)",
                "Google Search",
                "lead",
                "Handcrafted rings, focus on texture preservation.",
            ),
            (
                "Milano Oro & Pietre",
                "IT",
                "https://milanooro.it",
                "@milano_oro",
                "marco.rossi@milanooro.it",
                "unverified",
                "Marco Rossi (Owner)",
                "en",
                "High Jewelry",
                "high",
                "120 items",
                "Good camera, mediocre post-production",
                "patient",
                "CET (UTC+1)",
                "VicenzaOro Exhibitor List",
                "replied",
                "Requested before/after samples of emeralds and gold reflections.",
            ),
            (
                "Atelier Dauphin Paris",
                "FR",
                "https://atelier-dauphin.fr",
                "@atelierdauphin",
                "claire@atelier-dauphin.fr",
                "valid",
                "Claire Laurent (Marketing Lead)",
                "fr",
                "Contemporary Art Jewelry",
                "medium",
                "150 items",
                "High quality 3D CAD renders needing photorealism touch",
                "slow",
                "CET (UTC+1)",
                "LinkedIn",
                "negotiation",
                "Currently discussing test batch of 15 pieces.",
            ),
            (
                "Nordic Aurum Studio",
                "SE",
                "https://nordicaurum.se",
                "@nordic.aurum",
                "astrid@nordicaurum.se",
                "unverified",
                "Astrid Lind (Designer)",
                "en",
                "Minimalist Jewelry",
                "low",
                "45 items",
                "iPhone daylight photos",
                "patient",
                "CET (UTC+1)",
                "Instagram",
                "lead",
                "Small collection, might need budget package.",
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO contacts (
                brand_name, country, website, instagram, email, email_status,
                decision_maker, language, category, priority, catalog_size,
                photo_quality, cultural_profile, timezone_note, source_base,
                pipeline_status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            contacts_data,
        )

        # Seed 3 Touches
        touches_data = [
            (
                1,
                "Email",
                "initial_cold",
                "Quick retouching question for Lumina Fine Jewels",
                "2026-09-10",
                "sent",
                "2026-09-13",
                "Cold email with link to curated diamond ring portfolio.",
            ),
            (
                3,
                "Instagram",
                "dm_compliment",
                "Compliment on emerald collection & test offer",
                "2026-09-08",
                "replied",
                "2026-09-15",
                "Client replied asking for pricing per item.",
            ),
            (
                4,
                "Email",
                "portfolio_followup",
                "Test piece estimation for Atelier Dauphin Paris",
                "2026-09-05",
                "sent",
                "2026-09-15",
                "Sent quote of $750 for 15 pieces. Waiting for approval.",
            ),
        ]

        cursor.executemany(
            """
            INSERT INTO touches (
                contact_id, channel, template_type, subject, sent_date,
                status, next_action_date, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            touches_data,
        )

        # Seed 1 Deal
        deals_data = [
            (
                4,
                "one-off",
                "Test batch: 15 pieces lookbook retouching",
                750.0,
                "Upwork",
                "https://www.upwork.com/contracts/~01testdauphin123",
                "in_progress",
                "2026-09-11",
                "2026-09-18",
                None,
            )
        ]

        cursor.executemany(
            """
            INSERT INTO deals (
                contact_id, deal_type, description, amount_usd,
                payment_method, upwork_contract_url, status,
                created_date, delivered_date, paid_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            deals_data,
        )

        conn.commit()


# ==========================================
# Generic DB helper functions
# ==========================================


def fetch_all(query: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
    """Execute a query and return all rows."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()


def fetch_one(query: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
    """Execute a query and return a single row or None."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone()


def execute_query(query: str, params: Tuple[Any, ...] = ()) -> int:
    """Execute INSERT/UPDATE/DELETE and return the lastrowid or affected count."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid


def get_dataframe(query: str, params: Tuple[Any, ...] = ()) -> pd.DataFrame:
    """Read query directly into pandas DataFrame."""
    with get_connection() as conn:
        return pd.read_sql_query(query, conn, params=params)


if __name__ == "__main__":
    init_db()
    seed_demo_data()
    print("Database initialized and demo data seeded successfully.")
