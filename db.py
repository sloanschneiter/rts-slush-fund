"""Turso (libSQL) client + schema bootstrap, via the Turso HTTP API.

Using the HTTP API (instead of libsql-experimental) avoids a native build
dependency, which means it works on Windows for local dev and on Streamlit
Cloud's Linux containers identically.

API ref: https://docs.turso.tech/sdk/http/reference (v2 pipeline endpoint)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import uuid4

import requests
import streamlit as st


# ---------------------------------------------------------------------------
# Seed data — the May FC budget diff (true original vs current).
# Positive amount = cut (savings). Negative amount = added spend.
# Loaded on first bootstrap only; later edits live in the DB.
# ---------------------------------------------------------------------------
SEED_ITEMS: list[dict] = [
    # HAVENLY — net +$22,449
    {"brand": "Havenly", "channel": "Pinterest", "amount": 3000,
     "summary": "Pinterest $20,000 → $17,000."},
    {"brand": "Havenly", "channel": "Pinterest - Merch RT", "amount": 9500,
     "summary": "Pinterest Merch RT $9,500 → $0 (line removed)."},
    {"brand": "Havenly", "channel": "Meta - Merch RT", "amount": 5000,
     "summary": "Meta Merch RT $5,000 → $0 (line removed)."},
    {"brand": "Havenly", "channel": "Criteo", "amount": 3000,
     "summary": "Criteo $3,000 → $0 (line removed)."},
    {"brand": "Havenly", "channel": "Affiliate (Impact)", "amount": 1000,
     "summary": "Affiliate (Impact) $1,000 → $0 (line removed)."},
    {"brand": "Havenly", "channel": "Influencers", "amount": 25409,
     "summary": "Influencers $25,409 → $0 (line removed)."},
    {"brand": "Havenly", "channel": "Affiliate Agency Fees (Revel)", "amount": 1540,
     "summary": "Affiliate Agency Fees (Revel) $1,540 → $0 (line removed)."},
    {"brand": "Havenly", "channel": "Google - Brand Search", "amount": -15000,
     "summary": "ADDED: Google Brand Search $5,000 → $20,000 (+$15k for Memorial Day)."},
    {"brand": "Havenly", "channel": "TikTok", "amount": -11000,
     "summary": "ADDED: TikTok $9,000 → $20,000 (+$11k)."},

    # BURROW — net +$83,866
    {"brand": "Burrow", "channel": "Meta", "amount": 200000,
     "summary": "Meta $475,000 → $275,000 (line restructure; see Meta Retargeting added)."},
    {"brand": "Burrow", "channel": "Pinterest", "amount": 60000,
     "summary": "Pinterest $60,000 → $0 (line removed)."},
    {"brand": "Burrow", "channel": "Affiliate (Pepperjam)", "amount": 25000,
     "summary": "Affiliate (Pepperjam) $50,000 → $25,000."},
    {"brand": "Burrow", "channel": "Catalog", "amount": 23264,
     "summary": "Catalog $23,264 → $0 (line removed)."},
    {"brand": "Burrow", "channel": "Influencer/Product Seeding", "amount": 2602,
     "summary": "Influencer/Product Seeding $9,602 → $7,000."},
    {"brand": "Burrow", "channel": "Meta - Retargeting", "amount": -110000,
     "summary": "ADDED: New Meta Retargeting line $0 → $110,000 (offsets Meta cut above)."},
    {"brand": "Burrow", "channel": "PMax (Google)", "amount": -50000,
     "summary": "ADDED: PMax (Google) $425,000 → $475,000 (+$50k)."},
    {"brand": "Burrow", "channel": "NB Search (Google)", "amount": -48000,
     "summary": "ADDED: NB Search (Google) $2,000 → $50,000 (+$48k)."},
    {"brand": "Burrow", "channel": "TikTok", "amount": -19000,
     "summary": "ADDED: TikTok $6,000 → $25,000 (+$19k)."},

    # CITIZENRY — net +$8,766
    {"brand": "Citizenry", "channel": "Brand Search & PLA (Google)", "amount": 30000,
     "summary": "Brand Search & PLA (Google) $70,000 → $40,000."},
    {"brand": "Citizenry", "channel": "Influencers", "amount": 6226,
     "summary": "Influencers $6,226 → $0 (line removed)."},
    {"brand": "Citizenry", "channel": "Meta (Trade)", "amount": 2000,
     "summary": "Meta (Trade) $2,000 → $0 (line removed)."},
    {"brand": "Citizenry", "channel": "Search (Trade)", "amount": 2000,
     "summary": "Search (Trade) $2,000 → $0 (line removed)."},
    {"brand": "Citizenry", "channel": "PMax (Google)", "amount": -20000,
     "summary": "ADDED: PMax (Google) $180,000 → $200,000 (+$20k)."},
    {"brand": "Citizenry", "channel": "Meta (total)", "amount": -9460,
     "summary": "ADDED: Meta restructure — $189,000 single line → $133k Prospecting + $39k Retargeting + $26,460 Retention = $198,460 (+$9.46k net)."},
    {"brand": "Citizenry", "channel": "Pinterest", "amount": -2000,
     "summary": "ADDED: Pinterest $18,000 → $20,000 (+$2k)."},

    # INTERIOR DEFINE — net +$98,634
    {"brand": "Interior Define", "channel": "PMax - Swatch", "amount": 52000,
     "summary": "PMax - Swatch $152,000 → $100,000."},
    {"brand": "Interior Define", "channel": "Criteo", "amount": 25000,
     "summary": "Criteo $50,000 → $25,000."},
    {"brand": "Interior Define", "channel": "Meta - All Other", "amount": 50000,
     "summary": "Meta - All Other $450,000 → $400,000."},
    {"brand": "Interior Define", "channel": "Pinterest - All Other", "amount": 70000,
     "summary": "Pinterest - All Other $110,000 → $40,000."},
    {"brand": "Interior Define", "channel": "Affiliate (Pepperjam)", "amount": 70000,
     "summary": "Affiliate (Pepperjam) $150,000 → $80,000."},
    {"brand": "Interior Define", "channel": "Influencers/Ambassadors", "amount": 13634,
     "summary": "Influencers/Ambassadors $13,634 → $0 (line removed)."},
    {"brand": "Interior Define", "channel": "Non Brand Search (Trade)", "amount": 10000,
     "summary": "Non Brand Search (Trade) $10,000 → $0 (line removed)."},
    {"brand": "Interior Define", "channel": "Meta (Trade)", "amount": 5000,
     "summary": "Meta (Trade) $5,000 → $0 (line removed)."},
    {"brand": "Interior Define", "channel": "PMax - Purchase", "amount": -109000,
     "summary": "ADDED: PMax - Purchase $741,000 → $850,000 (+$109k)."},
    {"brand": "Interior Define", "channel": "Meta - Retargeting", "amount": -88000,
     "summary": "ADDED: New Meta Retargeting line $0 → $88,000."},
]


# ---------------------------------------------------------------------------
# Secrets + HTTP plumbing
# ---------------------------------------------------------------------------
def _secret(name: str) -> str:
    try:
        return st.secrets[name]
    except (KeyError, FileNotFoundError):
        value = os.environ.get(name.upper())
        if not value:
            raise RuntimeError(
                f"Missing secret '{name}'. Set it in .streamlit/secrets.toml locally "
                f"or in App settings -> Secrets on Streamlit Cloud."
            )
        return value


def _http_base_url() -> str:
    raw = _secret("turso_database_url").strip()
    if raw.startswith("libsql://"):
        return "https://" + raw[len("libsql://"):]
    if raw.startswith("https://"):
        return raw
    raise RuntimeError(f"Unexpected turso_database_url scheme: {raw!r}")


def _arg(value: Any) -> dict:
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "integer", "value": str(int(value))}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    return {"type": "text", "value": str(value)}


def _unwrap(cell: dict) -> Any:
    if cell is None:
        return None
    t = cell.get("type")
    v = cell.get("value")
    if t == "null" or v is None:
        return None
    if t == "integer":
        try:
            return int(v)
        except (TypeError, ValueError):
            return v
    if t == "float":
        try:
            return float(v)
        except (TypeError, ValueError):
            return v
    return v


def _pipeline(statements: Sequence[tuple[str, Sequence[Any]]]) -> list[dict]:
    requests_body = [
        {"type": "execute", "stmt": {"sql": sql, "args": [_arg(a) for a in args]}}
        for sql, args in statements
    ]
    requests_body.append({"type": "close"})
    resp = requests.post(
        _http_base_url().rstrip("/") + "/v2/pipeline",
        json={"requests": requests_body},
        headers={
            "Authorization": f"Bearer {_secret('turso_auth_token')}",
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Turso HTTP {resp.status_code}: {resp.text[:500]}")
    payload = resp.json()
    results = payload.get("results", [])
    execute_results: list[dict] = []
    for i, r in enumerate(results):
        if r.get("type") == "error":
            err = r.get("error", {}).get("message", "unknown")
            raise RuntimeError(f"Turso statement #{i} failed: {err}")
        response = r.get("response", {})
        if response.get("type") == "execute":
            execute_results.append(response.get("result", {}))
    return execute_results


def _execute(sql: str, args: Sequence[Any] = ()) -> dict:
    return _pipeline([(sql, list(args))])[0]


def _rows(result: dict) -> list[list[Any]]:
    return [[_unwrap(cell) for cell in row] for row in result.get("rows", [])]


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def _bootstrap() -> bool:
    """Create the items table and seed initial budget-diff rows on first run."""
    _execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id          TEXT PRIMARY KEY,
            created_at  TEXT NOT NULL,
            brand       TEXT NOT NULL,
            channel     TEXT NOT NULL,
            amount      REAL NOT NULL DEFAULT 0,
            summary     TEXT
        )
        """,
    )
    # Seed only if table is empty
    existing = _rows(_execute("SELECT COUNT(*) FROM items"))
    count = int(existing[0][0]) if existing and existing[0] else 0
    if count == 0:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        statements = []
        for it in SEED_ITEMS:
            statements.append((
                "INSERT INTO items (id, created_at, brand, channel, amount, summary) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid4()), now, it["brand"], it["channel"], float(it["amount"]), it["summary"]),
            ))
        if statements:
            _pipeline(statements)
    return True


def _ensure_bootstrap() -> None:
    _bootstrap()


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------
def list_items() -> list[dict]:
    _ensure_bootstrap()
    result = _execute(
        "SELECT id, created_at, brand, channel, amount, summary "
        "FROM items ORDER BY brand, amount DESC"
    )
    out: list[dict] = []
    for r in _rows(result):
        out.append({
            "id": r[0],
            "created_at": r[1],
            "brand": r[2],
            "channel": r[3],
            "amount": float(r[4] or 0),
            "summary": r[5] or "",
        })
    return out


def add_item(brand: str, channel: str, amount: float, summary: str) -> str:
    _ensure_bootstrap()
    item_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _execute(
        "INSERT INTO items (id, created_at, brand, channel, amount, summary) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (item_id, created_at, brand, channel, float(amount), summary),
    )
    return item_id


def update_item(item_id: str, brand: str, channel: str, amount: float, summary: str) -> None:
    _ensure_bootstrap()
    _execute(
        "UPDATE items SET brand = ?, channel = ?, amount = ?, summary = ? WHERE id = ?",
        (brand, channel, float(amount), summary, item_id),
    )


def delete_item(item_id: str) -> None:
    _ensure_bootstrap()
    _execute("DELETE FROM items WHERE id = ?", (item_id,))
