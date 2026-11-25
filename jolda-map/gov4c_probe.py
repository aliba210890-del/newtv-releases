# Разведка 5: API кадастровой карты map.gov4c.kz — поиск участка по кадастровому номеру
import json, ssl, urllib.request, re
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
def get(u, n=8000000, data=None, h=None):
    hd = {"User-Agent": "Mozilla/5.0", "Referer": "https://map.gov4c.kz/", "Origin": "https://map.gov4c.kz"}
    if h: hd.update(h)
    try: return urllib.request.urlopen(urllib.request.Request(u, data=data, headers=hd), timeout=60, context=ctx).read(n).decode("utf-8", "ignore")
    except Exception as e: return "ERR " + str(e)
out = []
h = get("https://map.gov4c.kz/")
out.append("HTML " + h[:1500].replace("\n", " "))
js = sorted(set(re.findall(r'(?:src|href)="([^"]+\.js)"', h)))
for s in js:
    u = s if s.startswith("http") else "https://map.gov4c.kz/" + s.lstrip("./")
    t = get(u)
    out.append(f"FILE {u} len={len(t)}")
    for m in sorted(set(re.findall(r'["\'`]((?:https?:)?//[^"\'`\s]{4,200}|/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-/{}$.]{3,160})["\'`]', t))):
        if re.search(r"api|cad|kad|search|land|parcel|geo|arcgis|query|wfs|wms|egkn|gis", m, re.I) and "w3.org" not in m: out.append("  U " + m)
    for m in re.finditer(r'.{200}(kadNum|cadNum|kad_num|cad_num|cadastr|kadastr).{250}', t, re.I):
        out.append("  CTX " + m.group(0).replace("\n", " "))
open("probe.txt", "w").write("\n".join(out)); print(len(out))
