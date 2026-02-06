#!/usr/bin/env python3
"""
Fix booking.js by removing blocking checks that prevent script initialization.
"""

import re

filepath = r"e:\Проекты MyWave\Site_MyWave\static\js\booking.js"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

print("📝 Original content (lines 45-65)...")

# Find and replace the blocking code
# OLD:
#   if (!UI.bookingDateInput || !UI.slotButtonsContainer) {
#     console.warn("⚠️ booking.js не может инициализироваться — отсутствуют ключевые элементы.");
#     return;
#   }

# NEW: (just warn, don't return)

old_pattern = r"""  if \(!UI\.bookingDateInput \|\| !UI\.slotButtonsContainer\) \{
    console\.warn\("⚠️ booking\.js не может инициализироваться — отсутствуют ключевые элементы\."\);
    return;
  \}"""

new_code = """  if (!UI.bookingDateInput || !UI.slotButtonsContainer) {
    console.warn("⚠️ Предупреждение: отсутствуют некоторые модальные элементы (это нормально, если они подгружаются позже).");
    // NOTE: We do NOT return here anymore - this allows booking buttons to work even if modals aren't ready yet
  }"""

if re.search(old_pattern, content):
    content = re.sub(old_pattern, new_code, content)
    print("✅ Replaced blocking check (bookingDateInput)")
else:
    print("⚠️  Pattern not found, trying manual fix...")

# Also fix the second blocking check
old_pattern2 = r"""  // Проверяем инициализацию кнопок бронирования
  if \(!UI\.openBookingButtons \|\| UI\.openBookingButtons\.length === 0\) \{
    console\.warn\("⚠️ Не найдены кнопки для бронирования"\);
    return;
  \}"""

new_code2 = """  // Проверяем инициализацию кнопок бронирования
  if (!UI.openBookingButtons || UI.openBookingButtons.length === 0) {
    console.warn("⚠️ Не найдены кнопки для бронирования - попытаемся продолжить");
    // NOTE: We do NOT return here - let booking initialization continue
  }"""

if re.search(old_pattern2, content):
    content = re.sub(old_pattern2, new_code2, content)
    print("✅ Replaced blocking check (openBookingButtons)")
else:
    print("⚠️  Second pattern not found")

# Write back
with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\n✅ Fixed {filepath}")
print(
    "📌 The booking.js will now continue initialization even if some modal elements are missing"
)
print("   This allows button click handlers to register properly")
