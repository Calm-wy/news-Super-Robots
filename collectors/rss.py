"""RSS/Atom feed collector.

Reads config/feeds.yaml and produces NewsItem objects filtered by
company match OR primary keyword match.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

import feedparser
import requests

from .base import (
    NewsItem,
    hash_url,
    keyword_match,
    load_yaml,
    match_companies,
    normalize_date,
    strip_html,
)

log = logging.getLogger(__name__)


HTTP_TIMEOUT = 20  # seconds per feed


def _fetch_one(feed: dict, companies_cfg: dict, keywords_cfg: dict) -> list[NewsItem]:
    url = feed["url"]
    log.info("Fetching %s", feed["name"])
    try:
        resp = requests.get(
            url,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": "RobotaxiDashboardBot/1.0 (+https://github.com/)"},
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("Feed %s HTTP failed: %s", feed["name"], e)
        return []

    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        log.warning("Feed %s parse failed: %s", feed["name"], parsed.bozo_exception)
        return []

    items: list[NewsItem] = []
    for entry in parsed.entries:
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            continue

        excerpt = strip_html(entry.get("summary", "") or entry.get("description", ""))
        text = f"{title} {excerpt}"

        matched = match_companies(text, companies_cfg)
        # Feed-level company override: e.g. an official Waymo blog. Always tag.
        if not matched and feed.get("company"):
            matched = [feed["company"]]

        # Keep an item only if it mentions a tracked company OR matches a primary keyword.
        if not matched and not keyword_match(text, keywords_cfg):
            continue

        published = entry.get("published") or entry.get("updated") or entry.get("pubDate")
        items.append(
            NewsItem(
                id=hash_url(link),
                title=title,
                url=link,
                source=feed["name"],
                category=feed.get("category", "tech_media"),
                lang=feed.get("lang", "en"),
                published_at=normalize_date(published),
                excerpt=excerpt,
                company_ids=matched,
                source_weight=feed.get("weight", 3),
            )
        )
    log.info("  → %s: %d items kept", feed["name"], len(items))
    return items


def collect_rss(max_workers: int = 8) -> list[NewsItem]:
    feeds_cfg = load_yaml("feeds.yaml")
    companies_cfg = load_yaml("companies.yaml")
    keywords_cfg = load_yaml("keywords.yaml")

    all_items: list[NewsItem] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(_fetch_one, feed, companies_cfg, keywords_cfg): feed
            for feed in feeds_cfg["feeds"]
        }
        for fut in as_completed(futures):
            feed = futures[fut]
            try:
                all_items.extend(fut.result())
            except Exception as e:
                log.exception("Feed %s crashed: %s", feed["name"], e)
    return all_items
