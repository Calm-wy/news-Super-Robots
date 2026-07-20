"""Social media collector — placeholder.

The dashboard's original spec includes Twitter/X, 微博, 小紅書 signals.
These platforms all require either:
  - Authenticated API access (paid Twitter API, Weibo open platform),
  - Or scraping via a maintained proxy layer (Nitter for X, RSSHub for 微博).

Rather than baking one brittle scraper in, this module is a stub that
provides two integration paths:

1. Add Nitter/RSSHub feeds to config/feeds.yaml (recommended, zero code).
   Example:
     - name: Waymo Twitter (via Nitter)
       url: https://nitter.net/waymo/rss
       category: social
       lang: en
       company: waymo
       weight: 3

2. Fill collect_social() below with direct API calls when you have keys.
   Set env vars in .env / GitHub Secrets, then implement the fetch here.
"""
from __future__ import annotations

import logging

from .base import NewsItem

log = logging.getLogger(__name__)


def collect_social() -> list[NewsItem]:
    """Return social-media NewsItems. Currently a no-op stub."""
    log.info("collect_social: stub (add Nitter/RSSHub feeds to feeds.yaml, or implement API calls here)")
    return []
