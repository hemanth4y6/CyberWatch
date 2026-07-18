"""
feeds/github_advisory.py — GitHub Advisory Database Atom feed.

GitHub's own security advisory database publishes CVE disclosures
and package vulnerability reports in real-time — covering npm, PyPI,
Maven, Go, Rust, and more. Often the earliest public disclosure point
for library/supply-chain vulnerabilities.

Refreshes every 60 minutes.
"""

import logging
from feeds.rss_base import ingest_and_store

logger = logging.getLogger(__name__)

# GitHub Advisory Database public Atom feed
RSS_URL   = "https://github.com/advisories.atom"
FEED_NAME = "github_advisory_rss"


async def fetch_github_advisory() -> list[dict]:
    """Fetch GitHub Advisory Database Atom feed and return new events."""
    logger.info(f"[{FEED_NAME}] fetching …")
    return await ingest_and_store(RSS_URL, FEED_NAME)
