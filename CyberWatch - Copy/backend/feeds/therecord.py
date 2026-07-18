"""
feeds/therecord.py — The Record by Recorded Future RSS feed.

Refreshes every 30 minutes. Focuses on nation-state attacks, named threat
actors, and geopolitically significant cyber incidents.
"""

import logging
from feeds.rss_base import ingest_and_store

logger = logging.getLogger(__name__)

RSS_URL   = "https://therecord.media/feed"
FEED_NAME = "therecord_rss"


async def fetch_therecord() -> list[dict]:
    """Fetch The Record RSS and return new events."""
    logger.info(f"[{FEED_NAME}] fetching …")
    return await ingest_and_store(RSS_URL, FEED_NAME)
