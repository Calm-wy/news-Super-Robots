"""对已有的 data/news/*.json 补跑翻译。

使用场景：
- 首次上线时，此前的 pipeline 是在没有 ANTHROPIC_API_KEY 时跑的，
  所有条目缺少 title_zh 且 summary_zh 是英文原文。
- 加了 API key 之后运行本脚本，一次性把所有历史条目补齐简体中文标题和摘要。

用法：
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/translate_backfill.py              # 处理所有缺 title_zh 的条目
    python scripts/translate_backfill.py --force      # 强制重新翻译（会覆盖已有 title_zh）
    python scripts/translate_backfill.py --date 2026-07-20
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.base import DATA_DIR  # noqa: E402
from enrich.summarize import enrich_items  # noqa: E402
from scripts.run_daily import build_latest  # noqa: E402

log = logging.getLogger("translate_backfill")


def needs_translation(item: dict) -> bool:
    title_zh = (item.get("title_zh") or "").strip()
    summary_zh = (item.get("summary_zh") or "").strip()
    if not title_zh:
        return True
    # summary_zh 是英文兜底填的（早期 pipeline 无 API key 时的行为）
    if not summary_zh:
        return True
    # 粗略判断：如果 summary_zh 几乎全是 ASCII，可能是英文兜底
    ascii_ratio = sum(1 for c in summary_zh if ord(c) < 128) / max(1, len(summary_zh))
    if ascii_ratio > 0.85:
        return True
    return False


def process_file(path: Path, force: bool) -> int:
    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)

    if force:
        pending = items
    else:
        pending = [it for it in items if needs_translation(it)]

    if not pending:
        log.info("%s: 全部已有中文，跳过", path.name)
        return 0

    log.info("%s: 需要翻译 %d / %d 条", path.name, len(pending), len(items))
    enriched = enrich_items(pending)

    # 用 url 作为 key 合并回原列表
    by_url = {it["url"]: it for it in enriched}
    merged = [by_url.get(it["url"], it) for it in items]

    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    log.info("%s: 已回写", path.name)
    return len(pending)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="仅处理指定日期，YYYY-MM-DD")
    p.add_argument("--force", action="store_true", help="强制重新翻译，覆盖已有 title_zh")
    args = p.parse_args()

    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("环境变量 ANTHROPIC_API_KEY 未设置，无法调用 Claude API。")
        return 1

    news_dir = DATA_DIR / "news"
    if args.date:
        files = [news_dir / f"{args.date}.json"]
    else:
        files = sorted(news_dir.glob("*.json"))

    total = 0
    for f in files:
        if not f.exists():
            log.warning("跳过不存在的文件: %s", f)
            continue
        total += process_file(f, args.force)

    log.info("=== 共翻译 %d 条 ===", total)
    log.info("=== 重建 latest.json ===")
    build_latest()

    # 同步到 web/data/
    from scripts.build_web import export_latest, export_companies
    export_companies()
    export_latest()
    log.info("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
