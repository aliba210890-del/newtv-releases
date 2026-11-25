# Версия 2 (25.11.2026): дом ставится на крышу своей стороны улицы по порядку номеров, без соседей — по правилу
# «нечётные слева от начала улицы, начало — со стороны центра посёлка». EVAL=1 — только проверка точности на домах OSM.
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
P["addr"] = [a for a in P["addr"] if len(a) < 5]  # прошлые добавления из регистра собираем заново
addr = P["addr"]
have_pts = defaultdict(list)
for a in addr:
    have_pts[(skey(a[0]), str(a[1]).lower().replace(" ", ""))].append((a[2], a[3]))
def has(k, la0, ln0, R):
    # такой дом уже есть в базе именно в этом посёлке/городе (а не одноимённая улица в Астане)
    return any(dist(la0, ln0, la, ln) < R + 1500 for (la, ln) in have_pts.get(k, ()))
def add_have(k, la, ln): have_pts[k].append((la, ln))

# посёлки и города (центры) из базы
setl = defaultdict(list)
for p in P["pois"]:
    if p[1] in ("Город", "Посёлок", "Село", "Деревня", "Аул"):
        setl[norm(p[0])].append((p[2], p[3]))

# точные центры посёлков (по 2ГИС), если в OpenStreetMap точка стоит с краю
setl["жибек жолы"] = [(51.0745, 71.7659)]

# микрорайоны с известной точкой (из OpenStreetMap и наших дополнений) — для домов на улицах, которых нет на карте
# улицы/микрорайоны, стоящие ровно в центре посёлка, — следы прошлых сборок (домов без точки); убираем, чтобы не вели не туда
CENTERS = [c for v in setl.values() for c in v] + [(51.0811, 71.74459)]
def at_center(la, ln): return any(abs(la - a) < 0.0004 and abs(ln - b) < 0.0006 for (a, b) in CENTERS)
# улица остаётся (её ищут по названию), но переезжает в нынешний центр посёлка; микрорайон-дубль, у которого есть настоящая точка, убираем
CUR = [c for v in setl.values() for c in v]
real_area = defaultdict(list)
for p in P["pois"]:
    if p[1] in ("Район", "ЖК") and not at_center(p[2], p[3]): real_area[skey(p[0])].append((p[2], p[3]))
_keep, _drop, _moved = [], 0, 0
for p in P["pois"]:
    if p[1] in ("Улица", "Район") and at_center(p[2], p[3]):
        if p[1] == "Район" and any(math.hypot((a - p[2]) * 111, (b - p[3]) * 69) < 5 for (a, b) in real_area.get(skey(p[0]), ())):
            _drop += 1; continue
        c = min(CUR, key=lambda c: (c[0] - p[2]) ** 2 + (c[1] - p[3]) ** 2)
        if math.hypot((c[0] - p[2]) * 111, (c[1] - p[3]) * 69) < 3 and (c[0], c[1]) != (p[2], p[3]):
            p[2], p[3] = c[0], c[1]; _moved += 1
    _keep.append(p)
P["pois"] = _keep
print("следы в центрах посёлков: убрано дублей", _drop, "перенесено", _moved)
areas = defaultdict(list)
for p in P["pois"]:
    if p[1] in ("Район", "ЖК") and not (len(p) > 4 and p[4]):
        areas[skey(p[0])].append((p[2], p[3]))

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
def streets_near(cs, R=4000):
    key = (tuple(cs), R)
    if key in _sn: return _sn[key]
    out = []
    for kk, mids in skeys_pts.items():
        if any(dist(la0, ln0, m[0], m[1]) < R for (la0, ln0) in cs for m in mids):
            out.append(kk)
    _sn[key] = out
    return out

# здания: сетка 0.002°
B = json.load(gzip.open(BLD, "rt"))["b"]
bgrid = defaultdict(list)
bgrid2 = defaultdict(list)
import os
EVAL = os.environ.get("EVAL") == "1"
EV = {"старый способ": [], "с соседями": [], "без соседей": []}
ON_ROOF = [0]
for b in B:
    if b[2] < 35 or b[2] > 3000:
        continue
    bgrid[(int(b[0] / 0.002), int(b[1] / 0.002))].append((b[0], b[1]))
    if b[2] >= 40: bgrid2[(int(b[0] / 0.002), int(b[1] / 0.002))].append((b[0], b[1], b[2]))

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
    big = norm(s["loc"]) == "астана"
    R = 28000 if big else 9000 if s.get("loc_type", "").startswith("Город") else 4000
    best = None
    kw = set(k.split())
    cands = [k] + [kk for kk in streets_near(cs, R) if kk != k and kw and set(kk.split()) and (set(kk.split()) <= kw or kw <= set(kk.split())) and max(map(len, kw & set(kk.split())), default=0) >= 4]
    for (la0, ln0) in cs:
        lines = []
        for kk in cands:
            lines = [(pts, nm) for (pts, nm) in streets.get(kk, []) if any(dist(la0, ln0, p[0], p[1]) < R for p in pts[:: max(1, len(pts) // 5)] + [pts[-1]])]
            if lines: break
        if lines and (best is None or len(lines) > len(best[1])):
            best = ((la0, ln0), lines)
    if not best and (big or s.get("loc_type", "").startswith("Город")):
        nostreet += 1
        continue
    if not best:
        nostreet += 1
        # улицы нет на карте — адрес всё равно показываем (точку человек уточнит): в центр микрорайона, если он известен, иначе в центр посёлка
        la0, ln0 = cs[0]
        for (pla, pln) in areas.get(skey(s["street"]), ()):
            if dist(la0, ln0, pla, pln) < R + 3000 and dist(la0, ln0, pla, pln) > 50:
                la0, ln0 = pla, pln; break
        disp0 = ("улица " if s.get("stype", "ул.") in ("ул.", "") else (s["stype"] + " ")) + s["street"]
        for h in s["h"]:
            hn = h.lower().replace(" ", "")
            if has((skey(disp0), hn), la0, ln0, R): continue
            addr.append([disp0, h, round(la0, 5), round(ln0, 5), 2]); add_have((skey(disp0), hn), la0, ln0); unplaced += 1
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
        if dist(la0, ln0, la, ln) > R + 500:
            continue
        x, y = (ln - cx) * kx, (la - cy) * ky
        kn.append((n, x * ux + y * uy, side_of(x, y), la, ln, raw))
    # начало улицы — конец ближе к центру посёлка; номера растут от него (правило нумерации)
    x0, y0 = (ln0 - cx) * kx, (la0 - cy) * ky
    t0c = x0 * ux + y0 * uy
    dirn = 1 if abs(t0c - tmin) <= abs(t0c - tmax) else -1
    tstart, tend = (tmin, tmax) if dirn == 1 else (tmax, tmin)
    # дома (крыши) вдоль улицы: сторона, расстояние до улицы, место по оси
    bl = []
    gi0, gi1 = int((cy + min(y for x, y in XY) / ky - 0.0007) / 0.002), int((cy + max(y for x, y in XY) / ky + 0.0007) / 0.002)
    gj0, gj1 = int((cx + min(x for x, y in XY) / kx - 0.001) / 0.002), int((cx + max(x for x, y in XY) / kx + 0.001) / 0.002)
    if (gi1 - gi0 + 1) * (gj1 - gj0 + 1) < 4000:
        for gi in range(gi0, gi1 + 1):
            for gj in range(gj0, gj1 + 1):
                for (bla, bln, bar) in bgrid2.get((gi, gj), ()):
                    x, y = (bln - cx) * kx, (bla - cy) * ky
                    t = x * ux + y * uy
                    if t < tmin - 40 or t > tmax + 40: continue
                    (px, py), (dx, dy) = on_street(t)
                    dd = math.hypot(x - px, y - py)
                    if 5 <= dd <= 55:
                        bl.append([t, 1 if (dx * (y - py) - dy * (x - px)) > 0 else -1, bar, bla, bln])
    # один дом на участок: соседние крыши ближе 9 м по оси — оставляем самую большую (сараи и бани отпадают)
    roofs = {1: [], -1: []}
    for sd in (1, -1):
        L = sorted([b for b in bl if b[1] == sd])
        for b in L:
            if roofs[sd] and abs(b[0] - roofs[sd][-1][0]) < 9:
                if b[2] > roofs[sd][-1][2]: roofs[sd][-1] = b
            else:
                roofs[sd].append(b)
    def side_for(par, anchors):
        v = [a[2] for a in anchors if a[0] % 2 == par]
        if v: return 1 if sum(v) >= 0 else -1
        v = [a[2] for a in anchors if a[0] % 2 != par]
        if v: return -(1 if sum(v) >= 0 else -1)
        # нечётные — слева по ходу нумерации: слева = side -1 при движении по оси вперёд
        left = -1 if dirn == 1 else 1
        return left if par == 1 else -left
    def target_t(n, rank, cnt, anchors):
        same = sorted([(a[0], a[1]) for a in anchors if a[0] % 2 == n % 2]) or sorted([(a[0], a[1]) for a in anchors])
        if same:
            lo = [x for x in same if x[0] <= n]; hi = [x for x in same if x[0] >= n]
            if lo and hi and hi[0][0] != lo[-1][0]:
                (n1, t1), (n2, t2) = lo[-1], hi[0]
                return t1 + (t2 - t1) * (n - n1) / (n2 - n1)
            if len(same) >= 2 and same[-1][0] != same[0][0]:
                (n1, t1), (n2, t2) = same[0], same[-1]
                return t1 + (t2 - t1) * (n - n1) / (n2 - n1)
            # один сосед: шаг ~20 м на номер той же чётности в сторону роста номеров
            n1, t1 = same[0]
            return t1 + dirn * (n - n1) / 2 * 20
        return tstart + (tend - tstart) * (rank + 0.5) / max(1, cnt)
    def place(n, rank, cnt, anchors, taken):
        t = max(tmin - 30, min(tmax + 30, target_t(n, rank, cnt, anchors)))
        sd = side_for(n % 2, anchors)
        best, bd = None, 70
        for b in roofs[sd]:
            if id(b) in taken: continue
            d = abs(b[0] - t)
            if d < bd: best, bd = b, d
        if best is not None:
            taken.add(id(best))
            return best[3], best[4], True
        (px, py), (dx, dy) = on_street(t)
        ox, oy = px - dy * 18 * sd, py + dx * 18 * sd
        return cy + oy / ky, cx + ox / kx, False
    def taken_by(anchors):
        tk = set()
        for a in anchors:
            for sd in (1, -1):
                for b in roofs[sd]:
                    if dist(a[3], a[4], b[3], b[4]) < 15: tk.add(id(b))
        return tk
    if EVAL:
        if not big and len(kn) >= 3:
            for i, h0 in enumerate(kn):
                rest = kn[:i] + kn[i + 1:]
                for mode, anch in (("с соседями", rest), ("без соседей", [])):
                    same_par = sorted(x[0] for x in kn if x[0] % 2 == h0[0] % 2)
                    rk = same_par.index(h0[0]); cnt = len(same_par)
                    la, ln, onroof = place(h0[0], rk, cnt, anch, taken_by(anch))
                    EV[mode].append(dist(la, ln, h0[3], h0[4]))
                # старая расстановка — для сравнения
                n = h0[0]
                same = sorted([(x[0], x[1]) for x in rest if x[0] % 2 == n % 2]) or sorted([(x[0], x[1]) for x in rest])
                if same:
                    lo = [x for x in same if x[0] <= n]; hi = [x for x in same if x[0] >= n]
                    if lo and hi and hi[0][0] != lo[-1][0]:
                        (n1, t1), (n2, t2) = lo[-1], hi[0]; t = t1 + (t2 - t1) * (n - n1) / (n2 - n1)
                    elif len(same) >= 2 and same[-1][0] != same[0][0]:
                        (n1, t1), (n2, t2) = same[0], same[-1]; t = t1 + (t2 - t1) * (n - n1) / (n2 - n1)
                    else: t = same[0][1]
                    t = max(tmin - 30, min(tmax + 30, t))
                    sp = {}
                    for par in (0, 1):
                        v = [x[2] for x in rest if x[0] % 2 == par]
                        if v: sp[par] = 1 if sum(v) >= 0 else -1
                    if 0 in sp and 1 not in sp: sp[1] = -sp[0]
                    if 1 in sp and 0 not in sp: sp[0] = -sp[1]
                    sd = sp.get(n % 2, 1)
                    (px, py), (dx, dy) = on_street(t)
                    ox, oy = px - dy * 18 * sd, py + dx * 18 * sd
                    la, ln = cy + oy / ky, cx + ox / kx
                    bb = near_bld(la, ln)
                    if bb: la, ln = bb
                    EV["старый способ"].append(dist(la, ln, h0[3], h0[4]))
        continue
    hs = [(numint(h), h) for h in s["h"] if numint(h) is not None]
    taken = taken_by(kn)
    for par in (1, 0):
        grp = sorted([x for x in hs if x[0] % 2 == par])
        for rk, (n, h) in enumerate(grp):
            hn = h.lower().replace(" ", "")
            if has((skey(disp), hn), la0, ln0, R) or has((skey("улица " + s["street"]), hn), la0, ln0, R):
                exact += 1
                continue
            la, ln, onroof = place(n, rk, len(grp), kn, taken)
            addr.append([disp, h, round(la, 5), round(ln, 5), 1])
            add_have((skey(disp), hn), la, ln)
            added += 1
            if onroof: ON_ROOF[0] += 1
print(f"register streets {len(AR)}; added {added}; unplaced(center) {unplaced}; already {exact}; no street {nostreet}; no settlement {nosett}; on roof {ON_ROOF[0]}")
if EVAL:
    for kname, v in EV.items():
        v = sorted(v)
        if v: print(f"ПРОВЕРКА {kname}: домов {len(v)}, медиана {v[len(v)//2]:.0f} м, до 30 м {100*sum(1 for x in v if x<=30)/len(v):.0f}%, до 60 м {100*sum(1 for x in v if x<=60)/len(v):.0f}%")
    raise SystemExit(0)
P["ar"] = "Адресный регистр РК (address-registry.itanalytics.kz) + контуры зданий Overture"
json.dump(P, gzip.open(PLACES, "wt"), ensure_ascii=False, separators=(",", ":"))
