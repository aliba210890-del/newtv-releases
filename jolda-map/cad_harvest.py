# Дома из публичной кадастровой карты (map.gov4c.kz, слой участков u_view) по районам вокруг Астаны.
# Результат: cad-<район>.txt.gz строками «посёлок|улица|дом|lat|lng» для /api/cadimport.
# Координаты пишутся так, чтобы после поправки cadFix в сервере (она рассчитана на старую загрузку) получилась точная точка.
import ssl, urllib.request, urllib.parse, json, re, gzip, sys, time, math, os
from pyproj import Transformer
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
G = "https://map.gov4c.kz/geoserver/egkn/wfs"
DIST = {5: "arshaly", 10: "tselinograd", 11: "shortandy", 272: "kosshy"}
def get(u):
    for i in range(6):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://map.gov4c.kz/egkn/"}), timeout=180, context=ctx).read().decode("utf-8", "ignore")
        except Exception as e: err = e; time.sleep(5 + 10 * i)
    raise err
# правильная проекция ЕГКН: поперечная Меркатора на GRS80, зоны 69° и 75°
TRUE = {12: Transformer.from_crs("+proj=tmerc +lat_0=0 +lon_0=69 +k=1 +x_0=12500000 +y_0=0 +ellps=GRS80 +units=m +no_defs", "EPSG:4326", always_xy=True),
        13: Transformer.from_crs("+proj=tmerc +lat_0=0 +lon_0=75 +k=1 +x_0=13500000 +y_0=0 +ellps=GRS80 +units=m +no_defs", "EPSG:4326", always_xy=True)}
OLD = {12: Transformer.from_crs("EPSG:28412", "EPSG:4326", always_xy=True), 13: Transformer.from_crs("EPSG:28413", "EPSG:4326", always_xy=True)}
CADFIX = {12: [[0.00046677974084917564, -5.081454021991727e-06, -1.084931173351045e-05, 7.056789958461318e-08, -1.2339216943893899e-07, -7.803743347927794e-08], [0.0009419705960429201, 2.7371817983134985e-05, 5.083345145051936e-06, 7.478926111449331e-07, 3.937543954836942e-07, -1.789301384556684e-07]],
  13: [[0.00046578598907090555, -5.090790371202227e-06, -8.360751354606312e-06, 7.217604076592712e-08, -9.990969731386591e-08, -7.61650904100121e-08], [0.0007264630800883227, 2.109352344265831e-05, 5.053650642348507e-06, 5.922609102454023e-07, 3.8430966533668335e-07, -1.4221785502877097e-07]]}
Z13 = {"жибек жолы", "аршалы", "жалтырколь", "михайловка", "ижевское", "елток", "волгодоновка", "акбулак", "мичурино", "арнасай", "бабатай", "койгельды", "вишневка", "42 разъезд", "александровка", "николаевка", "ольгинка", "костомар", "сараба", "булаксай", "акжар", "сары-оба"}
def zone_srv(loc, la, ln):
    k = loc.lower().replace("ё", "е").replace("қ", "к").replace("ң", "н"); k = re.sub(r"^с\.?\s*", "", k).strip()
    if k: return 13 if k in Z13 else 12
    return 13 if (ln > 71.72 and la < 51.17) else 12
def fix(la, ln, z):
    cA, cN = CADFIX[z]; y = la - 51.1; x = ln - 71.6; v = [1, y, x, y * y, x * y, x * x]
    return la + sum(a * b for a, b in zip(cA, v)), ln + sum(a * b for a, b in zip(cN, v))
def unfix(la, ln, z):  # точка, которая после fix() станет (la, ln)
    sa, sn = la, ln
    for _ in range(4):
        fa, fn = fix(sa, sn, z); sa += la - fa; sn += ln - fn
    return sa, sn
log = []
# проверка: разница «старый пересчёт → поправка» и «правильная проекция» должна быть ~0
for z, (x, y) in {12: (12690700, 5668700), 13: (13311000, 5628700)}.items():
    ol, oa = OLD[z].transform(x, y); tl, ta = TRUE[z].transform(x, y); fa, fn = fix(oa, ol, z)
    log.append(f"CHECK zone{z}: old+fix vs true = {math.hypot((fa - ta) * 111320, (fn - tl) * 111320 * math.cos(math.radians(ta))):.2f} m")
ADDR = re.compile(r"^(с\.|п\.|ст\.|рзд\.|а\.|г\.|мкр\.|ж\.м\.)\s*")
def parse(a):
    parts = [p.strip() for p in (a or "").split(",") if p.strip()]
    loc, street, house = "", [], ""
    for p in parts:
        if re.match(r"^(обл\.|р-н|с\.о\.|г\.а\.|п\.о\.)", p): continue
        if re.match(r"^(с\.|п\.|ст\.|рзд\.|а\.|г\.)\s", p) and not street and not loc: loc = ADDR.sub("", p); continue
        m = re.match(r"^(д\.|уч\.|участок|зд\.)\s*(.+)$", p)
        if m: house = m.group(2).strip(); continue
        if re.match(r"^(кв\.|пом\.|н\.п\.|корп)", p): continue
        street.append(p)
    return loc, ", ".join(street), house
def centroid(geom):
    best = None
    for poly in geom["coordinates"]:
        ring = poly[0]; A = cx = cy = 0
        for i in range(len(ring) - 1):
            x0, y0 = ring[i][:2]; x1, y1 = ring[i + 1][:2]; c = x0 * y1 - x1 * y0; A += c; cx += (x0 + x1) * c; cy += (y0 + y1) * c
        if A == 0: continue
        A /= 2; p = (abs(A), cx / (6 * A), cy / (6 * A))
        if not best or p[0] > best[0]: best = p
    return best
# здания (Overture: Microsoft/OSM/Google) — точка дома ставится на крышу самого большого здания внутри участка
B = {}
try:
    tok = os.environ.get("GH_TOKEN", "")
    rq = urllib.request.Request("https://api.github.com/repos/aliba210890-del/newtv-releases/releases/assets/766835894", headers={"Accept": "application/octet-stream", "Authorization": "Bearer " + tok})
    for la, ln, ar, *_ in json.loads(gzip.decompress(urllib.request.urlopen(rq, timeout=300).read()))["b"]:
        if ar >= 25: B.setdefault((int(la * 500), int(ln * 300)), []).append((la, ln, ar))
    log.append(f"buildings cells {len(B)}")
except Exception as e: log.append("buildings ERR " + str(e))
def inside(x, y, ring):
    c = False
    for i in range(len(ring) - 1):
        x0, y0 = ring[i]; x1, y1 = ring[i + 1]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0: c = not c
    return c
def roof(geom, z):
    best = None
    for poly in geom["coordinates"]:
        ring = [TRUE[z].transform(p[0], p[1]) for p in poly[0]]  # (lng, lat)
        lo = min(p[0] for p in ring); hi = max(p[0] for p in ring); sa = min(p[1] for p in ring); na = max(p[1] for p in ring)
        if (hi - lo) * (na - sa) > 0.00002: continue  # большой участок — не ищем
        for a in range(int(sa * 500), int(na * 500) + 1):
            for b in range(int(lo * 300), int(hi * 300) + 1):
                for la, ln, ar in B.get((a, b), ()):
                    if sa <= la <= na and lo <= ln <= hi and inside(ln, la, ring) and (not best or ar > best[2]): best = (la, ln, ar)
    return best
stat = {"roof": 0, "plot": 0}
only = [int(x) for x in sys.argv[1:]] or list(DIST)
for did in only:
    rows, seen, n, off, step = {}, 0, 0, 0, 2000
    while True:
        q = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "egkn:u_view", "outputFormat": "application/json", "count": str(step), "startIndex": str(off), "sortBy": "gid", "viewparams": f"district_id:{did}", "propertyName": "gid,kad_nomer,address_ru,geom"}
        j = json.loads(get(G + "?" + urllib.parse.urlencode(q)))
        fs = j.get("features", [])
        for f in fs:
            seen += 1; pr = f.get("properties") or {}; a = pr.get("address_ru") or ""
            loc, st, h = parse(a)
            if not (loc and st and h) or not f.get("geometry"): continue
            c = centroid(f["geometry"])
            if not c: continue
            x, y = c[1], c[2]; z = 13 if x >= 13e6 else 12
            ln, la = TRUE[z].transform(x, y)
            r = roof(f["geometry"], z) if B else None
            if r: la, ln = r[0], r[1]; stat["roof"] += 1
            else: stat["plot"] += 1
            k = (loc, st, h.lower())
            if k in rows and rows[k][2] >= c[0]: continue
            rows[k] = (la, ln, c[0], loc, st, h)
        off += len(fs)
        print(did, off, len(rows), flush=True)
        if len(fs) < step: break
    out = []
    for (la, ln, area, loc, st, h) in rows.values():
        if area > 20000: continue  # поля и большие участки — не дом
        sa, sn = unfix(la, ln, zone_srv(loc, la, ln))
        out.append(f"{loc}|{st}|{h}|{sa:.6f}|{sn:.6f}")
    with gzip.open(f"cad-{DIST[did]}.txt.gz", "wt", encoding="utf-8") as fo: fo.write("\n".join(out))
    from collections import Counter
    cnt = Counter(r[3] for r in rows.values())
    log.append(f"DIST {did} {DIST[did]}: parcels {seen}, houses {len(out)}; " + ", ".join(f"{a} {b}" for a, b in cnt.most_common(40)))
log.append(f"points: on roof {stat['roof']}, plot center {stat['plot']}")
open("probe.txt", "w").write("\n".join(log)); print("\n".join(log))
