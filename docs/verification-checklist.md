# Verification Checklist (MyWave: Site + Parser)

This is the minimum manual smoke checklist before merging.

## 1) Site MyWave — Home
- Open the home page
- Expected: no server error, no console error, all critical UI loads

## 2) Booking — Slot Availability → Confirmation
Steps:
1) Click "Book" / "Записаться"
2) Select a date
3) Wait for slots to load
4) Select a slot
5) Enter contact details
6) Confirm booking

Expected:
- Slots list matches capacity rules
- Busy slots are hidden/disabled
- Confirmation message appears
- No duplicate booking when repeating the same confirm action quickly

## 3) Calendar Sync — No Duplicates
Steps:
1) Perform the same booking twice (simulate retry)
2) Check calendar entry

Expected:
- Exactly one calendar event exists for the booking
- If repeated, the event is updated, not duplicated

## 4) Chat / Sockets — Stability
Steps:
1) Open chat widget
2) Send a message
3) Refresh the page
4) Send again

Expected:
- No crash
- No duplicate event handlers
- No reconnect spam
- No CSP violations (if CSP is strict)

## 5) Parser Bot — Dedup & Idempotent Publish
Steps:
1) Run parser pipeline for a known input set
2) Run it again immediately (retry)

Expected:
- No duplicate items stored
- No duplicate items published
- published_at remains ISO 8601
    