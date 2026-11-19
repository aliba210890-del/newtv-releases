# Адресный регистр РК: все улицы и дома посёлков вокруг Астаны → ar-ast.json.gz
import urllib.request, urllib.parse, json, ssl, gzip, time, sys
from concurrent.futures import ThreadPoolExecutor
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
B = "https://address-registry.itanalytics.kz/api/v1/"
def get(path, tries=4):
    for i in range(tries):
        try:
            t = urllib.request.urlopen(urllib.request.Request(B + path, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}), timeout=90, context=ctx).read().decode("utf-8", "ignore")
            return json.loads(t).get("result", [])
        except Exception as e:
            time.sleep(2 + i * 3)
    return []
def allpages(path):
    out, off = [], 0
    while True:
        r = get(f"{path}&limit=500&offset={off}")
        out += r
        if len(r) < 500: return out
        off += 500
DIST = ["Целиноградский", "Аршалынский", "Шортандинский", "Аккольский", "Ерейментауский", "Астраханский"]
roots = []
for d in DIST:
    r = get("localities?name=" + urllib.parse.quote(d.replace("ский", "")))
    roots += [x for x in r if "Акмолинская" in x["full_path_rus"] and x["ats_type"]["value_ru"].startswith("Район")]
r = get("localities?name=" + urllib.parse.quote("Косшы")); roots += [x for x in r if "Акмолинская" in x["full_path_rus"]]
print("roots", [(x["id"], x["full_path_rus"]) for x in roots], flush=True)
locs, q, seen = [], [x["id"] for x in roots], set()
while q:
    lid = q.pop()
    if lid in seen: continue
    seen.add(lid)
    ch = allpages(f"localities?parent_id={lid}")
    for c in ch:
        locs.append(c); q.append(c["id"])
locs += roots
print("localities", len(locs), flush=True)
def streets(l):
    return [(l, g) for g in allpages(f"geonims?locality_id={l['id']}")]
with ThreadPoolExecutor(8) as ex: S = [s for r in ex.map(streets, locs) for s in r]
print("streets", len(S), flush=True)
def houses(lg):
    l, g = lg
    b = allpages(f"buildings?geonim_id={g['id']}")
    return {"loc": l["name_rus"], "loc_type": l["ats_type"]["value_ru"], "path": g["full_path_rus"], "street": g["name_rus"], "stype": (g.get("geonims_type") or {}).get("short_value_ru", ""), "h": sorted({str(x.get("number") or "").strip() for x in b if x.get("actual", True)} - {""})}
with ThreadPoolExecutor(8) as ex: H = list(ex.map(houses, S))
H = [h for h in H if h["h"]]
print("streets with houses", len(H), "houses", sum(len(h["h"]) for h in H), flush=True)
json.dump(H, gzip.open("ar-ast.json.gz", "wt"), ensure_ascii=False, separators=(",", ":"))
