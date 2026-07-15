# Release S3a — Site Admin sections fill (read-only)

**Status:** ready for PR / Owner GO  
**Base / rollback:** `c1ebacabe2b7e158f629bb6891362d8c6c6f5e94` (S2 on prod after restore)  
**Branch:** `release/s3-admin-sections-fill`

## Scope
Fill empty Site Admin stubs with usable read-only content:
- Blog list (Sheets/DB)
- Events list (`calendar_event`)
- Users list (DB, no password ops)
- Settings flags snapshot (no env write UI)
- Camp templates fixed (`admin_content`) — still gated by CAMP_* flags; public/import remain OFF

## Anti-scope
- No Camp public enable
- No Tour sync without GO
- No ParserNews admin
- No Blog editorial write workflow (still S7–S9)
- No YClients enable
