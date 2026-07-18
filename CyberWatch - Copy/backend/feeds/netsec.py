"""
feeds/netsec.py — Reddit r/netsec RSS feed.

r/netsec is a community-curated, high-signal feed of real vulnerability
disclosures, tool releases, and incident reports — often surfaces CVEs and
novel attack techniques days before mainstream security news picks them up.

Refreshes every 60 minutes.
"""

import logging
from feeds.rss_base import ingest_and_store

logger = logging.getLogger(__name__)

RSS_URL   = "https://www.reddit.com/r/netsec.rss"
FEED_NAME = "netsec_rss"


async def fetch_netsec() -> list[dict]:
    """Fetch r/netsec RSS and return new events."""
    logger.info(f"[{FEED_NAME}] fetching …")
    return await ingest_and_store(RSS_URL, FEED_NAME)
