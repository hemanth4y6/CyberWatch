"""
feeds/krebs.py — KrebsOnSecurity RSS feed.

Refreshes every 2 hours. Known for high-quality, named-victim reporting
on major breaches, fraud, and cybercrime.
"""

import logging
from feeds.rss_base import ingest_and_store

logger = logging.getLogger(__name__)

RSS_URL   = "https://krebsonsecurity.com/feed/"
FEED_NAME = "krebs_rss"


async def fetch_krebs() -> list[dict]:
    """Fetch KrebsOnSecurity RSS and return new events."""
    logger.info(f"[{FEED_NAME}] fetching …")
    return await ingest_and_store(RSS_URL, FEED_NAME)
