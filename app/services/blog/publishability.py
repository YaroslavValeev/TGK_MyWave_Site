"""
Единая логика «показывать на витрине / считать строку publishable» для raw_feed (контракт v1, сайт).

Полный канон: docs/BLOG_CONTRACT_v1.md

Контракт v1 (Parser_News ↔ сайт):
- publishable ⇔ status ∈ {READY_TO_PUBLISH, PUBLISHED} (без учёта регистра)
  и не ARCHIVED
  и есть контент (has_content)
- published_posts НЕ используется как признак показа на витрине
- final_ready не используется
- telegram_published не используется (отдельное продуктовое решение)

Решение по APPROVED: не маппим на READY_TO_PUBLISH. Записи со статусом APPROVED
на витрине не показываются; в таблице нужно выставить READY_TO_PUBLISH или PUBLISHED.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Статусы, при которых материал может отображаться на сайте (нормализуются через .upper())
PUBLISHABLE_STATUSES_V1 = frozenset({"READY_TO_PUBLISH", "PUBLISHED"})


def _status_upper(status_raw: Optional[str]) -> str:
    return str(status_raw or "").strip().upper()


def has_publishable_content(row: Dict[str, Any]) -> bool:
    """
    Есть ли смысловой контент для показа поста.
    raw_feed: final_posts / text / raw_content / raw_html
    news_articles-подобная строка: при наличии title и поля text — требуется непустой text.
    """
    fp = str(row.get("final_posts") or "").strip()
    text = str(row.get("text") or "").strip()
    rc = str(row.get("raw_content") or "").strip()
    rh = str(row.get("raw_html") or "").strip()

    title = str(row.get("title") or "").strip()
    if title and "text" in row:
        return bool(text)

    return bool(fp or text or rc or rh)


def is_publishable_row(row: Dict[str, Any]) -> bool:
    """
    Строка из Sheets (dict по заголовкам) считается publishable для витрины по контракту v1.
    """
    st = _status_upper(row.get("status"))
    if st == "ARCHIVED":
        return False
    if st not in PUBLISHABLE_STATUSES_V1:
        return False
    return has_publishable_content(row)


def analyze_raw_feed_vitrine_quality(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Read-only сводка по листу raw_feed: статусы, контент vs publishable v1.

    Используется в scripts/blog_raw_feed_smoke_check.py для отчётов GM/Parser.
    """
    key_order = ("DRAFT", "APPROVED", "READY_TO_PUBLISH", "PUBLISHED", "ARCHIVED", "REVIEW")
    counts: Dict[str, int] = {k: 0 for k in key_order}
    counts["(empty)"] = 0
    counts["OTHER"] = 0

    for r in records:
        raw = str(r.get("status") or "").strip()
        if not raw:
            counts["(empty)"] += 1
        else:
            su = raw.upper()
            if su in key_order:
                counts[su] += 1
            else:
                counts["OTHER"] += 1

    hc = sum(1 for r in records if has_publishable_content(r))
    pub = sum(1 for r in records if is_publishable_row(r))
    not_ready = sum(
        1 for r in records if has_publishable_content(r) and not is_publishable_row(r)
    )
    stuck_draft_approved = sum(
        1
        for r in records
        if has_publishable_content(r)
        and str(r.get("status") or "").strip().upper() in ("APPROVED", "DRAFT")
    )

    return {
        "status_buckets": {k: counts[k] for k in key_order + ("(empty)", "OTHER")},
        "rows_total": len(records),
        "rows_with_meaningful_content": hc,
        "publishable_v1": pub,
        "has_content_not_publishable_v1": not_ready,
        "has_content_status_draft_or_approved": stuck_draft_approved,
    }


def is_publishable_blog_post_record(post: Any) -> bool:
    """
    Резерв витрины из БД (BlogPost): тот же статус v1 + наличие content_md или HTML.
    """
    st = _status_upper(getattr(post, "status", None))
    if st == "ARCHIVED":
        return False
    if st not in PUBLISHABLE_STATUSES_V1:
        return False
    md = str(getattr(post, "content_md", None) or "").strip()
    html = str(
        getattr(post, "content_html", None) or getattr(post, "content", None) or ""
    ).strip()
    return bool(md or html)


# Имена статусов для SQL .in_(...) — плюс легаси lowercase «published»
DB_PUBLISHABLE_STATUS_VALUES = ("READY_TO_PUBLISH", "PUBLISHED", "published")
