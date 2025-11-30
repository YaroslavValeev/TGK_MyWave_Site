#!/bin/bash
# Quick fix: Comment out the blocking checks in booking.js

sed -i.bak '50,59s/^  if (!UI.bookingDateInput/  \/\/ DISABLED: if (!UI.bookingDateInput/' e:\\Проекты\ MyWave\\Site_MyWave\\static\\js\\booking.js
sed -i '51,59s/^    console.warn/    \/\/ console.warn/' e:\\Проекты\ MyWave\\Site_MyWave\\static\\js\\booking.js
sed -i '52,59s/^    return/    \/\/ return/' e:\\Проекты\ MyWave\\Site_MyWave\\static\\js\\booking.js

echo "✅ Patched booking.js"
