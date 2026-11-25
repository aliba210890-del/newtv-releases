#!/bin/bash
# АТС Jolda на сервере маршрутов (Hoster.kz) одной командой, от root:
#   curl -fsSL https://raw.githubusercontent.com/aliba210890-del/newtv-releases/main/jolda-sip/install.sh | bash -s КЛЮЧ_ПАРКА
# GoIP парка регистрируется сюда через интернет (белый IP у парка не нужен), диспетчеры звонят из браузера,
# автозвонок клиентам идёт отсюда же. Линии и пароли берутся из Jolda (sync.py), автозвонок — jolda-autocall.py.
set -euo pipefail
trap 'echo "== ОШИБКА на шаге выше: пришлите этот текст =="' ERR
KEY="${1:-}"; [ ${#KEY} -ge 24 ] || { echo "== ОШИБКА: нужен ключ парка (вставьте команду целиком) =="; exit 1; }
R=${R:-https://raw.githubusercontent.com/aliba210890-del/newtv-releases/main}
S=$R/jolda-sip
echo "== Jolda: телефонная станция =="
export DEBIAN_FRONTEND=noninteractive
APT="apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3"
$APT update -qq || echo "предупреждение: одно из хранилищ Ubuntu недоступно, продолжаю"
$APT install -y -qq asterisk python3 curl iptables >/dev/null
$APT install -y -qq ffmpeg python3-pip >/dev/null
python3 -m pip install -q edge-tts --break-system-packages 2>/dev/null || python3 -m pip install -q edge-tts
IP=$(curl -4 -fsS https://api.ipify.org 2>/dev/null || hostname -I | cut -d" " -f1)
echo "IP сервера: $IP"

cd /etc/asterisk
[ -f pjsip.conf.orig ] || cp -a pjsip.conf pjsip.conf.orig 2>/dev/null || true
[ -f extensions.conf.orig ] || cp -a extensions.conf extensions.conf.orig 2>/dev/null || true
for f in pjsip.conf extensions.conf http.conf rtp.conf; do curl -fsSL -o "$f" "$S/$f"; done
sed -i "s/__PUBLIC_IP__/$IP/g" pjsip.conf
touch pjsip_jolda.conf extensions_jolda.conf
# старый драйвер chan_sip мешает WebSocket — не загружаем
grep -q '^noload => chan_sip.so' modules.conf || echo 'noload => chan_sip.so' >> modules.conf
chown -R asterisk: /etc/asterisk

mkdir -p /opt/jolda-sip
for f in sync.py jolda-autocall.py; do curl -fsSL -o "/opt/jolda-sip/$f" "$S/$f"; done
printf 'KEY=%s\nURL=https://joldataxi.kz\n' "$KEY" > /etc/jolda-tel.conf
chown asterisk /etc/jolda-tel.conf && chmod 600 /etc/jolda-tel.conf
mkdir -p /var/lib/asterisk/sounds/jolda && chown -R asterisk: /var/lib/asterisk/sounds/jolda

# порт 8088 (вход для Caddy) — только изнутри сервера и из docker, снаружи закрыт; правило ставится при каждом запуске
cat > /etc/systemd/system/jolda-sip-fw.service <<'EOF'
[Unit]
Description=Jolda АТС: закрыть порт 8088 снаружи
After=network-online.target docker.service
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/sh -c 'iptables -C INPUT -p tcp --dport 8088 -j JOLDA8088 2>/dev/null || { iptables -N JOLDA8088 2>/dev/null; iptables -F JOLDA8088; iptables -A JOLDA8088 -s 127.0.0.0/8 -j RETURN; iptables -A JOLDA8088 -s 172.16.0.0/12 -j RETURN; iptables -A JOLDA8088 -j DROP; iptables -I INPUT -p tcp --dport 8088 -j JOLDA8088; }'
[Install]
WantedBy=multi-user.target
EOF
for n in sync autocall; do
  cat > /etc/systemd/system/jolda-$n.service <<EOF
[Unit]
Description=Jolda АТС: $n
After=network-online.target asterisk.service
[Service]
Environment=JCONF=/etc/jolda-tel.conf
ExecStart=/usr/bin/python3 /opt/jolda-sip/$( [ $n = sync ] && echo sync.py || echo jolda-autocall.py )
Restart=always
RestartSec=5
User=$( [ $n = sync ] && echo root || echo asterisk )
[Install]
WantedBy=multi-user.target
EOF
done
systemctl daemon-reload
systemctl enable --now jolda-sip-fw >/dev/null
systemctl enable asterisk >/dev/null 2>&1 || true
systemctl restart asterisk
sleep 4
JCONF=/etc/jolda-tel.conf python3 /opt/jolda-sip/sync.py --once
systemctl enable --now jolda-sync jolda-autocall >/dev/null

# если на сервере есть брандмауэр ufw — открыть SIP и голос
if command -v ufw >/dev/null && ufw status | grep -q active; then ufw allow 5060/udp >/dev/null; ufw allow 10000:20000/udp >/dev/null; fi

# вход для браузеров диспетчеров: sip.joldataxi.kz через Caddy сервера маршрутов
if [ -d /opt/osrm ]; then
  cd /opt/osrm
  for f in docker-compose.yml Caddyfile; do curl -fsSL -o "$f.new" "$R/jolda-osrm/$f" && mv "$f.new" "$f"; done
  docker compose -f /opt/osrm/docker-compose.yml up -d >/dev/null 2>&1
fi
sleep 8
asterisk -rx "pjsip show transports" | grep -E "transport-(udp|ws)" || true
W=$(curl --http1.1 --max-time 5 -s -o /dev/null -w '%{http_code}' -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' -H 'Sec-WebSocket-Protocol: sip' https://sip.joldataxi.kz/ws || true)
if python3 -m edge_tts --voice ru-RU-SvetlanaNeural --text "Проверка голоса Жолда." --write-media /tmp/jv.mp3 >/dev/null 2>&1; then echo "голос: работает"; else echo "голос: НЕ работает — пришлите этот текст"; fi
if [ "$W" = 101 ]; then echo "== ГОТОВО: телефонная станция работает (IP $IP) =="; else echo "== ПРОВЕРКА: вход для браузеров ответил $W — пришлите этот текст =="; fi
