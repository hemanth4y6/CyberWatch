"""
feeds/rss_base.py — Shared RSS parser for all news-based threat feeds.

Parses RSS entries into the common CyberWatch event schema. Performs:
  - Attack type inference from article text keywords
  - Severity inference from article text keywords
  - Country extraction (target and source/threat-actor)
  - CVE ID extraction via regex
  - Centroid lat/lng resolution for known countries
  - Near-duplicate clustering (Jaccard token overlap)
  - Optional LLM pre-filtering via Groq (LLM_PREFILTER_ENABLED=true)
  - Watchlist keyword escalation & immediate Firecrawl trigger
"""

import asyncio
import feedparser
import hashlib
import logging
import os
import re
from datetime import datetime, timezone

import httpx

from models import insert_event, get_connection
from enrichment.geo import apply_centroids
from normalize import apply_watchlist, apply_vendor_hq

logger = logging.getLogger(__name__)

# ── Env config ────────────────────────────────────────────────────────────────

_LLM_PREFILTER_ENABLED = os.getenv("LLM_PREFILTER_ENABLED", "false").lower() == "true"
_LLM_FILTER_MIN_SCORE  = int(os.getenv("LLM_FILTER_SCORE_MIN", "6"))   # 1-10 threshold
_GROQ_API_KEY          = os.getenv("GROQ_API_KEY", "")
_GROQ_MODEL            = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# ── Keyword tables ─────────────────────────────────────────────────────────────

ATTACK_TYPE_KEYWORDS = {
    "Ransomware":   ["ransomware", "lockbit", "blackcat", "cl0p", "alphv", "encrypted files",
                     "blackmatter", "conti", "revil", "sodinokibi", "ryuk", "ransom demand"],
    "Phishing":     ["phishing", "spear-phishing", "credential", "spoofed", "spearphishing",
                     "business email compromise", "bec", "pretexting"],
    "DDoS":         ["ddos", "denial of service", "flood", "botnet", "overloaded",
                     "traffic flood", "layer 7", "volumetric attack"],
    "Exploit":      ["exploit", "zero-day", "0-day", "vulnerability", "cve", "patch",
                     "proof-of-concept", "poc", "remote code execution", "rce",
                     "privilege escalation", "sql injection", "buffer overflow"],
    "Malware":      ["malware", "trojan", "backdoor", "wiper", "infostealer", "spyware",
                     "rootkit", "keylogger", "remote access trojan", "rat", "loader"],
    "Data Breach":  ["breach", "leaked", "stolen data", "exfiltrated", "exposed records",
                     "data dump", "database exposed", "millions of records", "personal data exposed",
                     "sensitive information leaked"],
    "Brute Force":  ["brute force", "credential stuffing", "password spray", "account takeover"],
}

SEVERITY_FROM_KEYWORDS = {
    "Critical": ["critical infrastructure", "hospital", "government", "zero-day",
                 "nation-state", "actively exploited", "military", "power grid",
                 "water treatment", "election", "nuclear", "supply chain attack"],
    "High":     ["ransomware", "data breach", "exploit", "financial", "bank",
                 "healthcare", "university", "school district", "law enforcement"],
    "Medium":   ["phishing", "malware", "botnet", "credential"],
}

COUNTRY_MENTIONS = {
    "united states": "US", "u.s.": "US", "u.s": "US", "american": "US", "america": "US",
    "russia":        "RU", "russian": "RU",
    "china":         "CN", "chinese": "CN",
    "iran":          "IR", "iranian": "IR",
    "north korea":   "KP", "dprk": "KP", "north korean": "KP",
    "ukraine":       "UA", "ukrainian": "UA",
    "united kingdom":"GB", "u.k.": "GB", "british": "GB", "england": "GB",
    "germany":       "DE", "german": "DE",
    "france":        "FR", "french": "FR",
    "japan":         "JP", "japanese": "JP",
    "australia":     "AU", "australian": "AU",
    "india":         "IN", "indian": "IN",
    "israel":        "IL", "israeli": "IL",
    "canada":        "CA", "canadian": "CA",
    "netherlands":   "NL", "dutch": "NL",
    "brazil":        "BR", "brazilian": "BR",
    "south korea":   "KR", "korean": "KR",
    "taiwan":        "TW", "taiwanese": "TW",
    "poland":        "PL", "polish": "PL",
    "italy":         "IT", "italian": "IT",
    "spain":         "ES", "spanish": "ES",
    # Middle East & conflict regions
    "palestine":     "PS", "palestinian": "PS", "gaza": "PS", "west bank": "PS",
    "lebanon":       "LB", "lebanese": "LB",
    "syria":         "SY", "syrian": "SY",
    "iraq":          "IQ", "iraqi": "IQ",
    "yemen":         "YE", "yemeni": "YE",
    "jordan":        "JO", "jordanian": "JO",
    "saudi arabia":  "SA", "saudi": "SA",
    "uae":           "AE", "emirates": "AE", "emirati": "AE",
    "qatar":         "QA", "qatari": "QA",
    "bahrain":       "BH", "bahraini": "BH",
    "egypt":         "EG", "egyptian": "EG",
    "turkey":        "TR", "turkish": "TR",
    "pakistan":       "PK", "pakistani": "PK",
    # Additional countries
    "mexico":        "MX", "mexican": "MX",
    "singapore":     "SG", "singaporean": "SG",
    "indonesia":     "ID", "indonesian": "ID",
    "philippines":   "PH", "filipino": "PH",
    "vietnam":       "VN", "vietnamese": "VN",
    "thailand":      "TH", "thai": "TH",
    "nigeria":       "NG", "nigerian": "NG",
    "south africa":  "ZA",
}

THREAT_ACTOR_COUNTRY = {
    # China
    "volt typhoon":   "CN", "apt41": "CN", "apt40": "CN", "apt10": "CN",
    "double dragon":  "CN", "winnti":  "CN", "hafnium": "CN", "bronze starlight": "CN",
    "salt typhoon":   "CN", "flax typhoon": "CN",
    # Russia
    "fancy bear":     "RU", "cozy bear": "RU", "sandworm": "RU",
    "apt28":          "RU", "apt29": "RU", "killnet": "RU", "gamaredon": "RU",
    "lockbit":        "RU", "cl0p": "RU", "blackcat": "RU", "alphv": "RU",
    "conti":          "RU", "darkside": "RU", "revil": "RU",
    "turla":          "RU", "star blizzard": "RU", "midnight blizzard": "RU",
    # North Korea
    "lazarus group":  "KP", "kimsuky": "KP", "andariel": "KP", "bluenoroff": "KP",
    # Iran — expanded
    "charming kitten":"IR", "apt35": "IR", "phosphorus": "IR", "muddy water": "IR",
    "muddywater":     "IR", "apt33": "IR", "apt34": "IR", "oilrig":   "IR",
    "magic hound":    "IR", "cotton sandstorm": "IR", "mint sandstorm": "IR",
    "imperial kitten": "IR", "crimson sandstorm": "IR", "peach sandstorm": "IR",
    # Palestinian-linked
    "arid viper":     "PS", "molerats": "PS",
    # Lebanon / Hezbollah-linked
    "volatile cedar": "LB", "lebanese cedar": "LB",
    # Turkey
    "sea turtle":     "TR",
}


# ── Inference helpers ──────────────────────────────────────────────────────────

def infer_attack_type(text: str) -> str:
    t = text.lower()
    for atype, kws in ATTACK_TYPE_KEYWORDS.items():
        if any(k in t for k in kws):
            return atype
    return "Unknown"


def infer_severity(text: str) -> str:
    t = text.lower()
    for sev, kws in SEVERITY_FROM_KEYWORDS.items():
        if any(k in t for k in kws):
            return sev
    return "Medium"


def extract_countries(text: str) -> tuple[str | None, str | None]:
    t = text.lower()
    # Source: check threat actor names first for an attributed country
    source = next(
        (code for phrase, code in THREAT_ACTOR_COUNTRY.items() if phrase in t),
        None
    )
    # Target: first country mention that isn't the same as source
    target = next(
        (code for phrase, code in COUNTRY_MENTIONS.items()
         if phrase in t and code != source),
        None
    )
    return source, target


def extract_cve(text: str) -> str | None:
    m = re.search(r'CVE-\d{4}-\d{4,7}', text, re.IGNORECASE)
    return m.group(0).upper() if m else None


# ── Deduplication ──────────────────────────────────────────────────────────────

def _tokenise(text: str) -> set[str]:
    """Lowercase word tokens, length ≥ 4 (skip noise words)."""
    return {w for w in re.findall(r'\b[a-z]{4,}\b', text.lower())}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _get_recent_descriptions(hours: int = 4) -> list[str]:
    """Pull descriptions from the last N hours for near-duplicate detection."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT description FROM events WHERE timestamp >= ? LIMIT 500",
            (cutoff,)
        ).fetchall()
        return [r["description"] for r in rows]
    finally:
        conn.close()


def _is_near_duplicate(new_desc: str, recent_descs: list[str], threshold: float = 0.72) -> bool:
    """Return True if any recent description is too similar (Jaccard ≥ threshold)."""
    tokens_new = _tokenise(new_desc)
    for old in recent_descs:
        if _jaccard(tokens_new, _tokenise(old)) >= threshold:
            return True
    return False


# ── LLM pre-filter ─────────────────────────────────────────────────────────────

async def _llm_impact_score(headline: str, summary: str) -> int:
    """
    Ask Groq to score the cybersecurity impact of an article on a 1-10 scale.
    Returns the score, or 10 (pass-through) on any error / API unavailability.

    Scoring guide sent to model:
      1-3  Generic advice, product release, marketing fluff, routine phishing tip
      4-5  Minor vulnerability, old patched issue, low-impact malware
      6-7  Significant named incident, high-severity CVE, notable breach
      8-9  Critical infrastructure, nation-state, zero-day, supply chain
      10   Imminent mass-exploitation, critical systemic threat
    """
    if not _GROQ_API_KEY:
        return 10  # no key → pass everything through

    prompt_text = (
        f"Headline: {headline[:200]}\n"
        f"Summary: {summary[:300]}\n\n"
        "Rate the cybersecurity impact of this article from 1 to 10 using this scale:\n"
        "1-3: generic advice, marketing, routine phishing tip, no named victim\n"
        "4-5: minor or already-patched vulnerability, low-stakes malware campaign\n"
        "6-7: significant named breach, high-severity CVE, notable ransomware hit\n"
        "8-9: critical infrastructure, nation-state attack, zero-day exploitation\n"
        "10: imminent mass-exploitation, systemic supply-chain or grid threat\n\n"
        'Respond with ONLY valid JSON: {"score": <integer 1-10>}'
    )
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {_GROQ_API_KEY}"},
                json={
                    "model": _GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a JSON-only API. Output only raw JSON."},
                        {"role": "user",   "content": prompt_text},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 16,
                },
            )
        if resp.status_code == 200:
            import json
            text = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            data = json.loads(text)
            score = int(data.get("score", 10))
            return max(1, min(10, score))
    except Exception as exc:
        logger.debug(f"LLM pre-filter error (will pass): {exc}")
    return 10  # fail open — never drop due to API failure


# ── Main parser ────────────────────────────────────────────────────────────────

def parse_rss_feed(url: str, feed_name: str, max_items: int = 50) -> list[dict]:
    """
    Fetch and parse an RSS feed URL.
    Returns a list of event dicts in the common CyberWatch schema.
    """
    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        logger.error(f"RSS parse error ({feed_name}): {exc}")
        return []

    events = []
    for entry in feed.entries[:max_items]:
        title   = entry.get("title", "")
        summary = entry.get("summary", "")
        full    = f"{title} {summary}"

        source_c, target_c = extract_countries(full)

        event = {
            "id":             hashlib.sha256(
                                  f"{feed_name}{entry.get('id', title)}".encode()
                              ).hexdigest()[:16],
            "timestamp":      _parse_ts(entry.get("published", "")),
            "attack_type":    infer_attack_type(full),
            "source_country": source_c,
            "target_country": target_c,
            "source_lat":     None,
            "source_lng":     None,
            "target_lat":     None,
            "target_lng":     None,
            "severity":       infer_severity(full),
            "cvss_score":     None,
            "cve_id":         extract_cve(full),
            "description":    title,
            "source_feed":    feed_name,
            "source_url":     entry.get("link", ""),
            "enriched":       False,
            "enrichment":     None,
            # Internal — stripped by insert_event via _ip pop pattern
            "_raw_summary":   summary,
        }

        apply_centroids(event)
        apply_vendor_hq(event, full)   # populates lat/lng for CVE vendor mentions
        events.append(event)

    return events


async def ingest_and_store(url: str, feed_name: str) -> list[dict]:
    """
    Parse an RSS feed, optionally LLM-filter and dedup, insert new events,
    and return only the genuinely new events (for WebSocket broadcast).

    Pipeline per article:
      1. Parse RSS → event dict
      2. Near-duplicate check against last 4h of DB descriptions
      3. LLM impact score (if LLM_PREFILTER_ENABLED=true) — drop if below threshold
      4. Apply watchlist escalation (severity → Critical + immediate Firecrawl)
      5. Insert into DB (INSERT OR IGNORE handles exact-ID dedup)
    """
    events = parse_rss_feed(url, feed_name)
    if not events:
        logger.info(f"[{feed_name}] fetched 0 items, 0 new stored")
        return []

    # Fetch recent descriptions once for the whole batch (avoid N+1 queries)
    recent_descs = _get_recent_descriptions(hours=4)

    new_events = []
    inserted = skipped_dedup = skipped_llm = 0

    for ev in events:
        full_text = f"{ev['description']} {ev.get('_raw_summary', '')}"

        # ── Step 2: Near-duplicate check ──────────────────────────────────────
        if _is_near_duplicate(ev["description"], recent_descs):
            skipped_dedup += 1
            continue

        # ── Step 3: LLM pre-filter ─────────────────────────────────────────────
        if _LLM_PREFILTER_ENABLED:
            score = await _llm_impact_score(ev["description"], ev.get("_raw_summary", ""))
            if score < _LLM_FILTER_MIN_SCORE:
                logger.debug(f"[{feed_name}] LLM dropped (score={score}): {ev['description'][:60]}")
                skipped_llm += 1
                continue

        # ── Step 4: Watchlist escalation ───────────────────────────────────────
        apply_watchlist(ev, full_text)

        # Strip internal-only key before DB insert
        watchlist_hit = ev.pop("_watchlist_hit", False)
        ev.pop("_raw_summary", None)

        # ── Step 5: Insert ─────────────────────────────────────────────────────
        if insert_event(ev):
            new_events.append(ev)
            inserted += 1
            recent_descs.append(ev["description"])  # update local cache to catch intra-batch dups

            # Immediate Firecrawl enrichment for watchlist hits
            if watchlist_hit and ev.get("source_url") and os.getenv("FIRECRAWL_API_KEY"):
                asyncio.create_task(_immediate_enrich(ev["id"], ev["source_url"]))

    logger.info(
        f"[{feed_name}] fetched {len(events)} items, "
        f"{inserted} new stored | "
        f"dedup-skipped={skipped_dedup} llm-skipped={skipped_llm}"
    )
    return new_events


async def _immediate_enrich(event_id: str, url: str) -> None:
    """Fire-and-forget Firecrawl enrichment for watchlist-hit events."""
    try:
        from enrichment.firecrawl import _enrich_event
        logger.info(f"Watchlist hit — immediate Firecrawl enrich for {event_id}")
        await _enrich_event(event_id, url)
    except Exception as exc:
        logger.warning(f"Immediate enrichment failed for {event_id}: {exc}")


def _parse_ts(ts_str: str) -> str:
    """Try to parse a feedparser timestamp string; fall back to now."""
    if not ts_str:
        return datetime.now(timezone.utc).isoformat()
    try:
        import email.utils
        tt = email.utils.parsedate_to_datetime(ts_str)
        return tt.isoformat()
    except Exception:
        pass
    try:
        return datetime.fromisoformat(ts_str).isoformat()
    except Exception:
        pass
    return datetime.now(timezone.utc).isoformat()
