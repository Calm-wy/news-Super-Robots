# L4 Robotaxi 每日新聞看板

追蹤全球 16 家主要 L4 Robotaxi 玩家的每日動態：官方公告、科技媒體、社交媒體、資本市場、招聘信號。

- **前端**：靜態單頁 (Tailwind + Alpine.js CDN，無 build step)
- **抓取**：Python (feedparser + requests + BeautifulSoup)
- **摘要**：Anthropic Claude Haiku 4.5 / Sonnet 4.6（重要新聞升級）
- **排程**：GitHub Actions，每日北京 08:17 更新
- **部署**：GitHub Pages（免費）

---

## 快速開始

### 1. 本地驗證

```bash
cd robotaxi-dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 抓取當日 RSS（不摘要，快速驗證通路）
python scripts/run_daily.py --collect-only

# 生成前端資料（若無 latest.json 則使用範例資料）
python scripts/build_web.py

# 本地預覽
cd web && python3 -m http.server 4321
# 打開 http://localhost:4321
```

### 2. 首次部署到 GitHub Pages

```bash
# 1) 建 GitHub repo（例如 robotaxi-dashboard）
git init && git add -A
git commit -m "init: robotaxi dashboard"
git remote add origin git@github.com:<YOUR>/<REPO>.git
git push -u origin main   # 或 develop

# 2) 到 GitHub 網頁：
#    Settings → Secrets and variables → Actions → New repository secret
#      名稱: ANTHROPIC_API_KEY
#      值:   sk-ant-...
#
#    Settings → Pages
#      Source: GitHub Actions
#
#    Actions → Daily News Update → Run workflow   (手動觸發一次驗證)
```

執行完成後，Actions 頁面會顯示 Pages URL，形如：
`https://<username>.github.io/<repo>/`

---

## 目錄結構

```
robotaxi-dashboard/
├── config/
│   ├── companies.yaml     # 16 家追蹤廠商 (id / 別名 / 官方連結 / 權重)
│   ├── feeds.yaml         # RSS 來源
│   ├── newsrooms.yaml     # HTML 抓取的官方 newsroom (CSS selectors)
│   └── keywords.yaml      # 主關鍵詞 + 事件加成詞
├── collectors/
│   ├── base.py            # NewsItem + 共用工具 (去重/日期/關鍵詞)
│   ├── rss.py             # RSS/Atom 抓取
│   ├── official.py        # 通用 HTML 抓取器 (config-driven)
│   ├── social.py          # (stub) 建議走 Nitter / RSSHub 加到 feeds.yaml
│   └── capital.py         # (stub) 資本市場由 RSS + Claude 分類負責
├── enrich/
│   └── summarize.py       # Claude 摘要 + 分類 + 重要度打分
├── scripts/
│   ├── run_daily.py       # 完整 pipeline: collect → enrich → dump
│   └── build_web.py       # 匯出 web/data/{companies,latest}.json
├── data/
│   ├── raw/               # 原始抓取 (每天一檔，gitignore)
│   ├── news/              # 摘要處理後 (每天一檔，入 git)
│   └── latest.json        # 近 30 天合併，前端讀取
├── web/                   # 靜態站，部署到 GitHub Pages
│   ├── index.html
│   └── data/
├── .github/workflows/
│   └── daily-update.yml   # 排程 + 部署
└── requirements.txt
```

---

## 常見操作

### 新增追蹤廠商

編輯 `config/companies.yaml`，加一筆：

```yaml
- id: newco
  name_zh: 某某公司
  name_en: NewCo
  region: CN
  weight: 3
  aliases: [某某公司, NewCo, "某某"]
  homepage: https://newco.example.com/
```

如果對方有 RSS，加到 `feeds.yaml`（`company: newco`）；否則加到 `newsrooms.yaml` 並填入 CSS selector。

### 新增資料來源

**有 RSS**：加到 `config/feeds.yaml`。

**沒 RSS，但有網頁**：加到 `config/newsrooms.yaml`：
```yaml
- company: waymo
  name: XX Site
  url: https://xx.com/news
  lang: en
  weight: 4
  item_selector: article        # 每張新聞卡的外框
  link_selector: a              # 內部的連結
  title_selector: h2            # 內部的標題
  date_selector: time
```

**Twitter/微博**：透過 Nitter / RSSHub 公共實例接 RSS。範例：
```yaml
- name: Waymo Twitter
  url: https://nitter.net/waymo/rss
  category: social
  lang: en
  company: waymo
  weight: 3
```

### 調整摘要模型

`enrich/summarize.py` 中：
- `HAIKU`：預設模型
- `SONNET`：偵測到融資/事故/裁員關鍵詞時升級
- `_pick_model()`：修改升級條件

### 成本控制

- 用了 **prompt caching**（system prompt 快取 1h）+ 每次一封 API call
- 每日 100–200 篇時，Haiku ≈ 每月 < 5 USD
- 若想更省，可改用 Batch API（`enrich/summarize.py` 保留為未來優化）

### 資料保留

- `data/raw/*.json`：抓取原檔，`.gitignore` 排除，只留當地端
- `data/news/*.json`：摘要後，入 git；`build_latest()` 合併近 30 天
- 想長期歸檔：把超過 90 天的檔案 `mv data/news/2025-*.json data/archive/2025/`

---

## 故障排查

**Actions 跑失敗，`ANTHROPIC_API_KEY` 沒設**：
Pipeline 會照跑但不做摘要，`summary_zh` 用 `excerpt` 前 200 字代替。

**某個 feed 一直失敗**：
去 `feeds.yaml` 刪掉或換 URL，pipeline 對單一 feed 失敗有容忍。

**HTML 官方站抓不到內容**：
用瀏覽器 DevTools 找對的 selector，改 `config/newsrooms.yaml`。不需要改任何 Python。

**前端 `latest.json` 是空的**：
先在 GitHub 上手動觸發一次 workflow (`workflow_dispatch`)；如果本地想試，跑 `python scripts/build_web.py` 會生範例資料。

---

## Roadmap

- [ ] 微信公眾號整合（透過自架 RSSHub）
- [ ] 融資事件時間軸視圖
- [ ] Weekly digest email (每週日發送 Markdown 摘要)
- [ ] 廠商對比雷達圖（部署城市、車隊規模、里程）
