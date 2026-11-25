# Разведка: id районов и выборка участков u_view/nu_view с viewparams
import ssl, urllib.request, urllib.parse, json, re
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
G = "https://map.gov4c.kz/geoserver/egkn/wfs"
def get(u, n=3000):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://map.gov4c.kz/egkn/"}), timeout=120, context=ctx).read().decode("utf-8", "ignore")[:n]
    except Exception as e: return "ERR " + str(e)
out = []
d = get("https://map.gov4c.kz/egkn/rest/map/districts?lang=ru", 10**7)
out.append("DISTR " + d[:200])
ids = []
try:
    for x in json.loads(d):
        s = json.dumps(x, ensure_ascii=False)
        if re.search("Аршал|Целиноград|Акмол|Астан", s): out.append("D " + s[:400]); ids.append(x)
except Exception as e: out.append("DERR " + str(e))
def find(o, keys=("id",)):
    return [o.get(k) for k in keys]
for x in ids[:6]:
    did = x.get("id")
    for lay in ["egkn:u_view", "egkn:nu_view", "egkn:ned_view"]:
        q = {"service": "WFS", "version": "1.1.0", "request": "GetFeature", "typeName": lay, "outputFormat": "application/json", "maxFeatures": "2", "viewparams": f"district_id:{did}"}
        r = get(G + "?" + urllib.parse.urlencode(q), 2500)
        out.append(f"V {did} {lay} " + re.sub(r'"coordinates":\[\[\[\[[^\]]+\]', '"coordinates":[[[[..]', r))
        q.update({"resultType": "hits"}); q.pop("outputFormat")
        out.append(f"HITS {did} {lay} " + get(G + "?" + urllib.parse.urlencode(q), 600))
open("probe.txt", "w").write("\n".join(o.replace("\n", " ") for o in out))
