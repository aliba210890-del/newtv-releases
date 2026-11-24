#!/bin/bash
# Безопасное обновление графа дорог: собрать/скачать в свободный каталог, проверить, только потом переключить.
set -euo pipefail
cd /opt/osrm
IMG=ghcr.io/project-osrm/osrm-backend:v5.27.1
CUR=$(readlink current 2>/dev/null || echo b); NEW=$([ "$CUR" = a ] && echo b || echo a)
rm -rf "$NEW" && mkdir -p "$NEW"
# граф собирает GitHub Actions (jolda-osrm-graph.yml) и выкладывает в релиз jolda-osrm-graph
curl -fsSL -o "$NEW/kz.tar.zst" "https://github.com/aliba210890-del/newtv-releases/releases/download/jolda-osrm-graph/kz-osrm.tar.zst"
tar -I zstd -xf "$NEW/kz.tar.zst" -C "$NEW" && rm "$NEW/kz.tar.zst"
docker rm -f osrm-check >/dev/null 2>&1 || true
docker run -d --name osrm-check -p 127.0.0.1:5001:5000 -v "/opt/osrm/$NEW:/data:ro" $IMG osrm-routed --algorithm mld /data/kz.osrm >/dev/null
for i in $(seq 1 60); do curl -sf "http://127.0.0.1:5001/route/v1/driving/71.43,51.13;71.76,51.07" | grep -q '"Ok"' && break; sleep 2; done
fail=0
while read -r q; do
  a=$(curl -sf "http://127.0.0.1:5001/route/v1/driving/$q?overview=false" | jq -r '.routes[0].distance // empty')
  b=$(curl -sf "http://127.0.0.1:5000/route/v1/driving/$q?overview=false" | jq -r '.routes[0].distance // empty' || true)
  [ -z "$a" ] && { echo "нет маршрута: $q"; fail=$((fail+1)); continue; }
  [ -n "$b" ] && python3 -c "import sys;a,b=float('$a'),float('$b');sys.exit(0 if abs(a-b)/max(b,1)<0.05 else 1)" || { [ -n "$b" ] && { echo "расхождение >5%: $q $a/$b"; fail=$((fail+1)); }; }
done < /opt/osrm/check_routes.txt
docker rm -f osrm-check >/dev/null
if [ "$fail" -gt 2 ]; then echo "$(date) ПРОВЕРКА НЕ ПРОЙДЕНА ($fail), остаётся старый граф"; exit 1; fi
ln -sfn "$NEW" current.tmp && mv -T current.tmp current
docker compose -f /opt/osrm/docker-compose.yml up -d && docker compose -f /opt/osrm/docker-compose.yml restart osrm
echo "$(date) граф обновлён: $CUR -> $NEW, ошибок проверки: $fail"
