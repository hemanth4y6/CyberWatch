"""
feeds/infosecmag.py — Infosecurity Magazine RSS feed.

Refreshes every 30 minutes. Provides broad coverage of global
cybersecurity news including Middle East, geopolitical cyber
conflicts, and enterprise security incidents.
"""

import logging
from feeds.rss_base import ingest_and_store

logger = logging.getLogger(__name__)

RSS_URL   = "https://www.infosecurity-magazine.com/rss/news/"
FEED_NAME = "infosecmag_rss"


async def fetch_infosecmag() -> list[dict]:
    """Fetch Infosecurity Magazine RSS and return new events."""
    logger.info(f"[{FEED_NAME}] fetching …")
    return await ingest_and_store(RSS_URL, FEED_NAME)
