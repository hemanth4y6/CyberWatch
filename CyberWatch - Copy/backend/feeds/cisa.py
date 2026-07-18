"""
feeds/cisa.py — CISA Known Exploited Vulnerabilities (KEV) feed.

Refresh: daily.
Geo: null (vulnerability registry — no IP/geo data).
Globe render: skipped; events are stored for CARS + stats only.
"""

import logging
import httpx

from normalize import normalize_cisa
from models import insert_event

logger = logging.getLogger(__name__)

_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


async def fetch_cisa() -> list[dict]:
    logger.info("Fetching CISA KEV…")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(_URL)
            resp.raise_for_status()
            data = resp.json()

        new: list[dict] = []
        for entry in data.get("vulnerabilities", []):
            event = normalize_cisa(entry)
            if insert_event(event):
                new.append(event)

        logger.info(f"CISA: {len(new)} new events (total in feed: {len(data.get('vulnerabilities', []))})")
        return new

    except Exception as exc:
        logger.error(f"CISA fetch failed: {exc}")
        return []
