# Разведка: REST кадастровой карты — поиск участка по кадастровому номеру/адресу
import ssl, urllib.request, urllib.parse, json
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
R = "https://map.gov4c.kz/egkn/rest"
def get(p, n=4000):
    try: return urllib.request.urlopen(urllib.request.Request(R + p, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://map.gov4c.kz/egkn/"}), timeout=60, context=ctx).read().decode("utf-8", "ignore")[:n]
    except Exception as e: return "ERR " + str(e)
out = []
out.append("LAYERS " + get("/map/layers?lang=ru", 6000))
q = urllib.parse.quote
for s in ["01-011-082-017", "01011082017", "Орталық 24", "Сарыадыр"]:
    for L in ["lands", "", "lands,address"]:
        out.append(f"SEARCH {s} [{L}] " + get(f"/map/search?searchText={q(s)}&offset=0&limit=5&lang=ru&layers={L}", 2500))
out.append("GET " + get("/map/get?x=71.7659&y=51.0745&layers=lands&lang=ru", 2500))
out.append("LAYER " + get("/map/layer?name=lands&pageNum=1&pageSize=3&lang=ru&readySite=false", 2500))
open("probe.txt", "w").write("\n".join(o.replace("\n", " ") for o in out))
