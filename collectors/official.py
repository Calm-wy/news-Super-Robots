"""Generic HTML scraper for company newsrooms that don't publish RSS.

Config-driven: config/newsrooms.yaml lists site + CSS selectors.
Each site produces NewsItem entries tagged with the given company id.

Selectors are intentionally lenient — a broken selector logs a warning
but never breaks the whole pipeline. If a site changes structure, only
the selectors need updating.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import (
    NewsItem,
    hash_url,
    load_yaml,
    normalize_date,
    strip_html,
)

log = logging.getLogger(__name__)

HTTP_TIMEOUT = 20
UA = "RobotaxiDashboardBot/1.0 (+https://github.com/)"


def _fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": UA})
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("HTTP failed %s: %s", url, e)
        return None
    return BeautifulSoup(resp.text, "lxml")


def _scrape_one(site: dict) -> list[NewsItem]:
    soup = _fetch(site["url"])
    if soup is None:
        return []
    items: list[NewsItem] = []
    for entry in soup.select(site["item_selector"])[: site.get("limit", 20)]:
        link_el = entry.select_one(site.get("link_selector", "a"))
        title_el = entry.select_one(site.get("title_selector", site.get("link_selector", "a")))
        if not link_el or not title_el:
            continue
        href = link_el.get("href", "").strip()
        if not href:
            continue
        url = urljoin(site["url"], href)
        title = title_el.get_text(" ", strip=True)
        if not title:
            continue

        date_str = ""
        if "date_selector" in site:
            date_el = entry.select_one(site["date_selector"])
            if date_el:
                date_str = date_el.get("datetime") or date_el.get_text(" ", strip=True)

        excerpt = ""
        if "excerpt_selector" in site:
            ex_el = entry.select_one(site["excerpt_selector"])
            if ex_el:
                excerpt = strip_html(str(ex_el))

        items.append(
            NewsItem(
                id=hash_url(url),
                title=title,
                url=url,
                source=site["name"],
                category="official",
                lang=site.get("lang", "en"),
                published_at=normalize_date(date_str) if date_str else normalize_date(None),
                excerpt=excerpt,
                company_ids=[site["company"]],
                source_weight=site.get("weight", 5),
            )
        )
    log.info("Scraped %s: %d items", site["name"], len(items))
    return items


def collect_official(max_workers: int = 6) -> list[NewsItem]:
    try:
        cfg = load_yaml("newsrooms.yaml")
    except FileNotFoundError:
        log.info("No newsrooms.yaml, skipping official HTML scraper")
        return []

    all_items: list[NewsItem] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_scrape_one, s) for s in cfg.get("sites", [])]
        for fut in as_completed(futures):
            try:
                all_items.extend(fut.result())
            except Exception as e:
                log.exception("Scrape crashed: %s", e)
    return all_items
