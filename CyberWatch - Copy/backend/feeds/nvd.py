"""
feeds/nvd.py — NIST National Vulnerability Database (NVD) feed.

Refresh: every 2 h (fetches CVEs published in last 2 h).
Geo: null (vulnerability registry — no IP/geo data).
Globe render: skipped; events are stored for CARS + stats only.
NVD API key increases rate limit from 5 to 50 req/30s.

Startup mode: lookback_hours=720 (30 days), min_cvss=7.0 to populate
the database with recent high/critical CVEs that appear in the news.
"""

import logging
import os
from datetime import datetime, timezone, timedelta

import httpx

from normalize import normalize_nvd, apply_vendor_hq
from models import insert_event

logger  = logging.getLogger(__name__)
NVD_KEY = os.getenv("NVD_API_KEY", "")
_URL    = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000")


def _extract_cvss(cve: dict) -> float | None:
    """Extract the best available CVSS base score from a CVE object."""
    for key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
        metrics = cve.get("metrics", {}).get(key, [])
        if metrics:
            base = metrics[0].get("cvssData", {}).get("baseScore")
            if base is not None:
                return float(base)
    return None


async def fetch_nvd(
    lookback_hours: int = 2,
    min_cvss: float | None = None,
) -> list[dict]:
    """
    Fetch NVD CVEs published in the last `lookback_hours`.
    If `min_cvss` is set, only events with CVSS >= that score are stored.

    Startup call uses lookback_hours=720, min_cvss=7.0 to backfill
    the last 30 days of newsworthy (High / Critical) CVEs.
    Recurring 2-hour jobs leave both params at defaults.
    """
    label = f"{lookback_hours}h window" + (f", CVSS ≥ {min_cvss}" if min_cvss else "")
    logger.info(f"Fetching NVD CVEs ({label})…")
    try:
        now   = datetime.now(timezone.utc)
        start = now - timedelta(hours=lookback_hours)

        headers = {"apiKey": NVD_KEY} if NVD_KEY else {}
        params: dict = {
            "pubStartDate":   _fmt(start),
            "pubEndDate":     _fmt(now),
            "resultsPerPage": 2000,
        }
        # NVD API severity filter (reduces payload for long lookbacks)
        if min_cvss is not None and min_cvss >= 9.0:
            params["cvssV3Severity"] = "CRITICAL"
        elif min_cvss is not None and min_cvss >= 7.0:
            params["cvssV3Severity"] = "HIGH"   # includes CRITICAL too

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        new: list[dict] = []
        for item in data.get("vulnerabilities", []):
            cve   = item.get("cve", {})
            # Client-side double-check in case API doesn't filter perfectly
            if min_cvss is not None:
                score = _extract_cvss(cve)
                if score is None or score < min_cvss:
                    continue
            event = normalize_nvd(cve)
            # Apply vendor HQ geo-mapping so named-vendor CVEs appear on globe
            apply_vendor_hq(event, event.get("description", ""))
            if insert_event(event):
                new.append(event)

        logger.info(f"NVD: {len(new)} new events ({label})")
        return new

    except Exception as exc:
        logger.error(f"NVD fetch failed: {exc}")
        return []
