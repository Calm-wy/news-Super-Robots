"""Claude-powered enrichment: summary + classification + importance.

Design:
- One API call per news item (Haiku 4.5 default; escalate to Sonnet 4.6 when
  keyword-boost signals a high-value story).
- Extended thinking OFF (not needed for 2-3 sentence summaries).
- Structured tool_use output ensures valid JSON.
- Prompt caching on the (large, static) system prompt keeps cost down.

The env var ANTHROPIC_API_KEY must be set. If not, `enrich_items()` returns
the input list unchanged and logs a warning — so the pipeline still ships
raw titles when the key is absent.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Iterable

from anthropic import Anthropic
from anthropic import APIError
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from collectors.base import load_yaml

log = logging.getLogger(__name__)

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"

_client: Anthropic | None = None


def _get_client() -> Anthropic | None:
    global _client
    if _client is not None:
        return _client
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    _client = Anthropic(api_key=key)
    return _client


# ---------- prompt construction ----------

def _build_system_prompt() -> list[dict]:
    """Return a system prompt with prompt caching on the large static block."""
    companies_cfg = load_yaml("companies.yaml")
    keywords_cfg = load_yaml("keywords.yaml")

    company_lines = []
    for c in companies_cfg["companies"]:
        aliases = ", ".join(c["aliases"][:6])
        company_lines.append(f'- {c["id"]}: {c["name_zh"]} / {c["name_en"]} ({aliases})')
    company_block = "\n".join(company_lines)

    boost_lines = []
    for cat, spec in keywords_cfg.get("category_boost", {}).items():
        kw = ", ".join(spec["keywords"][:8])
        boost_lines.append(f"- {cat}: {kw}")
    boost_block = "\n".join(boost_lines)

    static_block = f"""You are an expert autonomous-driving industry analyst.

You will be given a single news article (title + excerpt). Your job:
1. Write a concise 2-3 sentence Chinese (繁體) summary — factual, no fluff.
2. Identify which of the tracked companies the article is about.
3. Classify into one of: announcement, funding, incident, launch, layoff, hiring,
   partnership, regulation, product, opinion, other.
4. Score importance 1-5 (1 = trivial, 5 = major industry news).
5. Detect sentiment: positive, neutral, negative.

Tracked companies:
{company_block}

Event categories (used for boosted importance):
{boost_block}

Rules:
- If title/excerpt only mentions a company in passing, do not add it.
- Chinese summary must be neutral, third-person, no marketing tone.
- If article is off-topic (not L4/robotaxi related), set importance=1 and category="other".
"""
    return [
        {
            "type": "text",
            "text": static_block,
            "cache_control": {"type": "ephemeral"},
        }
    ]


ENRICH_TOOL = {
    "name": "record_analysis",
    "description": "Record your analysis of the news article.",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary_zh": {
                "type": "string",
                "description": "2-3 sentence Chinese (traditional) summary of the article.",
            },
            "companies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Company ids from the tracked list, only real subjects of the article.",
            },
            "category": {
                "type": "string",
                "enum": [
                    "announcement", "funding", "incident", "launch", "layoff",
                    "hiring", "partnership", "regulation", "product", "opinion", "other",
                ],
            },
            "importance": {
                "type": "integer",
                "minimum": 1,
                "maximum": 5,
            },
            "sentiment": {"type": "string", "enum": ["positive", "neutral", "negative"]},
        },
        "required": ["summary_zh", "companies", "category", "importance", "sentiment"],
    },
}


def _pick_model(item: dict) -> str:
    """Escalate to Sonnet for likely-high-value stories."""
    text = (item.get("title", "") + " " + item.get("excerpt", "")).lower()
    hot = ("funding", "raise", "series", "ipo", "融資", "融资", "上市",
           "accident", "crash", "事故", "召回", "recall", "layoff", "裁員", "裁员")
    if any(h in text for h in hot):
        return SONNET
    return HAIKU


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=1, max=10),
    reraise=True,
)
def _call_claude(client: Anthropic, model: str, system: list[dict], user_text: str) -> dict:
    resp = client.messages.create(
        model=model,
        max_tokens=800,
        system=system,
        tools=[ENRICH_TOOL],
        tool_choice={"type": "tool", "name": "record_analysis"},
        messages=[{"role": "user", "content": user_text}],
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "record_analysis":
            return dict(block.input)
    raise RuntimeError("Claude did not call record_analysis tool")


# ---------- public API ----------

def enrich_items(items: list[dict]) -> list[dict]:
    """Attach summary_zh / category / importance / sentiment to each item."""
    client = _get_client()
    if client is None:
        log.warning("ANTHROPIC_API_KEY not set. Returning items without enrichment.")
        for it in items:
            it.setdefault("summary_zh", it.get("excerpt", "")[:200])
            it.setdefault("category", "other")
            it.setdefault("importance", 2)
            it.setdefault("sentiment", "neutral")
        return items

    system = _build_system_prompt()
    out: list[dict] = []
    for i, item in enumerate(items, 1):
        user_text = (
            f"Title: {item['title']}\n"
            f"Source: {item['source']} ({item['category']}, {item['lang']})\n"
            f"URL: {item['url']}\n"
            f"Excerpt: {item.get('excerpt', '')}\n"
        )
        model = _pick_model(item)
        try:
            analysis = _call_claude(client, model, system, user_text)
        except APIError as e:
            log.warning("API error on item %d (%s): %s", i, item["url"], e)
            analysis = {
                "summary_zh": item.get("excerpt", "")[:200],
                "companies": item.get("company_ids", []),
                "category": "other",
                "importance": 2,
                "sentiment": "neutral",
            }

        # merge, preferring existing company_ids if regex already found them
        merged_companies = sorted(set(item.get("company_ids", []) + analysis.get("companies", [])))
        item.update({
            "summary_zh": analysis["summary_zh"],
            "category_llm": analysis["category"],
            "importance": int(analysis["importance"]),
            "sentiment": analysis["sentiment"],
            "company_ids": merged_companies,
            "model_used": model,
        })
        out.append(item)
        if i % 10 == 0:
            log.info("Enriched %d/%d", i, len(items))
    log.info("Enrichment done: %d items", len(out))
    return out
