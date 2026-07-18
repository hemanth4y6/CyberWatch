"""
enrichment/geo.py — Batch IP geolocation via ip-api.com.

Only batch endpoint is used — no per-event calls anywhere.
Rate limit: 100 IPs per POST, 45 requests/min on free tier.

max_ips guard: callers can cap how many IPs are resolved per
cycle to avoid blowing through the rate limit on startup when
all 6 feeds fire simultaneously (AbuseIPDB alone returns 10k IPs).
"""

import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

_GEO_URL = "http://ip-api.com/batch"


async def batch_geo_lookup(
    ips: list[str],
    max_ips: int = 200,
) -> dict[str, dict]:
    """
    Resolve a list of IPs → {ip: {lat, lng, country}}.
    Deduplicates first, takes at most `max_ips` unique IPs,
    then chunks into 100-IP batches with 1.5 s between chunks
    to stay within ip-api.com's 45 req/min free-tier limit.
    """
    if not ips:
        return {}

    unique = list(set(ips))[:max_ips]          # cap per-call to avoid rate exhaustion
    chunks = [unique[i : i + 100] for i in range(0, len(unique), 100)]
    results: dict[str, dict] = {}

    async with httpx.AsyncClient(timeout=20.0) as client:
        for i, chunk in enumerate(chunks):
            if i > 0:
                await asyncio.sleep(1.5)       # ~40 req/min headroom for concurrent feeds
            try:
                payload = [{"query": ip} for ip in chunk]
                resp = await client.post(_GEO_URL, json=payload)
                resp.raise_for_status()
                for entry in resp.json():
                    if entry.get("status") == "success":
                        results[entry["query"]] = {
                            "lat":     entry["lat"],
                            "lng":     entry["lon"],
                            "country": entry["countryCode"],
                        }
            except Exception as exc:
                logger.warning(f"Geo batch chunk failed: {exc}")

    return results

COUNTRY_CENTROIDS = {
    # North America
    "US": (37.09, -95.71),  "CA": (56.13, -106.34), "MX": (23.63, -102.55),
    # Europe
    "RU": (61.52, 105.32),  "DE": (51.16, 10.45),   "GB": (55.37, -3.43),
    "FR": (46.23, 2.21),    "UA": (48.37, 31.16),   "PL": (51.91, 19.14),
    "NL": (52.13, 5.29),    "IT": (41.87, 12.56),   "ES": (40.46, -3.74),
    # Asia-Pacific
    "CN": (35.86, 104.19),  "JP": (36.20, 138.25),  "KR": (35.90, 127.76),
    "IN": (20.59, 78.96),   "KP": (40.33, 127.51),  "TW": (23.70, 120.96),
    "AU": (-25.27, 133.77), "SG": (1.35, 103.82),   "ID": (-0.79, 113.92),
    "PH": (12.88, 121.77),  "VN": (14.06, 108.28),  "TH": (15.87, 100.99),
    "PK": (30.37, 69.34),   "MY": (4.21, 101.97),
    # Middle East
    "IR": (32.42, 53.68),   "IL": (31.04, 34.85),   "PS": (31.95, 35.20),
    "LB": (33.85, 35.86),   "SY": (34.80, 38.99),   "IQ": (33.22, 43.68),
    "YE": (15.55, 48.51),   "JO": (30.58, 36.23),   "SA": (23.88, 45.07),
    "AE": (23.42, 53.84),   "QA": (25.35, 51.18),   "BH": (26.07, 50.55),
    "EG": (26.82, 30.80),   "TR": (38.96, 35.24),
    # South America
    "BR": (-14.23, -51.92),
    # Africa
    "NG": (9.08, 8.67),     "ZA": (-30.56, 22.94),
}

def apply_centroids(event):
    for prefix in ("source", "target"):
        if event.get(f"{prefix}_country") and not event.get(f"{prefix}_lat"):
            coords = COUNTRY_CENTROIDS.get(event[f"{prefix}_country"])
            if coords:
                event[f"{prefix}_lat"] = coords[0]
                event[f"{prefix}_lng"] = coords[1]
    return event

