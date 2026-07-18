"""
feeds/bleepingcomputer.py — BleepingComputer RSS feed.

Refreshes every 30 minutes. Covers ransomware attacks, malware campaigns,
named breaches, and actively exploited vulnerabilities.
"""

import logging
from feeds.rss_base import ingest_and_store

logger = logging.getLogger(__name__)

RSS_URL   = "https://www.bleepingcomputer.com/feed/"
FEED_NAME = "bleepingcomputer_rss"


async def fetch_bleepingcomputer() -> list[dict]:
    """Fetch BleepingComputer RSS and return new events."""
    logger.info(f"[{FEED_NAME}] fetching …")
    return await ingest_and_store(RSS_URL, FEED_NAME)
