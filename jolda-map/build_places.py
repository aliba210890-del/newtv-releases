# База адресов и мест «Жолда» (Астана и пригороды) из свежего OpenStreetMap.
# Дополняет старую базу: всё, что было, остаётся; новое из OSM — добавляется.
import gzip, json, sys, time, urllib.request, urllib.parse

BBOX = (50.90, 71.05, 51.40, 71.85)  # юг, запад, север, восток — Астана с пригородами
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]

def q(body):
    b = "(%s,%s,%s,%s)" % BBOX
    data = "[out:json][timeout:900];(" + body.replace("{b}", b) + ");out center tags;"
    for url in OVERPASS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": data}).encode(), headers={"User-Agent": "jolda-places/1.0"})
                with urllib.request.urlopen(req, timeout=1000) as r:
                    return json.load(r)["elements"]
            except Exception as e:
                print("overpass", url, attempt, e, file=sys.stderr); time.sleep(20)
    raise SystemExit("Overpass недоступен")

def ll(e):
    if "lat" in e: return e["lat"], e["lon"]
    c = e.get("center") or {}
    return c.get("lat"), c.get("lon")

CAT = [
    (lambda t: t.get("landuse") == "residential" or t.get("residential") or (t.get("building") in ("apartments", "residential") and t.get("name")), "ЖК"),
    (lambda t: t.get("shop") == "mall" or t.get("amenity") == "marketplace" and False, "ТРЦ"),
    (lambda t: t.get("amenity") == "cafe", "Кафе"), (lambda t: t.get("amenity") == "restaurant", "Ресторан"),
    (lambda t: t.get("amenity") == "fast_food", "Фастфуд"), (lambda t: t.get("amenity") in ("bar", "pub"), "Бар"),
    (lambda t: t.get("amenity") == "fuel", "АЗС"), (lambda t: t.get("amenity") == "bank", "Банк"), (lambda t: t.get("amenity") == "pharmacy", "Аптека"),
    (lambda t: t.get("amenity") == "school", "Школа"), (lambda t: t.get("amenity") == "kindergarten", "Детсад"), (lambda t: t.get("amenity") in ("university", "college"), "Университет"),
    (lambda t: t.get("amenity") in ("hospital",), "Больница"), (lambda t: t.get("amenity") in ("clinic", "doctors") or t.get("healthcare"), "Клиника"),
    (lambda t: t.get("amenity") == "dentist", "Стоматология"), (lambda t: t.get("amenity") == "place_of_worship", "Храм/мечеть"),
    (lambda t: t.get("amenity") in ("theatre",), "Театр"), (lambda t: t.get("amenity") == "cinema", "Кинотеатр"), (lambda t: t.get("amenity") == "police", "Полиция"),
    (lambda t: t.get("amenity") == "post_office", "Почта"), (lambda t: t.get("amenity") == "car_wash", "Автомойка"), (lambda t: t.get("amenity") == "marketplace", "Рынок"),
    (lambda t: t.get("amenity") == "bus_station", "Автовокзал"), (lambda t: t.get("railway") == "station", "Вокзал"), (lambda t: t.get("aeroway") in ("aerodrome", "terminal"), "Аэропорт"),
    (lambda t: t.get("tourism") in ("hotel", "motel", "guest_house", "apartment"), "Отель"), (lambda t: t.get("tourism") == "hostel", "Хостел"), (lambda t: t.get("tourism") == "museum", "Музей"),
    (lambda t: t.get("tourism") in ("attraction", "viewpoint", "artwork"), "Достопримечательность"), (lambda t: t.get("leisure") == "park", "Парк"),
    (lambda t: t.get("leisure") in ("fitness_centre", "sports_centre", "sports_hall"), "Спорткомплекс"), (lambda t: t.get("leisure") == "stadium", "Стадион"),
    (lambda t: t.get("shop") in ("car_repair", "tyres", "car_parts") or t.get("craft") == "car_repair" or t.get("amenity") == "car_repair", "СТО"),
    (lambda t: t.get("shop") == "car", "Автосалон"), (lambda t: t.get("shop") in ("supermarket", "convenience"), "Магазин"),
    (lambda t: t.get("amenity") in ("nightclub", "karaoke_box") or t.get("leisure") in ("bowling_alley", "amusement_arcade", "escape_game", "water_park", "trampoline_park", "ice_rink"), "Развлечения"),
    (lambda t: t.get("leisure") in ("playground",), "Детская площадка"), (lambda t: t.get("amenity") in ("sauna",) or t.get("leisure") == "sauna", "Баня/сауна"),
    (lambda t: t.get("shop") in ("beauty", "hairdresser") or t.get("amenity") == "beauty", "Салон красоты"),
    (lambda t: t.get("shop") == "mall", "ТРЦ"), (lambda t: t.get("shop"), "Магазин"), (lambda t: t.get("office"), "Офис"),
    (lambda t: t.get("place") in ("village", "hamlet", "town", "suburb"), "Посёлок"), (lambda t: t.get("place") in ("neighbourhood", "quarter"), "Район"),
    (lambda t: t.get("amenity") or t.get("leisure") or t.get("tourism") or t.get("craft") or t.get("building"), "Здание"),
]
def cat(t):
    for f, c in CAT:
        try:
            if f(t): return c
        except Exception: pass
    return "Здание"

def main(old_path, out_path):
    old = json.load(gzip.open(old_path)) if old_path else {"pois": [], "addr": [], "cams": []}
    pois = {(p[0].lower(), round(p[2], 3), round(p[3], 3)): p for p in old["pois"]}
    addr = {(a[0].lower(), str(a[1]).lower(), round(a[2], 4), round(a[3], 4)): a for a in old["addr"]}
    n0p, n0a = len(pois), len(addr)
    els = q('nwr["name"]["landuse"="residential"]{b};nwr["name"]["residential"]{b};nwr["name"]["building"]{b};nwr["name"]["amenity"]{b};nwr["name"]["shop"]{b};nwr["name"]["office"]{b};nwr["name"]["tourism"]{b};nwr["name"]["leisure"]{b};nwr["name"]["healthcare"]{b};nwr["name"]["craft"]{b};nwr["name"]["place"]{b};nwr["name"]["railway"="station"]{b};nwr["name"]["aeroway"]{b};nwr["name"]["craft"]{b};nwr["name"]["sport"]{b}')
    for e in els:
        t = e.get("tags", {}); la, ln = ll(e)
        if la is None: continue
        name = (t.get("name:ru") or t.get("name") or "").strip()
        if not name: continue
        c = cat(t)
        alias = " ".join(x for x in {t.get(k, "") for k in ("name", "name:kk", "name:en", "name:ru", "alt_name", "old_name", "short_name", "official_name", "brand")} if x and x != name)
        p = [name, c, round(la, 5), round(ln, 5), t.get("addr:street", ""), t.get("addr:housenumber", ""), t.get("phone", t.get("contact:phone", "")), t.get("opening_hours", ""), alias]
        k = (name.lower(), round(la, 3), round(ln, 3))
        if k not in pois or (len(pois[k]) < 9 and alias): pois[k] = p
    els = q('nwr["addr:housenumber"]["addr:street"]{b}')
    for e in els:
        t = e.get("tags", {}); la, ln = ll(e)
        if la is None: continue
        a = [t["addr:street"], t["addr:housenumber"], round(la, 5), round(ln, 5)]
        addr.setdefault((a[0].lower(), str(a[1]).lower(), round(la, 4), round(ln, 4)), a)
    out = {"pois": list(pois.values()), "addr": list(addr.values()), "cams": old.get("cams", []), "license": "© OpenStreetMap contributors, ODbL", "built": time.strftime("%Y-%m-%d")}
    with gzip.open(out_path, "wt", encoding="utf-8") as f: json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("мест: %d → %d, адресов: %d → %d, ЖК: %d" % (n0p, len(pois), n0a, len(addr), sum(1 for p in pois.values() if p[1] == "ЖК")))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "-" else None, sys.argv[2] if len(sys.argv) > 2 else "astana-places.json.gz")
