#!/usr/bin/env python3
"""
blog raw_feed smoke check

Read-only диагностика источника блога (ParserNews/raw_feed) без запуска витрины.

Счётчик publishable согласован с docs/BLOG_CONTRACT_v1.md (is_publishable_row).

Выводит:
- worksheet name
- detected header row index
- total scanned rows
- usable rows after header
- publishable rows count
- status distribution
- vitrine_quality: разбивка DRAFT/APPROVED/READY_TO_PUBLISH/PUBLISHED и др.,
  контент без publishable v1, застрявшие APPROVED/DRAFT с контентом
- sample normalized entries (title, slug, published_at)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only smoke check для blog raw_feed"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_stdout",
        help="Печатать итог только в JSON в stdout",
    )
    parser.add_argument(
        "--out-json",
        dest="out_json",
        default="",
        help="Сохранить machine-readable JSON-отчёт в файл",
    )
    parser.add_argument(
        "--min-publishable",
        type=int,
        default=None,
        help="Минимально допустимое число publishable записей",
    )
    parser.add_argument(
        "--max-empty-status-share",
        type=float,
        default=None,
        help="Максимально допустимая доля строк с пустым status, от 0 до 1",
    )
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()

    if args.json_stdout:
        import logging
        import warnings
        logging.disable(logging.CRITICAL)
        warnings.filterwarnings("ignore", category=UserWarning)

    # Для локального запуска create_app требует multiproc-dir prometheus.
    prom_dir = REPO_ROOT / "prometheus_multiproc"
    prom_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", str(prom_dir))

    from app import create_app
    from app.services.google import get_google_services
    from app.services.parser_news_sheet import resolve_parser_source
    from app.services.blog.store import (
        _detect_parser_header_row_with_trace,
        _normalize_row_from_sheets,
    )
    from app.services.blog.publishability import analyze_raw_feed_vitrine_quality, is_publishable_row

    app = create_app("development")
    with app.app_context():
        spreadsheet_id, worksheet_title = resolve_parser_source()
        svc = get_google_services()[1]

        result = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{worksheet_title}!A1:ZZ1000",
        ).execute()
        all_rows = result.get("values", [])

        if worksheet_title == "raw_feed":
            header_idx, header_trace = _detect_parser_header_row_with_trace(all_rows)
            if header_idx is None:
                header_idx = 0
        else:
            header_idx = 0
            header_trace = {"reason": "not raw_feed", "matched_columns": []}

        headers = [str(x).strip() for x in all_rows[header_idx]] if all_rows else []
        data_rows = all_rows[header_idx + 1 :] if all_rows else []

        records = []
        for row in data_rows:
            if not any(str(cell).strip() for cell in row if cell is not None):
                continue
            padded = list(row) + [""] * max(0, len(headers) - len(row))
            records.append(dict(zip(headers, padded[: len(headers)])))

        status_counter = Counter(str(r.get("status") or "").strip() or "(empty)" for r in records)
        publishable_rows = [r for r in records if is_publishable_row(r)]
        total_records = len(records)
        empty_status_count = status_counter.get("(empty)", 0)
        empty_status_share = (empty_status_count / total_records) if total_records else 0.0

        normalized = []
        for r in records:
            post = _normalize_row_from_sheets(r)
            if post:
                normalized.append(post)

        sample_entries = []
        for post in normalized[:5]:
            sample_entries.append(
                {
                    "title": post.get("title"),
                    "slug": post.get("slug"),
                    "published_at": str(post.get("published_at")),
                }
            )

        vitrine_quality = analyze_raw_feed_vitrine_quality(records)

        report = {
            "worksheet_name": worksheet_title,
            "detected_header_row_index": header_idx,
            "header_detection": header_trace,
            "total_scanned_rows": len(all_rows),
            "usable_rows_after_header": len(records),
            "normalized_rows_count": len(normalized),
            "publishable_rows_count": len(publishable_rows),
            "empty_status_count": empty_status_count,
            "empty_status_share": round(empty_status_share, 6),
            "status_distribution": dict(status_counter),
            "vitrine_quality": vitrine_quality,
            "sample_entries": sample_entries,
        }

        if args.out_json:
            out_path = Path(args.out_json)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        if args.json_stdout:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print("=== blog raw_feed smoke check ===")
            print(f"worksheet name: {report['worksheet_name']}")
            print(f"detected header row index: {report['detected_header_row_index']}")
            if report.get("header_detection"):
                det = report["header_detection"]
                print(f"header matched columns: {det.get('matched_columns')}")
                print(f"header matched indices: {det.get('matched_indices')}")
                print(f"header detection reason: {det.get('reason')}")
            print(f"total scanned rows: {report['total_scanned_rows']}")
            print(f"usable rows after header: {report['usable_rows_after_header']}")
            print(f"normalized rows count: {report['normalized_rows_count']}")
            print(f"publishable rows count: {report['publishable_rows_count']}")
            print(f"empty status count: {report['empty_status_count']}")
            print(f"empty status share: {report['empty_status_share']}")
            print("status distribution:")
            for status, cnt in status_counter.most_common(12):
                print(f"  - {status}: {cnt}")

            vq = report.get("vitrine_quality") or {}
            print("vitrine quality (contract v1):")
            sb = vq.get("status_buckets") or {}
            for k in ("DRAFT", "APPROVED", "READY_TO_PUBLISH", "PUBLISHED", "ARCHIVED", "REVIEW", "(empty)", "OTHER"):
                if k in sb:
                    print(f"  - {k}: {sb[k]}")
            print(f"  - rows_with_meaningful_content: {vq.get('rows_with_meaningful_content')}")
            print(f"  - publishable_v1: {vq.get('publishable_v1')}")
            print(f"  - has_content_not_publishable_v1: {vq.get('has_content_not_publishable_v1')}")
            print(f"  - has_content_status_draft_or_approved: {vq.get('has_content_status_draft_or_approved')}")

            print("sample normalized entries:")
            for item in report["sample_entries"]:
                print(
                    f"  - title={item.get('title')!r}, "
                    f"slug={item.get('slug')!r}, "
                    f"published_at={item.get('published_at')!r}"
                )

        exit_code = 0

        if args.min_publishable is not None and len(publishable_rows) < args.min_publishable:
            exit_code = 2 if exit_code == 0 else exit_code

        if (
            args.max_empty_status_share is not None
            and empty_status_share > args.max_empty_status_share
        ):
            exit_code = 3 if exit_code == 0 else exit_code

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
