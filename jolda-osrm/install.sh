#!/bin/bash
# Установка сервера маршрутов Jolda одной командой (Ubuntu 22.04/24.04):
#   curl -fsSL https://raw.githubusercontent.com/aliba210890-del/newtv-releases/main/jolda-osrm/install.sh | bash -s route.joldataxi.kz
set -euo pipefail
trap 'echo "== ОШИБКА на шаге выше: пришлите этот текст =="' ERR
HOST="${1:-route.joldataxi.kz}"
R=https://raw.githubusercontent.com/aliba210890-del/newtv-releases/main/jolda-osrm
echo "== Jolda: сервер маршрутов для $HOST =="
export DEBIAN_FRONTEND=noninteractive
APT="apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3"
$APT update -qq || echo "предупреждение: одно из хранилищ Ubuntu недоступно, продолжаю"
$APT install -y -qq zstd jq curl python3 cron >/dev/null || { echo "повтор через основное зеркало Ubuntu"; \
  sed -i 's#http://[a-z0-9.-]*/ubuntu#http://archive.ubuntu.com/ubuntu#g' /etc/apt/sources.list /etc/apt/sources.list.d/*.sources 2>/dev/null || true; \
  $APT update -qq || true; $APT install -y -qq zstd jq curl python3 cron >/dev/null; }
command -v docker >/dev/null || $APT install -y -qq docker.io >/dev/null || curl -fsSL https://get.docker.com | sh >/dev/null
docker compose version >/dev/null 2>&1 || $APT install -y -qq docker-compose-v2 >/dev/null || $APT install -y -qq docker-compose-plugin >/dev/null
systemctl enable --now docker cron >/dev/null 2>&1 || true
timedatectl set-timezone Asia/Almaty 2>/dev/null || true
# запас памяти: 2 ГБ подкачки, чтобы проверочный сервер при обновлении не упирался в память
if ! swapon --show | grep -q swapfile; then
  fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q /swapfile /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
mkdir -p /opt/osrm && cd /opt/osrm
for f in docker-compose.yml update.sh check_routes.txt; do curl -fsSL -o "$f" "$R/$f"; done
chmod +x update.sh
echo "HOST=$HOST" > .env
echo "== загрузка карты дорог Казахстана (несколько минут) =="
bash /opt/osrm/update.sh
docker compose -f /opt/osrm/docker-compose.yml up -d
{ crontab -l 2>/dev/null | grep -v osrm/update.sh || true; echo "0 4 * * 0 bash /opt/osrm/update.sh >> /var/log/osrm-update.log 2>&1"; } | crontab -
sleep 5
if curl -sf "http://127.0.0.1:5000/route/v1/driving/71.43,51.13;71.76,51.07?overview=false" | grep -q '"Ok"'; then
  echo "== ГОТОВО: сервер маршрутов работает. IP этого сервера: $(hostname -I | cut -d" " -f1) =="
else
  echo "== ОШИБКА: сервер не ответил, пришлите этот текст =="; docker compose -f /opt/osrm/docker-compose.yml logs --tail 30 osrm
fi
