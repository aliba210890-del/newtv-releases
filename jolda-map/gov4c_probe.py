# Разведка: сохранить main.js кадастровой карты для разбора
import ssl, urllib.request, gzip
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
u = "https://map.gov4c.kz/egkn/static/js/main.df021c09.chunk.js"
t = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://map.gov4c.kz/"}), timeout=90, context=ctx).read()
open("gov4c-main.js.gz", "wb").write(gzip.compress(t))
open("probe.txt", "w").write("ok %d" % len(t))
