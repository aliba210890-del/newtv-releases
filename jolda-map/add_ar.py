# Дополняет базу адресов Jolda домами из Адресного регистра РК.
# Номера домов — из регистра, место — по соседним известным домам улицы (OpenStreetMap)
# и на ближайшую настоящую крышу (контуры зданий Overture/Microsoft).
# Запуск: add_ar.py astana-places.json.gz astana.geojsonseq ar-ast.json.gz ast-buildings.json.gz
import sys, json, gzip, math, re
from collections import defaultdict

PLACES, OSM, AR, BLD = sys.argv[1:5]
KZL = {"ә": "а", "ғ": "г", "қ": "к", "ң": "н", "ө": "о", "ұ": "у", "ү": "у", "һ": "х", "і": "и"}
STOP = {"улица", "ул", "переулок", "пер", "проспект", "пр", "проезд", "тупик", "туп", "микрорайон", "мкр", "шоссе", "бульвар", "бул",
        "кошеси", "коше", "кош", "даңгылы", "дангылы", "тыкыр", "тк", "квартал", "кв", "площадь", "пл", "трасса", "жолы_"}

def norm(t):
    t = str(t or "").lower().replace("ё", "е")
    t = "".join(KZL.get(c, c) for c in t)
    t = re.sub(r"[«»\"'.,()\-–—/№]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def skey(name):
    w = [x for x in norm(name).split() if x not in STOP]
    return " ".join(w)

def loose(k):
    # «Казыбек Би» = «Казыбек би», «Абая» = «Абай», «Ш. Уалиханова» = «Уалиханов»
    w = [x for x in k.split() if len(x) > 1]
    w = [re.sub(r"(ого|ой|ая|а|я|ы|и)$", "", x) if len(x) >= 5 else x for x in w]
    return " ".join(w)

P = json.load(gzip.open(PLACES, "rt"))
addr = P["addr"]
have = {(skey(a[0]), str(a[1]).lower().replace(" ", "")) for a in addr}

# посёлки и города (центры) из базы
setl = defaultdict(list)
for p in P["pois"]:
    if p[1] in ("Город", "Посёлок", "Село", "Деревня", "Аул"):
        setl[norm(p[0])].append((p[2], p[3]))

setl_loose = defaultdict(list)
for kk, v in setl.items():
    setl_loose[loose(re.sub(r"^имени\s+", "", kk))] += v

# улицы OpenStreetMap (линии)
streets = defaultdict(list)  # loose key -> list of polylines [(lat,lng),...]
with open(OSM, encoding="utf-8") as f:
    for line in f:
        if '"highway"' not in line or '"name' not in line:
            continue
        try:
            o = json.loads(line.lstrip("\x1e"))
        except Exception:
            continue
        g, t = o.get("geometry") or {}, o.get("properties") or {}
        if g.get("type") != "LineString" or t.get("highway") in ("footway", "path", "cycleway", "steps", "track"):
            continue
        pts = [(c[1], c[0]) for c in g["coordinates"]]
        names = {t.get(k) for k in ("name", "name:ru", "name:kk", "old_name") if t.get(k)}
        for n in names:
            streets[loose(skey(n))].append((pts, t.get("name:ru") or t.get("name")))

# ключи улиц рядом с посёлком (для нечёткого сравнения названий)
skeys_pts = defaultdict(list)
for kk, L in streets.items():
    for (pts, nm) in L:
        skeys_pts[kk].append(pts[len(pts) // 2])
_sn = {}
def streets_near(cs):
    key = tuple(cs)
    if key in _sn: return _sn[key]
    out = []
    for kk, mids in skeys_pts.items():
        if any(dist(la0, ln0, m[0], m[1]) < 4000 for (la0, ln0) in cs for m in mids):
            out.append(kk)
    _sn[key] = out
    return out

# здания: сетка 0.002°
B = json.load(gzip.open(BLD, "rt"))["b"]
bgrid = defaultdict(list)
for b in B:
    if b[2] < 35 or b[2] > 3000:
        continue
    bgrid[(int(b[0] / 0.002), int(b[1] / 0.002))].append((b[0], b[1]))

def near_bld(la, ln, rad_m=35):
    best, bd = None, rad_m
    gi, gj = int(la / 0.002), int(ln / 0.002)
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            for (bl, bn) in bgrid.get((gi + di, gj + dj), ()):
                d = dist(la, ln, bl, bn)
                if d < bd:
                    best, bd = (bl, bn), d
    return best

def dist(a, b, c, d):
    return math.hypot((c - a) * 110540, (d - b) * 111320 * math.cos(math.radians(a)))

# известные дома OSM по улицам
known = defaultdict(list)  # loose key -> [(num:int, raw, lat, lng)]
for a in addr:
    m = re.match(r"\d+", str(a[1]))
    if m:
        known[loose(skey(a[0]))].append((int(m.group()), str(a[1]), a[2], a[3]))

def numint(h):
    m = re.match(r"\d+", h)
    return int(m.group()) if m else None

AR = json.load(gzip.open(AR, "rt"))
added, nostreet, nosett, exact, unplaced = 0, 0, 0, 0, 0
for s in AR:
    k = loose(skey(s["street"]))
    if not k:
        continue
    cs = setl.get(norm(s["loc"])) or setl_loose.get(loose(norm(re.sub(r"^имени\s+", "", s["loc"], flags=re.I))))
    if not cs:
        nosett += 1
        continue
    # линии этой улицы рядом с посёлком (4 км)
    best = None
    kw = set(k.split())
    cands = [k] + [kk for kk in streets_near(cs) if kk != k and kw and set(kk.split()) and (set(kk.split()) <= kw or kw <= set(kk.split())) and max(map(len, kw & set(kk.split())), default=0) >= 4]
    for (la0, ln0) in cs:
        lines = []
        for kk in cands:
            lines = [(pts, nm) for (pts, nm) in streets.get(kk, []) if any(dist(la0, ln0, p[0], p[1]) < 4000 for p in pts[:: max(1, len(pts) // 5)] + [pts[-1]])]
            if lines: break
        if lines and (best is None or len(lines) > len(best[1])):
            best = ((la0, ln0), lines)
    if not best:
        nostreet += 1
        # улицы нет на карте — адрес всё равно показываем (точку человек уточнит), ставим в центр посёлка
        la0, ln0 = cs[0]
        disp0 = ("улица " if s.get("stype", "ул.") in ("ул.", "") else (s["stype"] + " ")) + s["street"]
        for h in s["h"]:
            hn = h.lower().replace(" ", "")
            if (skey(disp0), hn) in have: continue
            addr.append([disp0, h, round(la0, 5), round(ln0, 5), 2]); have.add((skey(disp0), hn)); unplaced += 1
        continue
    (la0, ln0), lines = best
    disp = lines[0][1] or ("улица " + s["street"])
    pts = [p for (pl, _) in lines for p in pl]
    # локальные метры
    cx, cy = sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)
    kx, ky = 111320 * math.cos(math.radians(cy)), 110540
    XY = [((p[1] - cx) * kx, (p[0] - cy) * ky) for p in pts]
    # главная ось улицы
    sxx = sum(x * x for x, y in XY); syy = sum(y * y for x, y in XY); sxy = sum(x * y for x, y in XY)
    ang = 0.5 * math.atan2(2 * sxy, sxx - syy)
    ux, uy = math.cos(ang), math.sin(ang)
    T = [x * ux + y * uy for x, y in XY]
    tmin, tmax = min(T), max(T)
    segs = [[((p[1] - cx) * kx, (p[0] - cy) * ky) for p in pl] for (pl, _) in lines]
    def on_street(t):
        # ближайшая точка самой улицы к точке оси t и направление участка
        ax, ay = t * ux, t * uy
        bd, bp, bdir = 1e18, (ax, ay), (ux, uy)
        for sg in segs:
            for (x1, y1), (x2, y2) in zip(sg, sg[1:]):
                dx, dy = x2 - x1, y2 - y1; L2 = dx * dx + dy * dy or 1e-9
                u = max(0, min(1, ((ax - x1) * dx + (ay - y1) * dy) / L2))
                px, py = x1 + u * dx, y1 + u * dy
                d = (px - ax) ** 2 + (py - ay) ** 2
                if d < bd:
                    L = math.sqrt(L2); bd, bp, bdir = d, (px, py), (dx / L, dy / L)
        return bp, bdir
    def side_of(x, y):
        (px, py), (dx, dy) = on_street(x * ux + y * uy)
        return 1 if (dx * (y - py) - dy * (x - px)) > 0 else -1
    kn = []
    for (n, raw, la, ln) in known.get(k, []):
        if dist(la0, ln0, la, ln) > 4500:
            continue
        x, y = (ln - cx) * kx, (la - cy) * ky
        kn.append((n, x * ux + y * uy, side_of(x, y)))
    side_par = {}
    for par in (0, 1):
        v = [sd for (n, t, sd) in kn if n % 2 == par]
        if v:
            side_par[par] = 1 if sum(v) >= 0 else -1
    if 0 in side_par and 1 not in side_par: side_par[1] = -side_par[0]
    if 1 in side_par and 0 not in side_par: side_par[0] = -side_par[1]
    if not side_par: side_par = {1: 1, 0: -1}
    maxn = max([numint(h) or 0 for h in s["h"]] + [1])
    for h in s["h"]:
        hn = h.lower().replace(" ", "")
        if (skey(disp), hn) in have or (skey("улица " + s["street"]), hn) in have:
            exact += 1
            continue
        n = numint(h)
        if n is None:
            continue
        same = sorted([(kn_n, t) for (kn_n, t, sd) in kn if kn_n % 2 == n % 2]) or sorted([(kn_n, t) for (kn_n, t, sd) in kn])
        if same:
            lo = [x for x in same if x[0] <= n]; hi = [x for x in same if x[0] >= n]
            if lo and hi and hi[0][0] != lo[-1][0]:
                (n1, t1), (n2, t2) = lo[-1], hi[0]
                t = t1 + (t2 - t1) * (n - n1) / (n2 - n1)
            elif len(same) >= 2:
                (n1, t1), (n2, t2) = (same[0], same[-1]) if same[-1][0] != same[0][0] else (same[0], same[0])
                t = t1 + ((t2 - t1) * (n - n1) / (n2 - n1) if n2 != n1 else 0)
            else:
                t = same[0][1]
            t = max(tmin - 30, min(tmax + 30, t))
        else:
            t = tmin + (tmax - tmin) * min(1, n / maxn)
        (px, py), (dx, dy) = on_street(t)
        sd = side_par[n % 2]
        ox, oy = px - dy * 18 * sd, py + dx * 18 * sd
        la, ln = cy + oy / ky, cx + ox / kx
        b = near_bld(la, ln)
        if b:
            la, ln = b
        addr.append([disp, h, round(la, 5), round(ln, 5), 1])
        have.add((skey(disp), hn))
        added += 1
print(f"register streets {len(AR)}; added {added}; unplaced(center) {unplaced}; already {exact}; no street {nostreet}; no settlement {nosett}")
P["ar"] = "Адресный регистр РК (address-registry.itanalytics.kz) + контуры зданий Overture"
json.dump(P, gzip.open(PLACES, "wt"), ensure_ascii=False, separators=(",", ":"))
