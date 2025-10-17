#!/bin/bash
set -e
BASE="http://localhost:1010"
OUT="API4_ENDPOINTS_TEST_RESULTS.md"

echo "# ✅ Результаты проверки API 4 через Traefik" > "$OUT"
echo "\nДата: $(date '+%Y-%m-%d %H:%M:%S')" >> "$OUT"

check() {
  local method="$1"; local path="$2"; local title="$3"; shift 3; local data="$@"
  echo "\n### ${title}" >> "$OUT"
  echo "\n- **${method} ${path}**" >> "$OUT"
  if [ "$method" = "GET" ]; then
    resp=$(curl -s -w "\n%{http_code}" "$BASE$path")
  else
    resp=$(curl -s -w "\n%{http_code}" -X "$method" -H 'Content-Type: application/json' -d "$data" "$BASE$path")
  fi
  code=$(echo "$resp" | tail -n1)
  body=$(echo "$resp" | head -n-1)
  echo "- **status**: $code" >> "$OUT"
  echo "\n\n\`\`\`json\n$body\n\`\`\`" >> "$OUT"
}

# Health
check GET "/api/battle/healthz" "Health: battle/healthz"
check GET "/api/analytics/health" "Health: analytics/health"
check GET "/api/healthz" "Health: root healthz"

# Battle
auth_q="?page=1&limit=3"
check GET "/api/battle/list$auth_q" "Battle: list"
check GET "/api/battle/search?limit=3" "Battle: search"
check GET "/api/battle/1" "Battle: get by id=1"

# Sync
check POST "/api/sync" "Sync: start"
check POST "/api/sync/reprocess" "Sync: reprocess"

# Analytics
check GET "/api/analytics/stats?days=7" "Analytics: stats"
check GET "/api/analytics/anomalies?days=7" "Analytics: anomalies"
check GET "/api/analytics/player/TestPlayer?days=7" "Analytics: player"
check GET "/api/analytics/players/top?metric=battles_count&limit=5" "Analytics: top players"
check GET "/api/analytics/clan/TestClan?days=7" "Analytics: clan"
check GET "/api/analytics/resource/Gold?days=7" "Analytics: resource"
check GET "/api/analytics/monster/Goblin?days=7" "Analytics: monster"

# Admin (ожидаем 503 без токена)
check GET "/api/admin/loading-stats" "Admin: loading-stats (no token)"
check POST "/api/admin/cleanup?days_old=30" "Admin: cleanup (no token)"

echo "\n\n---\n\nГотово." >> "$OUT"

echo "Saved -> $OUT"
