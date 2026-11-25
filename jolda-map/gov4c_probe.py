# Разведка: REST кадастровой карты — поиск участка по кадастровому номеру/адресу
import ssl, urllib.request, urllib.parse, json
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
R = "https://map.gov4c.kz/egkn/rest"
def get(p, n=4000):
    try: return urllib.request.urlopen(urllib.request.Request(R + p, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://map.gov4c.kz/egkn/"}), timeout=60, context=ctx).read().decode("utf-8", "ignore")[:n]
    except Exception as e: return "ERR " + str(e)
out = []
L = get("/map/layers?lang=ru", 10**7)
import re
names = sorted(set(re.findall(r'"name":"([a-z_0-9]+)"', L)))
out.append("NAMES " + " ".join(names))
nu = [n for n in names if n.startswith("nu_")]
import math
x = 71.7659 * 20037508.34 / 180; y = math.log(math.tan((90 + 51.0745) * math.pi / 360)) * 6378137
for lay in [",".join(nu)] + nu[:15]:
    out.append(f"GET3857 [{lay}] " + get(f"/map/get?x={x}&y={y}&layers={lay}&lang=ru", 3000))
for s2 in ["01-011-082-017", "Жибек"]:
    out.append(f"SEARCHNU {s2} " + get(f"/map/search?searchText={urllib.parse.quote(s2)}&offset=0&limit=5&lang=ru&layers={','.join(nu)}", 3000))
q = urllib.parse.quote
for s in ["01-011-082-017", "01011082017", "Орталық 24", "Сарыадыр"]:
    for L in ["lands", "", "lands,address"]:
        out.append(f"SEARCH {s} [{L}] " + get(f"/map/search?searchText={q(s)}&offset=0&limit=5&lang=ru&layers={L}", 2500))
out.append("GET " + get("/map/get?x=71.7659&y=51.0745&layers=lands&lang=ru", 2500))
out.append("LAYER " + get("/map/layer?name=lands&pageNum=1&pageSize=3&lang=ru&readySite=false", 2500))
open("probe.txt", "w").write("\n".join(o.replace("\n", " ") for o in out))
