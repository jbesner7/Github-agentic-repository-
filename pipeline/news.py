from __future__ import annotations

from typing import Any

from pipeline.io_util import utc_now_iso


def build_news_signal(
    symbol: str,
    articles: list[dict[str, Any]],
    earnings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Agent C: factual packaging of RH news/earnings payloads only."""
    headlines = []
    for a in articles[:10]:
        headlines.append(
            {
                "title": a.get("title") or a.get("headline"),
                "published_at": a.get("published_at") or a.get("updated_at") or a.get("created_at"),
                "source": a.get("source") or a.get("author"),
                "url": a.get("url") or a.get("link"),
            }
        )
    return {
        "symbol": symbol,
        "as_of": utc_now_iso(),
        "headline_count": len(headlines),
        "headlines": headlines,
        "earnings": earnings,
        "notes": "Read-only catalyst pack; no sentiment scores invented.",
    }
