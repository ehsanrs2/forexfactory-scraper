#!/bin/bash

cd "$(dirname "$0")"
source venv/bin/activate

[ -f .env ] && source .env
[ -f .env.local ] && source .env.local

# Scrape from 2 days ago to tomorrow to capture actuals for today and yesterday
if date -v-2d +%Y-%m-%d &>/dev/null 2>&1; then
  # macOS
  START=$(date -v-2d +%Y-%m-%d)
  END=$(date -v+1d +%Y-%m-%d)
else
  # Linux/Ubuntu
  START=$(date -d '-2 days' +%Y-%m-%d)
  END=$(date -d '+1 day' +%Y-%m-%d)
fi

echo "[$(date '+%Y-%m-%d %H:%M')] Updating actuals: $START → $END"

python3 -m src.forexfactory.main \
  --start "$START" \
  --end "$END" \
  --csv econ_2026.csv \
  --details

# Re-generate JSON from updated CSV
python3 to_json.py econ_2026.csv econ_2026.json

# Upload JSON to tmd-auth server
curl -s -X POST "${ECON_UPLOAD_URL}/calendar/econ/upload" \
  -H "Content-Type: application/json" \
  -H "x-upload-secret: ${ECON_UPLOAD_SECRET}" \
  --data-binary @econ_2026.json \
  && { echo "[$(date '+%Y-%m-%d %H:%M')] Upload success."; rm -f econ_2026.json econ_2026.csv; } \
  || echo "[$(date '+%Y-%m-%d %H:%M')] Upload FAILED."

echo "[$(date '+%Y-%m-%d %H:%M')] Done."
