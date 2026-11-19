# Разведка: публичная кадастровая карта (aisgzk.kz) — есть ли адреса домов с координатами
import re, urllib.request, json, ssl
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
out = []
def get(u, n=400000):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40, context=ctx).read(n).decode("utf-8", "ignore")
    except Exception as e:
        return "ERR " + str(e)
p = get("https://aisgzk.kz/aisgzk/ru/content/maps/")
out.append("PAGE len %d" % len(p))
urls = sorted(set(re.findall(r'https?://[^\s"\'<>]+', p)))
out += ["URL " + u for u in urls if any(k in u.lower() for k in ("arcgis", "rest", "wms", "map", "geo", "service", "js"))][:80]
for js in [u for u in urls if u.endswith(".js")][:15]:
    t = get(js, 2000000)
    for m in sorted(set(re.findall(r'(https?://[^\s"\'<>]*(?:arcgis|MapServer|FeatureServer|wms|geoserver)[^\s"\'<>]*)', t, re.I)))[:30]:
        out.append("JS " + js.split("/")[-1] + " -> " + m)
    for m in sorted(set(re.findall(r'["\'](/[^"\']*(?:MapServer|FeatureServer|geoserver|wms|arcgis)[^"\']*)["\']', t, re.I)))[:30]:
        out.append("JSREL " + js.split("/")[-1] + " -> " + m)
for base in ["https://aisgzk.kz/arcgis/rest/services?f=json", "https://aisgzk.kz/server/rest/services?f=json", "https://gis.aisgzk.kz/arcgis/rest/services?f=json", "https://map.gov4c.kz/", "https://egkn.gov4c.kz/"]:
    out.append("TRY " + base + " => " + get(base, 3000)[:600].replace("\n", " "))
open("out.txt", "w").write("\n".join(out))
print(len(out))
