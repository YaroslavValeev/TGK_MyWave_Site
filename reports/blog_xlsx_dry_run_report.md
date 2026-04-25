# BLOG XLSX Dry-Run Report

## Input
- xlsx: `C:\Users\X230\Downloads\MyWave_Parser_News.xlsx`
- sheet: `raw_feed`

## Schema detection
- mode: `header_row`
- header_row_index: `0`
- header_score: `21`

## Summary
- total_rows_scanned: `2729`
- valid_rows: `146`
- invalid_rows: `2583`
- missing_title: `2583`
- missing_slug: `0`
- missing_content: `2533`
- potential_publishable: `2`

## Status distribution (top)
- `(empty)`: `2581`
- `DRAFT`: `146`
- `READY_TO_PUBLISH`: `2`

## Conflicts
- unknown_editorial_status_count: `0`
- ingest_ok_with_non_publishable_count: `0`
- approved_status_count: `0`

## Notes
- Report is dry-run only. No writes to Sheets/DB were performed.
