"""
enrichment/firecrawl.py — Firecrawl enrichment layer.

Two jobs:
  1. scrape_threat_news()      — threat news sites every 12 h
  2. enrich_high_severity_events() — CVE write-ups for CVSS >= 7.0 events

Hard cap: 20 enrichments/day to stay within 500 credit/month free tier.
Cache: enriched events have enriched=1; cve_id already enriched is never rescrapped.
"""

import json
import logging
import os

from models import get_connection

logger = logging.getLogger(__name__)

FIRECRAWL_KEY = os.getenv("FIRECRAWL_API_KEY", "")
MAX_DAILY     = 20

_NEWS_SITES = [
    "https://therecord.media",
    "https://www.bleepingcomputer.com",
    "https://cyber.gc.ca",
    "https://attackerkb.com",
    "https://www.greynoise.io/blog",
]

_daily_count: int = 0


def reset_daily_counter() -> None:
    global _daily_count
    _daily_count = 0
    logger.info("Firecrawl daily enrichment counter reset")


async def scrape_threat_news() -> None:
    """Job 1: scrape threat news sites — one request per site per 12-h cycle."""
    if not FIRECRAWL_KEY:
        return
    try:
        from firecrawl import FirecrawlApp  # lazy import
        app = FirecrawlApp(api_key=FIRECRAWL_KEY)
        for site in _NEWS_SITES:
            try:
                result = app.scrape_url(site, params={"formats": ["markdown"]})
                logger.info(f"Firecrawl scraped {site}: {len(result.get('markdown',''))} chars")
            except Exception as exc:
                logger.warning(f"Firecrawl failed for {site}: {exc}")
    except Exception as exc:
        logger.error(f"Firecrawl news scrape job error: {exc}")


async def enrich_high_severity_events() -> None:
    """Job 2: enrich CVSS >= 7.0 events with CVE write-ups. Max 20 jobs/day."""
    global _daily_count
    if not FIRECRAWL_KEY or _daily_count >= MAX_DAILY:
        return

    # Fetch rows and close the connection BEFORE the async enrichment loop.
    # fetchall() materialises all results into memory, so closing here is safe.
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, cve_id FROM events "
            "WHERE cvss_score >= 7.0 AND enriched = 0 AND cve_id IS NOT NULL "
            "LIMIT 5"
        ).fetchall()
    finally:
        conn.close()  # connection released before any async I/O begins

    for row in rows:
        if _daily_count >= MAX_DAILY:
            break
        await _enrich_event(row["id"], row["cve_id"])
        _daily_count += 1


async def _enrich_event(event_id: str, cve_id_or_url: str) -> None:
    """
    Enrich a single event via Firecrawl.

    If `cve_id_or_url` looks like a CVE ID (starts with 'CVE-'), the NVD detail
    page is scraped. Otherwise it is treated as a direct URL (used for watchlist-hit
    news articles where source_url is available).
    """
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_KEY)

        if cve_id_or_url.upper().startswith("CVE-"):
            url = f"https://nvd.nist.gov/vuln/detail/{cve_id_or_url}"
        else:
            url = cve_id_or_url  # direct article URL from watchlist hit

        result = app.scrape_url(url, params={"formats": ["markdown"]})

        conn = get_connection()
        conn.execute(
            "UPDATE events SET enriched = 1, enrichment = ? WHERE id = ?",
            (json.dumps({"content": result.get("markdown", "")[:2000]}), event_id),
        )
        conn.commit()
        conn.close()
        logger.info(f"Enriched event {event_id} ({cve_id_or_url})")
    except Exception as exc:
        logger.error(f"Firecrawl enrich failed for {event_id}: {exc}")

