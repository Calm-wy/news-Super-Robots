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
        shutil.copy(src, dst)
        print(f"Copied {src} → {dst}")
        return
    # Fallback: emit a stub so the page loads
    now = datetime.now(timezone.utc)
    stub = {
        "generated_at": now.isoformat(),
        "count": 3,
        "items": [
            {
                "id": "sample1",
                "title": "[示例] Waymo 宣布擴大鳳凰城 Robotaxi 覆蓋範圍",
                "url": "https://waymo.com/",
                "source": "Waymo Blog (sample)",
                "category": "official",
                "category_llm": "launch",
                "lang": "en",
                "published_at": (now - timedelta(hours=2)).isoformat(),
                "excerpt": "Waymo announced expanded service area...",
                "summary_zh": "Waymo 宣布將鳳凰城 Robotaxi 服務區域擴大 15%，覆蓋人口首次超過百萬。此舉是繼舊金山之後最大規模的擴張。",
                "company_ids": ["waymo"],
                "importance": 4,
                "sentiment": "positive",
                "source_weight": 5,
            },
            {
                "id": "sample2",
                "title": "[示例] 蘿蔔快跑北京訂單量單月突破 100 萬",
                "url": "https://www.apollo.auto/",
                "source": "36 氪 (sample)",
                "category": "tech_media",
                "category_llm": "launch",
                "lang": "zh",
                "published_at": (now - timedelta(hours=8)).isoformat(),
                "excerpt": "百度 Apollo 蘿蔔快跑在北京地區 6 月訂單...",
                "summary_zh": "百度 Apollo 蘿蔔快跑 6 月在北京單月訂單首次突破 100 萬單，環比增長 40%。目前已在 11 個城市開放無人化運營。",
                "company_ids": ["baidu-apollo"],
                "importance": 4,
                "sentiment": "positive",
                "source_weight": 4,
            },
            {
                "id": "sample3",
                "title": "[示例] 小馬智行完成 3 億美元 D 輪融資",
                "url": "https://pony.ai/",
                "source": "TechCrunch (sample)",
                "category": "tech_media",
                "category_llm": "funding",
                "lang": "en",
                "published_at": (now - timedelta(days=1)).isoformat(),
                "excerpt": "Pony.ai closed a $300M Series D...",
                "summary_zh": "小馬智行完成 3 億美元 D 輪融資，投後估值達 85 億美元。本輪資金主要用於車隊擴充和海外市場拓展。",
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
