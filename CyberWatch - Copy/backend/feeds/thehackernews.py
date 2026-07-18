"""
feeds/thehackernews.py — The Hacker News RSS feed.

Refreshes every 30 minutes.
"""

import logging
from feeds.rss_base import ingest_and_store

logger = logging.getLogger(__name__)

RSS_URL   = "https://feeds.feedburner.com/TheHackersNews"
FEED_NAME = "thehackernews_rss"


async def fetch_thehackernews() -> list[dict]:
    """Fetch The Hacker News RSS and return new events."""
    logger.info(f"[{FEED_NAME}] fetching …")
    return await ingest_and_store(RSS_URL, FEED_NAME)
