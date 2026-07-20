"""Shared building blocks for all collectors.

A NewsItem is the common shape all collectors produce.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import yaml
from dateutil import parser as dateparser

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"


@dataclass
class NewsItem:
    id: str                        # sha1(url) — deterministic dedup key
    title: str
    url: str
    source: str                    # human-readable feed/site name
    category: str                  # official | tech_media | social | capital
    lang: str                      # zh | en
    published_at: str              # ISO 8601 UTC
    excerpt: str = ""              # first ~500 chars, before LLM summarization
    company_ids: list[str] = field(default_factory=list)  # matched companies
    source_weight: int = 3
    raw: dict = field(default_factory=dict)  # anything extra a collector wants to keep

    def to_dict(self) -> dict:
        return asdict(self)


def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def hash_url(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def normalize_date(raw: str | datetime | None) -> str:
    """Return ISO 8601 UTC. Falls back to now() if unparseable."""
    if raw is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(raw, datetime):
        dt = raw
    else:
        try:
            dt = dateparser.parse(raw)
        except (ValueError, TypeError):
            return datetime.now(timezone.utc).isoformat()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def match_companies(text: str, companies_cfg: dict) -> list[str]:
    """Return list of company ids whose aliases appear in text (case-insensitive)."""
    if not text:
        return []
    lower = text.lower()
    hits: list[str] = []
    for c in companies_cfg["companies"]:
        for alias in c["aliases"]:
            if alias.lower() in lower:
                hits.append(c["id"])
                break
    return hits


def keyword_match(text: str, keywords_cfg: dict) -> bool:
    """True if any primary keyword matches (either language)."""
    if not text:
        return False
    lower = text.lower()
    for lang in ("zh", "en"):
        for kw in keywords_cfg.get("primary_keywords", {}).get(lang, []):
            if kw.lower() in lower:
                return True
    return False


_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(html: str, max_len: int = 500) -> str:
    if not html:
        return ""
    txt = _TAG_RE.sub(" ", html)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:max_len]


def dedup(items: Iterable[NewsItem]) -> list[NewsItem]:
    """Deduplicate by NewsItem.id, keeping first occurrence."""
    seen: set[str] = set()
    out: list[NewsItem] = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        out.append(item)
    return out
