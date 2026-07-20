"""Daily pipeline entry point.

    python scripts/run_daily.py             # full pipeline: collect → enrich → dump
    python scripts/run_daily.py --collect-only
    python scripts/run_daily.py --skip-enrich  # alias for --collect-only
    python scripts/run_daily.py --date 2026-07-19  # reprocess a specific day
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.base import DATA_DIR, dedup  # noqa: E402
from collectors.rss import collect_rss  # noqa: E402
from collectors.official import collect_official  # noqa: E402
from collectors.social import collect_social  # noqa: E402
from collectors.capital import collect_capital  # noqa: E402

log = logging.getLogger("run_daily")


def _today_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)
    log.info("Wrote %s (%d items)", path, len(obj) if isinstance(obj, list) else 1)


def collect_all(target_date: str) -> list[dict]:
    """Run every collector and return deduped NewsItem dicts."""
    log.info("=== Collect phase (target date %s) ===", target_date)
    items = []
    items.extend(collect_rss())
    items.extend(collect_official())
    items.extend(collect_social())
    items.extend(collect_capital())
    items = dedup(items)
    log.info("Collected %d unique items", len(items))
    return [i.to_dict() for i in items]


def build_latest(days: int = 30) -> None:
    """Merge last N days of enriched news into data/latest.json."""
    news_dir = DATA_DIR / "news"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    merged: list[dict] = []
    for f in sorted(news_dir.glob("*.json"), reverse=True):
        if f.name.startswith("."):
            continue
        try:
            day_iso = f.stem
            day_dt = datetime.strptime(day_iso, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if day_dt < cutoff:
            continue
        with open(f, "r", encoding="utf-8") as fh:
            merged.extend(json.load(fh))
    # sort by published_at desc, then importance desc
    merged.sort(
        key=lambda x: (x.get("published_at", ""), x.get("importance", 0)),
        reverse=True,
    )
    _write_json(DATA_DIR / "latest.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(merged),
        "items": merged,
    })


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=_today_iso(), help="target date, YYYY-MM-DD (default: today)")
    p.add_argument("--collect-only", action="store_true", help="skip Claude enrichment")
    p.add_argument("--skip-enrich", action="store_true", help="alias for --collect-only")
    p.add_argument("--enrich-only", action="store_true", help="run enrichment on existing raw file")
    args = p.parse_args()

    raw_path = DATA_DIR / "raw" / f"{args.date}.json"
    news_path = DATA_DIR / "news" / f"{args.date}.json"

    if args.enrich_only:
        if not raw_path.exists():
            log.error("No raw file at %s", raw_path)
            return 1
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_items = json.load(f)
    else:
        raw_items = collect_all(args.date)
        _write_json(raw_path, raw_items)

    if args.collect_only or args.skip_enrich:
        log.info("Collect-only: skipping enrichment.")
        return 0

    # Enrichment (imported lazily so `--collect-only` doesn't require anthropic to be installed)
    from enrich.summarize import enrich_items  # noqa: WPS433

    log.info("=== Enrich phase (%d items) ===", len(raw_items))
    enriched = enrich_items(raw_items)
    _write_json(news_path, enriched)

    log.info("=== Build latest.json ===")
    build_latest()
    log.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
