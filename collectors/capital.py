"""Capital-market signals: funding / IPO / layoffs / hiring.

Most of the raw material comes from RSS (Crunchbase News is already in
feeds.yaml), and enrichment auto-classifies items into 'funding' /
'layoff' / 'hiring' categories via Claude.

This module is reserved for signals that need custom logic:
  - LinkedIn open-role count trend (proxy for hiring/layoff pace),
  - 企查查 / 天眼查 registration changes,
  - SEC EDGAR filings for US-listed autonomy plays.

For now, it's a stub — the RSS pipeline handles funding news adequately.
"""
from __future__ import annotations

import logging

from .base import NewsItem

log = logging.getLogger(__name__)


def collect_capital() -> list[NewsItem]:
    log.info("collect_capital: stub (funding news already flows through RSS + Claude classification)")
    return []
