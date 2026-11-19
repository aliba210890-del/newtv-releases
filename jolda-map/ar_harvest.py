# Адресный регистр РК: все улицы и дома посёлков вокруг Астаны → ar-ast.json.gz
import urllib.request, urllib.parse, json, ssl, gzip, time, sys, re
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
# все населённые пункты РК постранично, берём районы вокруг Астаны
ALL = allpages("localities?x=1")
print("all localities", len(ALL), flush=True)
locs = [x for x in ALL if "Акмолинская" in x["full_path_rus"] and (any(("р-н " + d) in x["full_path_rus"] for d in DIST) or "г. Косшы" in x["full_path_rus"])] + [x for x in ALL if x["full_path_rus"].startswith("Республика Казахстан, г. Астана")]
ids = {x["id"] for x in locs}
q = [x["id"] for x in locs]
while q:  # дети каждого округа/посёлка — постраничный список мог что-то пропустить
    for c in allpages(f"localities?parent_id={q.pop()}"):
        if c["id"] not in ids: ids.add(c["id"]); locs.append(c); q.append(c["id"])
print("localities", len(locs), flush=True)
# все улицы РК постранично (у части посёлков нет связи parent_id) → фильтр по пути
def page(off):
    return get(f"geonims?limit=500&offset={off}")
GE, off, step = [], 0, 8
while True:
    with ThreadPoolExecutor(8) as ex: chunk = list(ex.map(page, range(off, off + 500 * step, 500)))
    for c in chunk: GE += c
    off += 500 * step
    if any(len(c) < 500 for c in chunk): break
print("all geonims", len(GE), flush=True)
DP = tuple("р-н " + d for d in DIST)
def want(path): return ("Акмолинская" in path and (any(d in path for d in DP) or "г. Косшы" in path)) or path.startswith("Республика Казахстан, г. Астана")
S = []
for g in GE:
    p0 = g.get("full_path_rus") or ""
    if not want(p0): continue
    parts = [x.strip() for x in p0.split(",")]
    loc = next((x for x in reversed(parts[:-1]) if re.match(r"^(с\.|п\.|г\.|ст\.|а\.|д\.|рзд\.)\s", x)), parts[-2] if len(parts) > 1 else "")
    lt = loc.split(" ", 1)[0]; ln = loc.split(" ", 1)[1] if " " in loc else loc
    S.append(({"name_rus": ln, "ats_type": {"value_ru": {"с.": "Село", "п.": "Посёлок", "г.": "Город", "ст.": "Станция"}.get(lt, lt)}}, g))
print("streets", len(S), flush=True)
def houses(lg):
    l, g = lg
    b = allpages(f"buildings?geonim_id={g['id']}")
    return {"loc": l["name_rus"], "loc_type": l["ats_type"]["value_ru"], "path": g["full_path_rus"], "street": g["name_rus"], "stype": (g.get("geonims_type") or {}).get("short_value_ru", ""), "h": sorted({str(x.get("number") or "").strip() for x in b if x.get("actual", True)} - {""})}
with ThreadPoolExecutor(8) as ex: H = list(ex.map(houses, S))
H = [h for h in H if h["h"]]
print("streets with houses", len(H), "houses", sum(len(h["h"]) for h in H), flush=True)
json.dump(H, gzip.open("ar-ast.json.gz", "wt"), ensure_ascii=False, separators=(",", ":"))
