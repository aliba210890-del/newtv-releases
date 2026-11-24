#!/bin/bash
# Один раз: включить ключ доступа и обновление без паузы.
#   curl -fsSL https://raw.githubusercontent.com/aliba210890-del/newtv-releases/main/jolda-osrm/upgrade.sh | bash -s КЛЮЧ
set -euo pipefail
KEY="${1:-}"; [ ${#KEY} -ge 24 ] || { echo "== ОШИБКА: нужен ключ (вставьте команду целиком) =="; exit 1; }
cd /opt/osrm
R=${R:-https://raw.githubusercontent.com/aliba210890-del/newtv-releases/main/jolda-osrm}
for f in docker-compose.yml Caddyfile check_routes.txt update.sh; do curl -fsSL -o "$f" "$R/$f"; done
chmod +x update.sh
HOST=$(grep '^HOST=' .env | cut -d= -f2)
printf 'HOST=%s\nKEY=%s\n' "$HOST" "$KEY" > .env && chmod 600 .env
docker compose -f /opt/osrm/docker-compose.yml up -d
sleep 6
A=$(curl -s -o /dev/null -w '%{http_code}' -H "X-Jolda-Key: $KEY" "https://$HOST/route/v1/driving/71.43,51.13;71.76,51.07?overview=false")
B=$(curl -s -o /dev/null -w '%{http_code}' "https://$HOST/route/v1/driving/71.43,51.13;71.76,51.07?overview=false")
if [ "$A" = 200 ] && [ "$B" = 403 ]; then echo "== ГОТОВО: сервер отвечает только Jolda =="; else echo "== ПРОВЕРКА: с ключом $A, без ключа $B — пришлите этот текст =="; docker compose -f /opt/osrm/docker-compose.yml logs --tail 20 caddy; fi
