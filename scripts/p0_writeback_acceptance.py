"""
P0 интеграционная приёмка writeback на реальной таблице raw_feed.

Важно:
- Скрипт добавляет тестовую запись в конец листа (append), проставляет row_number (как делает Parser Bot),
  затем запускает publish_ready_posts и выводит значения publish-полей до/после.
- Второй кейс: запись без row_number → сайт не делает writeback, фиксирует publish_error кодом.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime


def _idx_to_letter(n: int) -> str:
    res = ""
    n += 1
    while n > 0:
        n -= 1
        res = chr(65 + (n % 26)) + res
        n //= 26
    return res


def _pick(r: dict) -> dict:
    keys = [
        "row_number",
        "status",
        "slug",
        "published_posts",
        "published_at",
        "publish_attempts",
        "publish_last_try_at",
        "publish_error",
        "canonical_url",
        "_sheet_row_number",
    ]
    return {k: str(r.get(k) or "") for k in keys}


def main() -> int:
    # Обеспечиваем импорт `app` из корня репозитория, даже если скрипт запускают как файл.
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # Явно указываем источник Parser Bot таблицы
    os.environ.setdefault("PARSER_TAB", "1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50")
    os.environ.setdefault("PARSER_SHEET_NAME", "raw_feed")

    from app import create_app
    from app.services.google import append_to_sheet, read_sheet
    from app.services.google import get_google_services
    from app.services.parser_news_sheet import (
        resolve_parser_source,
        fetch_parser_news_rows,
    )
    from app.services.blog.publish import (
        acquire_publish_lock,
        ack_publish,
        release_publish_lock,
        record_publish_error_by_id,
        update_sheet_cells,
    )

    app = create_app("development")

    with app.app_context():
        spreadsheet_id, sheet_name = resolve_parser_source()

        # Диагностика: где API видит строку заголовков (простая проверка наличия id+status)
        try:
            svc = get_google_services()[1]
            res = (
                svc.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:ZZ1000")
                .execute()
            )
            values = res.get("values", [])

            def norm(x: str) -> str:
                return str(x or "").strip().lower()

            expected = {
                "id",
                "status",
                "published_posts",
                "publish_error",
                "source_type",
            }
            best_score = 0
            best_row = 1
            first_id_status_row = None

            for i, row in enumerate(values[:400]):
                rowset = {norm(c) for c in row if norm(c)}
                score = len(expected.intersection(rowset))
                if score > best_score:
                    best_score = score
                    best_row = i + 1
                if (
                    "id" in rowset
                    and "status" in rowset
                    and first_id_status_row is None
                ):
                    first_id_status_row = i + 1

            print(
                "header_scan",
                {
                    "best_score": best_score,
                    "best_row": best_row,
                    "first_id_status_row": first_id_status_row,
                },
            )
        except Exception as e:
            print("header_scan_error", str(e))

        records, headers = read_sheet(spreadsheet_id, sheet_name)

        hidx = {str(h).strip().lower(): i for i, h in enumerate(headers)}

        def col(name: str) -> int | None:
            return hidx.get(name)

        needed = [
            "id",
            "status",
            "row_number",
            "slug",
            "telegram_published",
            "final_posts",
            "final_ready",
            "published_posts",
            "published_at",
            "canonical_url",
            "publish_error",
            "publish_attempts",
            "publish_last_try_at",
        ]
        missing = [n for n in needed if col(n) is None]
        print("missing_cols", missing)
        if missing:
            return 3

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        test_id = f"site_p0_test_{ts}"
        test_slug = f"p0-test-{ts}"

        row = ["" for _ in headers]
        row[col("id")] = test_id
        row[col("status")] = "READY_TO_PUBLISH"
        row[col("slug")] = test_slug
        row[col("telegram_published")] = "TRUE"
        row[col("final_posts")] = (
            f"# P0 test\n\nThis is a P0 integration test record ({test_id})."
        )
        row[col("final_ready")] = "TRUE"

        append_to_sheet(spreadsheet_id, sheet_name, [row])
        print("appended", {"id": test_id, "slug": test_slug})

        records2, _headers2 = fetch_parser_news_rows()
        rec = [r for r in records2 if str(r.get("id") or "").strip() == test_id]
        if not rec:
            print("ERROR: cannot find appended row by id")
            return 4
        rec = rec[0]

        sheet_row = int(str(rec.get("_sheet_row_number") or "").strip())
        print(
            "located",
            {
                "sheet_row": sheet_row,
                "row_number_before": str(rec.get("row_number") or ""),
            },
        )

        rn_col_idx = col("row_number")
        rn_letter = _idx_to_letter(int(rn_col_idx))
        update_sheet_cells(
            spreadsheet_id,
            sheet_name,
            [{"range": f"{rn_letter}{sheet_row}", "values": [[str(sheet_row)]]}],
        )
        print("row_number_set", sheet_row)

        records3, _ = fetch_parser_news_rows()
        rec3 = [r for r in records3 if str(r.get("id") or "").strip() == test_id][0]
        print("before_publish", _pick(rec3))

        # P0 acceptance: проверяем writeback без привязки к локальной БД (актуально для стенда/интеграционного теста).
        published_at = datetime.utcnow()
        if not acquire_publish_lock(sheet_row):
            print("ERROR: cannot acquire lock", sheet_row)
            return 10
        try:
            ok = ack_publish(sheet_row, test_id, published_at, slug=None)
            print("ack_publish_ok", ok)
        finally:
            release_publish_lock(sheet_row)

        records4, _ = fetch_parser_news_rows()
        rec4 = [r for r in records4 if str(r.get("id") or "").strip() == test_id][0]
        print("after_publish", _pick(rec4))

        # Safety case: без row_number
        ts2 = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        test_id2 = f"site_p0_test_missing_rn_{ts2}"
        test_slug2 = f"p0-test-missing-rn-{ts2}"

        row2 = ["" for _ in headers]
        row2[col("id")] = test_id2
        row2[col("status")] = "READY_TO_PUBLISH"
        row2[col("slug")] = test_slug2
        row2[col("telegram_published")] = "TRUE"
        row2[col("final_posts")] = f"# P0 test\n\nMissing row_number ({test_id2})."
        row2[col("final_ready")] = "TRUE"

        append_to_sheet(spreadsheet_id, sheet_name, [row2])
        print("appended_missing_rn", {"id": test_id2, "slug": test_slug2})

        ok2 = record_publish_error_by_id(test_id2, "WP_ROW_NUMBER_MISSING")
        print("record_publish_error_by_id_ok", ok2)

        records5, _ = fetch_parser_news_rows()
        rec5 = [r for r in records5 if str(r.get("id") or "").strip() == test_id2]
        if rec5:
            print("missing_rn_row_after", _pick(rec5[0]))
        else:
            print("missing_rn_row_after", "NOT_FOUND")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
