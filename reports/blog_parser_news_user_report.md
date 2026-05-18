# BLOG XLSX Dry-Run Report

## Input
- xlsx: `C:\Users\X230\Downloads\MyWave_Parser_News (3).xlsx`
- sheet: `raw_feed`

## Schema detection
- mode: `header_row`
- header_row_index: `0`
- header_score: `23`

## Summary
- total_rows_scanned: `63`
- valid_rows: `63`
- invalid_rows: `0`
- missing_title: `0`
- missing_slug: `0`
- missing_content: `14`
- potential_publishable: `24`

## Status distribution (top)
- `ARCHIVED`: `31`
- `PUBLISHED`: `23`
- `DRAFT`: `8`
- `READY_TO_PUBLISH`: `1`

## Conflicts
- unknown_editorial_status_count: `0`
- ingest_ok_with_non_publishable_count: `39`
- approved_status_count: `0`

## Notes
- Report is dry-run only. No writes to Sheets/DB were performed.
