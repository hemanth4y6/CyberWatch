"""
feeds/otx.py — AlienVault OTX (Open Threat Exchange) feed.

Endpoint: /pulses/activity  (NOT /pulses/subscribed — returns empty for accounts
                             with no manual subscriptions)
Refresh: every 6 h.
Geo: IPv4 indicators batch-resolved before normalization.
Globe render: source pulse dot (target geo not available from OTX).
"""

import logging
import os

import httpx

from normalize import normalize_otx
from models import insert_event
from enrichment.geo import batch_geo_lookup

logger  = logging.getLogger(__name__)
OTX_KEY = os.getenv("OTX_API_KEY", "")
_URL    = "https://otx.alienvault.com/api/v1/pulses/activity"


async def fetch_otx() -> list[dict]:
    if not OTX_KEY:
        logger.warning("OTX_API_KEY not set — skipping OTX feed")
        return []

    logger.info("Fetching AlienVault OTX…")
    try:
        headers = {"X-OTX-API-KEY": OTX_KEY}
        params  = {"limit": 100, "page": 1}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        pulses = data.get("results", [])

        # Collect all IPv4 indicators (one geo batch for all pulses)
        ip_to_pulses: dict[str, list] = {}
        for pulse in pulses:
            for ind in pulse.get("indicators", []):
                if ind.get("type") == "IPv4":
                    ip = ind["indicator"]
                    ip_to_pulses.setdefault(ip, []).append(pulse)

        geo_data = await batch_geo_lookup(list(ip_to_pulses)) if ip_to_pulses else {}

        new: list[dict] = []
        seen: set[str]  = set()
        for pulse in pulses:
            for ind in pulse.get("indicators", []):
                if ind.get("type") == "IPv4":
                    ip    = ind["indicator"]
                    event = normalize_otx(pulse, geo_data, ip)
                    if event["id"] not in seen:
                        seen.add(event["id"])
                        if insert_event(event):
                            new.append(event)

        logger.info(f"OTX: {len(new)} new events from {len(pulses)} pulses")
        return new

    except Exception as exc:
        logger.error(f"OTX fetch failed: {exc}")
        return []
