"""
feeds/cisa_advisories.py — CISA Cybersecurity Advisories RSS feed.

Refreshes every 2 hours. Official US government cybersecurity advisories —
ICS alerts, nation-state attribution, and critical infrastructure warnings.
All items are classified Critical severity by default (government advisory = confirmed threat).
Also applies vendor HQ geo-mapping so CVEs mentioning named vendors appear on the globe.
"""

import logging
from feeds.rss_base import parse_rss_feed
from models import insert_event
from enrichment.geo import apply_centroids
from normalize import apply_vendor_hq, apply_watchlist

logger = logging.getLogger(__name__)

RSS_URL   = "https://www.cisa.gov/cybersecurity-advisories/advisories.xml"
FEED_NAME = "cisa_advisories_rss"


async def fetch_cisa_advisories() -> list[dict]:
    """Fetch CISA Advisories RSS and return new events.
    
    All CISA advisories are forced to 'Critical' severity regardless
    of keyword inference — they are verified government-level warnings.
    Vendor HQ geo-mapping is applied so CVE advisories appear on the globe.
    """
    logger.info(f"[{FEED_NAME}] fetching …")
    events = parse_rss_feed(RSS_URL, FEED_NAME)

    new_events = []
    inserted = 0
    for ev in events:
        full_text = ev.get("description", "")

        # Government advisories are unconditionally Critical
        ev["severity"] = "Critical"

        # Apply geo: centroids first, then vendor HQ for any remaining missing coords
        apply_centroids(ev)
        apply_vendor_hq(ev, full_text)

        # Apply watchlist flag for immediate Firecrawl (watchlist_hit stripped below)
        apply_watchlist(ev, full_text)
        ev.pop("_watchlist_hit", None)   # CISA is already Critical; no extra action needed
        ev.pop("_raw_summary", None)

        if insert_event(ev):
            new_events.append(ev)
            inserted += 1

    logger.info(f"[{FEED_NAME}] fetched {len(events)} items, {inserted} new stored")
    return new_events
