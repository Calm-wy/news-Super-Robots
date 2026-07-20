"""Prepare web/data/ for the static site.

- companies.yaml → web/data/companies.json
- data/latest.json → web/data/latest.json  (fallback: sample data)
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from collectors.base import DATA_DIR, load_yaml  # noqa: E402

WEB_DATA = ROOT / "web" / "data"


def export_companies() -> None:
    cfg = load_yaml("companies.yaml")
    out = [
        {
            "id": c["id"],
            "name_zh": c["name_zh"],
            "name_en": c["name_en"],
            "region": c["region"],
            "weight": c["weight"],
        }
        for c in cfg["companies"]
    ]
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    with open(WEB_DATA / "companies.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {WEB_DATA / 'companies.json'} ({len(out)} companies)")


def export_latest() -> None:
    src = DATA_DIR / "latest.json"
    dst = WEB_DATA / "latest.json"
    if src.exists():
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("count", 0) > 0:
            shutil.copy(src, dst)
            print(f"Copied {src} → {dst} ({data['count']} items)")
            return
        print(f"{src} exists but is empty — falling back to sample data")
    # Fallback: emit a stub so the page loads
    now = datetime.now(timezone.utc)
    stub = {
        "generated_at": now.isoformat(),
        "count": 3,
        "items": [
            {
                "id": "sample1",
                "title": "[示例] Waymo 宣布扩大凤凰城 Robotaxi 覆盖范围",
                "url": "https://waymo.com/",
                "source": "Waymo Blog (sample)",
                "category": "official",
                "category_llm": "launch",
                "lang": "en",
                "published_at": (now - timedelta(hours=2)).isoformat(),
                "excerpt": "Waymo announced expanded service area...",
                "summary_zh": "Waymo 宣布将凤凰城 Robotaxi 服务区域扩大 15%，覆盖人口首次超过百万。此举是继旧金山之后最大规模的扩张。",
                "company_ids": ["waymo"],
                "importance": 4,
                "sentiment": "positive",
                "source_weight": 5,
            },
            {
                "id": "sample2",
                "title": "[示例] 萝卜快跑北京订单量单月突破 100 万",
                "url": "https://www.apollo.auto/",
                "source": "36 氪 (sample)",
                "category": "tech_media",
                "category_llm": "launch",
                "lang": "zh",
                "published_at": (now - timedelta(hours=8)).isoformat(),
                "excerpt": "百度 Apollo 萝卜快跑在北京地区 6 月订单...",
                "summary_zh": "百度 Apollo 萝卜快跑 6 月在北京单月订单首次突破 100 万单，环比增长 40%。目前已在 11 个城市开放无人化运营。",
                "company_ids": ["baidu-apollo"],
                "importance": 4,
                "sentiment": "positive",
                "source_weight": 4,
            },
            {
                "id": "sample3",
                "title": "[示例] 小马智行完成 3 亿美元 D 轮融资",
                "url": "https://pony.ai/",
                "source": "TechCrunch (sample)",
                "category": "tech_media",
                "category_llm": "funding",
                "lang": "en",
                "published_at": (now - timedelta(days=1)).isoformat(),
                "excerpt": "Pony.ai closed a $300M Series D...",
                "summary_zh": "小马智行完成 3 亿美元 D 轮融资，投后估值达 85 亿美元。本轮资金主要用于车队扩充和海外市场拓展。",
                "company_ids": ["pony-ai"],
                "importance": 5,
                "sentiment": "positive",
                "source_weight": 4,
            },
        ],
    }
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(stub, f, ensure_ascii=False, indent=2)
    print(f"Wrote sample data → {dst}")


def main() -> int:
    export_companies()
    export_latest()
    return 0


if __name__ == "__main__":
    sys.exit(main())
