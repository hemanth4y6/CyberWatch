"""
feeds/darkreading.py — Dark Reading RSS feed.

Refreshes every 30 minutes.
"""

import logging
from feeds.rss_base import ingest_and_store

logger = logging.getLogger(__name__)

RSS_URL   = "https://www.darkreading.com/rss.xml"
FEED_NAME = "darkreading_rss"


async def fetch_darkreading() -> list[dict]:
    """Fetch Dark Reading RSS and return new events."""
    logger.info(f"[{FEED_NAME}] fetching …")
    return await ingest_and_store(RSS_URL, FEED_NAME)
