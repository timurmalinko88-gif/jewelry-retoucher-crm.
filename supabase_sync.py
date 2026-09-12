"""Supabase Cloud Sync Module for Retoucher CRM.

Synchronizes local offline-first SQLite database with Supabase cloud PostgreSQL.
Requires ZERO external packages (uses built-in standard library urllib).
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.parse
import urllib.request

from db import execute_query, fetch_all, get_connection

# Default configuration (can be overridden via Streamlit Secrets or Environment Variables)
DEFAULT_SUPABASE_URL = "https://mofkziuuzlotrfphvwdo.supabase.co"
DEFAULT_SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1vZmt6aXV1emxvdHJmcGh2d2RvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODkyMDUxODgsImV4cCI6MjEwNDc4MTE4OH0."
    "ioPFdjcGxdCN1GHQoDe1g-PlZl6p0Vt4ahfKNLwxfx0"
)

TABLES_ORDER = ["contacts", "touches", "deals", "payments", "retainers"]


def get_credentials() -> Tuple[str, str]:
    """Retrieve Supabase URL and API Key from secrets/env or defaults."""
    url = os.environ.get("SUPABASE_URL", "").strip() or DEFAULT_SUPABASE_URL
    key = os.environ.get("SUPABASE_KEY", "").strip() or DEFAULT_SUPABASE_KEY

    # Check streamlit secrets if in streamlit runtime
    try:
        import streamlit as st

        if hasattr(st, "secrets"):
            if "SUPABASE_URL" in st.secrets:
                url = st.secrets["SUPABASE_URL"]
            if "SUPABASE_KEY" in st.secrets:
                key = st.secrets["SUPABASE_KEY"]
    except Exception:
        pass

    return url.rstrip("/"), key


def api_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Any] = None,
    prefer: Optional[str] = None,
) -> Tuple[bool, Any]:
    """Execute standard REST request to Supabase PostgREST API."""
    url, key = get_credentials()
    full_url = f"{url}/rest/v1/{endpoint}"

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer

    payload_bytes = None
    if data is not None:
        payload_bytes = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(full_url, data=payload_bytes, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            if content:
                try:
                    return True, json.loads(content)
                except Exception:
                    return True, content
            return True, None
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        return False, f"HTTP {e.code}: {err_msg}"
    except Exception as ex:
        return False, str(ex)


def is_supabase_connected() -> bool:
    """Check if Supabase endpoint is reachable and authenticated."""
    ok, _ = api_request("contacts?select=id&limit=1")
    return ok


def push_to_supabase() -> Dict[str, Any]:
    """Upload all local SQLite records to Supabase Cloud with upsert."""
    summary: Dict[str, int] = {}
    errors: List[str] = []

    for table in TABLES_ORDER:
        rows = fetch_all(f"SELECT * FROM {table}")
        if not rows:
            summary[table] = 0
            continue

        records = [dict(r) for r in rows]

        # Clean datetime strings if necessary
        for rec in records:
            for k, v in rec.items():
                if v is None:
                    continue
                # ensure proper date formatting
                if k.endswith("_date") and len(str(v)) > 10:
                    rec[k] = str(v)[:10]

        ok, resp = api_request(
            table,
            method="POST",
            data=records,
            prefer="resolution=merge-duplicates",
        )
        if ok:
            summary[table] = len(records)
        else:
            errors.append(f"Table '{table}': {resp}")

    return {
        "success": len(errors) == 0,
        "summary": summary,
        "errors": errors,
    }


def pull_from_supabase() -> Dict[str, Any]:
    """Download all cloud records from Supabase and replace local SQLite database."""
    summary: Dict[str, int] = {}
    errors: List[str] = []

    with get_connection() as conn:
        cursor = conn.cursor()

        for table in TABLES_ORDER:
            ok, cloud_data = api_request(f"{table}?select=*&order=id.asc")
            if not ok or not isinstance(cloud_data, list):
                errors.append(f"Table '{table}': {cloud_data}")
                continue

            if not cloud_data:
                summary[table] = 0
                continue

            # Clear local table
            cursor.execute(f"DELETE FROM {table}")

            # Insert cloud records
            cols = list(cloud_data[0].keys())
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)

            for item in cloud_data:
                vals = [item.get(c) for c in cols]
                cursor.execute(f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})", vals)

            summary[table] = len(cloud_data)

        conn.commit()

    return {
        "success": len(errors) == 0,
        "summary": summary,
        "errors": errors,
    }
