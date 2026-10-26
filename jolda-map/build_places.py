# База адресов и мест «Жолда» (Астана и пригороды) из свежего OpenStreetMap.
# Дополняет старую базу: всё, что было, остаётся; новое из OSM — добавляется.
import gzip, json, sys, time, re, math

BBOX = (50.20, 70.00, 52.05, 72.90)  # юг, запад, север, восток — Астана и 100 км вокруг (как карта)
_OLD_MIRRORS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]

def load_export(path):
    # строки GeoJSON от «osmium export»: берём теги и центр объекта
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lstrip("\x1e")
            if not line: continue
            try: ft = json.loads(line)
            except Exception: continue
            g = ft.get("geometry") or {}; c = g.get("coordinates")
            if not c: continue
            t = g.get("type")
            if t == "Point": pts = [c]
            elif t == "LineString": pts = c
            elif t == "Polygon": pts = c[0]
            elif t == "MultiPolygon": pts = c[0][0]
            else: continue
            lon = sum(p[0] for p in pts) / len(pts); lat = sum(p[1] for p in pts) / len(pts)
            out.append({"lat": lat, "lon": lon, "tags": ft.get("properties") or {}})
    return out

def ll(e):
    if "lat" in e: return e["lat"], e["lon"]
    c = e.get("center") or {}
    return c.get("lat"), c.get("lon")

CAT = [
    (lambda t: t.get("highway") == "bus_stop" or (t.get("public_transport") in ("platform", "stop_position") and t.get("bus") == "yes"), "Остановка"),
    (lambda t: t.get("highway") in ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street", "service", "pedestrian", "road", "track", "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link") and not t.get("amenity") and not t.get("shop"), "Улица"),
    (lambda t: t.get("place") in ("city", "town"), "Город"), (lambda t: t.get("place") in ("village", "hamlet", "isolated_dwelling", "suburb"), "Посёлок"),
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
    (lambda t: t.get("amenity") in ("childcare",), "Детсад"), (lambda t: t.get("amenity") in ("library",), "Библиотека"),
    (lambda t: t.get("amenity") in ("townhall", "courthouse") or t.get("office") == "government", "Госучреждение"),
    (lambda t: t.get("building") in ("kindergarten",), "Детсад"), (lambda t: t.get("building") in ("school",), "Школа"),
    (lambda t: t.get("building") in ("hospital",), "Больница"), (lambda t: t.get("building") in ("retail", "supermarket", "kiosk"), "Магазин"),
    (lambda t: t.get("building") in ("mosque", "church", "cathedral", "religious"), "Храм/мечеть"), (lambda t: t.get("building") in ("university", "college"), "Университет"),
    (lambda t: t.get("amenity") or t.get("leisure") or t.get("tourism") or t.get("craft") or t.get("building"), "Здание"),
]
def cat(t):
    for f, c in CAT:
        try:
            if f(t): return c
        except Exception: pass
    return "Здание"

EXPORT = "astana.geojsonseq"

# --- категория по названию: для «Здание»/«Офис», у которых в OSM нет понятного тега ---
NAME_CAT = [
    (r"^(улица|ул\.|проспект|пр\.|переулок|пер\.|шоссе|трасса|бульвар|тупик|проезд)\b|\b(улица|көшесі|проспект|даңғылы|переулок|тұйығы|шоссе|трасса|бульвар|тас жолы)$", "Улица"),
    (r"детск\w* сад|балабақша|бөбекжай|ясли|д/с\b|mini.?центр|миницентр|kindergarten", "Детсад"),
    (r"школа|мектеп|гимназия|лицей|school", "Школа"), (r"колледж|college", "Колледж"), (r"университет|институт|академия|university", "Университет"),
    (r"больница|госпиталь|аурухана|перинатальн|роддом", "Больница"), (r"поликлиника|клиника|медцентр|медицинск|емхана|clinic|лаборатори|invitro|олимп\b", "Клиника"),
    (r"стоматолог|дентал|dental|тіс", "Стоматология"), (r"аптека|дәріхана|pharm", "Аптека"),
    (r"супермаркет|минимаркет|маркет|магазин|дүкен|small|magnum|галмарт|anvar|market|продукты", "Магазин"),
    (r"кофейня|coffee|кафе|cafe|café|кофе", "Кафе"), (r"ресторан|restaurant|асхана|столовая", "Ресторан"),
    (r"пицц|pizza|бургер|burger|kfc|донер|шаурм|doner|фастфуд", "Фастфуд"), (r"\bбар\b|\bpub\b|lounge|лаунж|караоке", "Бар"),
    (r"мечеть|мешіт|церковь|собор|храм", "Храм/мечеть"), (r"банк|bank", "Банк"), (r"\bазс\b|helios|гелиос|sinooil|qazaqoil|petro|компас|газпром|лукойл|\bkmg\b", "АЗС"),
    (r"отель|гостиниц|hotel|hostel|хостел|мотель|resort", "Отель"), (r"бизнес.?центр|\bбц\b|business center", "Бизнес-центр"),
    (r"трц|тц |торгов\w* центр|mall|молл|сауда орталығы", "ТРЦ"), (r"автомойка|car ?wash|мойка", "Автомойка"), (r"\bсто\b|автосервис|шиномонтаж|вулканизац", "СТО"),
    (r"акимат|әкімдік|министерств|департамент|управлени|суд\b|цон|хаб|прокуратур", "Госучреждение"), (r"парк\b|сквер|park\b", "Парк"),
    (r"фитнес|fitness|спорт|бассейн|gym|стадион|арена", "Спорткомплекс"), (r"салон красоты|барбершоп|barber|парикмахер|beauty|nail", "Салон красоты"),
]
NAME_CAT = [(re.compile(r, re.I), c) for r, c in NAME_CAT]
# явное слово в начале названия важнее категории из базы: «Детский сад …» — это садик, даже если в базе «Университет»
STRONG = [(re.compile(r, re.I), c) for r, c in [
    (r"^(я?сли.?сад|детск\w* сад|д/с|садик|балабақша|бөбекжай|мини.?центр|kindergarten)", "Детсад"),
    (r"^(школа|сш|сош|мектеп|школа.?гимназия|гимназия|лицей)\b|^№?\s?\d+\s?(мектеп|школа)", "Школа"),
    (r"^(аптека|дәріхана)", "Аптека"), (r"^(стоматолог|дентал)", "Стоматология"), (r"^(больница|детская .*больница|городская больница|аурухана|госпиталь)", "Больница"),
    (r"^(поликлиника|емхана)", "Клиника"), (r"^(магазин|супермаркет|минимаркет|дүкен)\b", "Магазин"), (r"^(кафе|кофейня)\b", "Кафе"), (r"^(ресторан|мейрамхана)\b", "Ресторан"),
    (r"^(мечеть|мешіт)", "Храм/мечеть"), (r"^(азс)\b", "АЗС"), (r"^(трц|тц|торгов\w* центр)\b", "ТРЦ"), (r"^(бизнес.?центр|бц)\b", "Бизнес-центр")]]
def cat_by_name(name, cur):
    if cur in ("Вокзал", "Здание", "Офис", "Госучреждение") and re.search(r"airport|аэропорт|әуежай|терминал t[12]", name, re.I) and not re.search(r"hotel|отель|кафе|cafe|bar|бар|парковк|parking|такси|taxi", name, re.I): return "Аэропорт"
    if cur not in ("Улица", "Посёлок", "Город", "Район", "Остановка"):
        for rx, c in STRONG:
            if rx.search(name.strip(" «»\"'")): return c
    if cur not in ("Здание", "Офис", "Магазин"): return cur
    for rx, c in NAME_CAT:
        if rx.search(name):
            if cur == "Магазин" and c not in ("Детсад", "Аптека", "ТРЦ", "Кафе", "Фастфуд"): continue
            return c
    return cur

def nkey(s):
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"[«»\"'`.,()\-–—/№#&!]", " ", s)
    s = re.sub(r"\b(тоо|ип|ао|llp|ltd)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# --- открытые базы организаций: Overture Maps (Meta/Microsoft/…) и Foursquare OS Places ---
OV_MAP = [
    (r"^airport|airport_terminal|international_airport", "Аэропорт"),
    (r"preschool|day_care|child_care|kindergarten|nursery_school", "Детсад"), (r"housing_development|apartment_or_condo|residential_building|residential_complex", "ЖК"), (r"military|polling|home_private|assisted_living|plane|airport_gate|airport_lounge|airport_service|airport_tram|baggage|road$|intersection|bridge|tunnel|bus_line|^train$|moving_target", "-"), (r"language_school|driving_school|specialty_school|tutoring|educational_service|art_school|music_school|dance_studio|training", "Курсы"),
    (r"elementary_school|high_school|middle_school|^school|private_school|public_school|primary_and_secondary", "Школа"), (r"college_university|university", "Университет"),
    (r"fast_food|burger|pizza|sandwich|doner|kebab|hot_dog|food_truck|chicken_wings|fried_chicken", "Фастфуд"),
    (r"coffee|cafe|tea_room|bakery|dessert|ice_cream|cake|pastry|juice|bubble_tea", "Кафе"),
    (r"restaurant|eatery|steakhouse|buffet|diner|food_court|canteen|cafeteria", "Ресторан"),
    (r"lounge|hookah|pub|^bar|_bar|beer|wine_bar|cocktail", "Бар"), (r"karaoke|night_club|nightclub|music_venue|bowling|arcade|amusement|escape|trampoline|water_park|cinema|movie|entertainment|event_venue|banquet", "Развлечения"),
    (r"hotel|lodging|hostel|motel|guest_house|resort|inn$|apartment_rental|holiday_rental", "Отель"),
    (r"hospital|maternity", "Больница"), (r"dent|orthodont", "Стоматология"), (r"pharmacy|drugstore", "Аптека"),
    (r"clinic|doctor|medical|health_care|outpatient|laboratory|diagnostic|physical_therap|optometr|veterin|ophthalm|pediatr|gynec|urgent_care", "Клиника"),
    (r"beauty|barber|hair|nail|spa$|^spa|massage|cosmetic|eyelash|tattoo|waxing|skin_care|makeup", "Салон красоты"),
    (r"gym|fitness|yoga|pilates|sport|martial|boxing|swimming|stadium|arena|ice_skating|tennis|football|golf", "Спорткомплекс"),
    (r"gas_station|fuel", "АЗС"), (r"car_wash|auto_detailing", "Автомойка"), (r"automotive_repair|auto_parts|tire|auto_body|oil_change|automotive_service|car_repair|auto_glass|auto_electric", "СТО"),
    (r"auto_dealer|car_dealer|used_car", "Автосалон"), (r"^atm$", "Банкомат"), (r"bank|credit_union|currency_exchange|microfinance|pawn", "Банк"),
    (r"shopping_mall|shopping_center|department_store", "ТРЦ"), (r"supermarket|grocery|convenience|food_and_beverage_store|liquor|butcher|meat|produce|discount_store", "Магазин"),
    (r"store|shop|shopping|market|boutique|florist|flowers|optician|bookstore", "Магазин"),
    (r"mosque|church|religious|place_of_worship|temple|cathedral|synagogue", "Храм/мечеть"), (r"museum|gallery", "Музей"), (r"theat", "Театр"),
    (r"^park$|playground|botanical|zoo|garden$|dog_park", "Парк"), (r"government|embassy|consulate|police|post_office|courthouse|town_hall|public_service|social_service|community_center|library", "Госучреждение"),
    (r"airport|airfield|aerodrome", "Аэропорт"), (r"train_station|railway|bus_station", "Вокзал"), (r"car_rental|parking", "Парковка"),
]
OV_MAP = [(re.compile(r), c) for r, c in OV_MAP]
OV_OFFICE = re.compile(r"professional|real_estate|b2b|marketing|advertis|internet|software|it_service|consult|financial_advis|insurance|lawyer|legal|accountant|travel|tour_operator|agency|media|construction|contractor|home_developer|interior_design|cleaning|event_planning|photograph|printing|logistic|freight|recruit|employment|wedding|planning")
BAD_NAME = re.compile(r"https?:|www\.|\.(kz|ru|com|net|org)\b|@|^\W*$|^[\d\s+()-]{6,}$|instagram|whatsapp|доставка по|онлайн|online|оптом|под заказ|в наличии|скидк|акци|бесплатн|\bв астане\b|\bв нур-султане\b|nur-sultan|в казахстане", re.I)

def ov_cat(*parts):
    s = " ".join(p for p in parts if p)
    if not s: return None
    toks = [p for p in parts if p]
    for t in toks:
        for rx, c in OV_MAP:
            if rx.search(t): return c
    if OV_OFFICE.search(s): return "Офис"
    return None

KZT = str.maketrans("әғқңөұүһіё", "агкноууhие")
ST_STOP = set("улица ул көшесі кошеси кошесі проспект пр пр-т даңғылы дангылы данғылы переулок пер тұйығы шоссе бульвар г город астана нур султан нур-султан казахстан қазақстан kazakhstan astana дом д здание блок кв офис этаж тц трц бц мкр микрорайон шағын ауданы ауданы район р-н жк и им имени street st avenue ave".split())
def street_core(st):
    w = [x for x in re.findall(r"[a-zа-я]+", (st or "").lower().translate(KZT)) if x not in ST_STOP and len(x) >= 3]
    return w
def build_addr_index(addr):
    idx = {}
    for a in addr.values():
        h = re.match(r"\s*(\d+[а-яa-z]?(?:/\d+)?)", str(a[1]).lower())
        if not h: continue
        for w in street_core(a[0]):
            idx.setdefault((w, h.group(1)), []).append((a[2], a[3]))
    return idx
def geocode(text, idx, near=None):
    t = (text or "").lower().translate(KZT)
    m = re.findall(r"(?<![\d/])(\d{1,4}[а-яa-z]?(?:/\d{1,3})?)(?![\d])", t)
    if not m: return None
    words = street_core(t)
    for h in m[:2]:
        for w in words:
            c = idx.get((w, h))
            if c:
                if near is None: return c[0]
                best = min(c, key=lambda q: (q[0] - near[0]) ** 2 + ((q[1] - near[1]) * 0.62) ** 2)
                if math.hypot((best[0] - near[0]) * 111, (best[1] - near[1]) * 69) <= near[2]: return best
    return None

STABLE = {"ЖК", "Школа", "Детсад", "Университет", "Колледж", "Больница", "Клиника", "Храм/мечеть", "ТРЦ", "Парк", "Музей", "Театр", "Госучреждение", "Вокзал", "Спорткомплекс", "АЗС", "Отель"}
def merge_extra(pois, addr=None):
    aidx = build_addr_index(addr or {})
    print("индекс адресов:", len(aidx), flush=True)
    import os, math
    from collections import Counter
    # быстрый поиск дублей: сетка ~250 м
    grid = {}
    def gk(la, ln): return (int(la * 400), int(ln * 250))
    def add_grid(p):
        grid.setdefault(gk(p[2], p[3]), []).append(p)
    for p in pois.values(): add_grid(p)
    def dup(name, la, ln, rad=0.25):
        k = nkey(name)
        if len(k) < 2: return True
        a, b = gk(la, ln)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for q in grid.get((a + i, b + j), []):
                    d = math.hypot((q[2] - la) * 111, (q[3] - ln) * 69)
                    if d > rad: continue
                    qk = nkey(q[0]); qa = nkey(q[8]) if len(q) > 8 else ""
                    if qk == k or (len(k) >= 4 and (k in qk or qk in k) and min(len(k), len(qk)) >= 4) or (qa and len(k) >= 4 and k in qa): return True
        return False
    def load(fn):
        if not os.path.exists(fn): return []
        op = gzip.open if fn.endswith(".gz") else open
        return [json.loads(l) for l in op(fn, "rt", encoding="utf-8") if l.strip()]
    added = Counter(); skipped = Counter(); geo = Counter()
    # Overture
    ov = load("overture.ndjson") or load("overture.ndjson.gz")
    pin = Counter((round(x["lat"], 4), round(x["lng"], 4)) for x in ov)
    for x in ov:
        name = (x.get("name") or "").strip(); conf = x.get("conf") or 0
        hier = x.get("alt") or []
        c = ov_cat(x.get("cat"), x.get("basic"), *(hier if isinstance(hier, list) else []))
        if not name or len(name) > 60 or BAD_NAME.search(name): skipped["имя"] += 1; continue
        shared = pin[(round(x["lat"], 4), round(x["lng"], 4))] >= 4
        g = geocode(x.get("addr"), aidx, (x["lat"], x["lng"], 25 if shared else 6))
        if g: x["lat"], x["lng"] = g; geo["по адресу"] += 1
        elif pin[(round(x["lat"], 4), round(x["lng"], 4))] >= 4 and conf < 0.9: skipped["общая точка"] += 1; continue
        if c is None or c == "-": skipped["без категории"] += 1; continue
        if c == "Офис" and (conf < 0.75 or not g): skipped["офис"] += 1; continue
        if conf < (0.3 if g else 0.45 if x.get("addr") else 0.6): skipped["низкое доверие"] += 1; continue
        if dup(name, x["lat"], x["lng"]): skipped["дубль"] += 1; continue
        addr = (x.get("addr") or "").strip()
        nm = x.get("names") or {}
        alias = " ".join(v for v in ((nm.get("common") or {}).values() if isinstance(nm.get("common"), dict) else []) if v and v != name)
        p = [name, c, round(x["lat"], 5), round(x["lng"], 5), addr, "", x.get("phone") or "", "", alias]
        pois[(name.lower(), round(p[2], 3), round(p[3], 3))] = p; add_grid(p); added["overture " + c] += 1
    # Foursquare
    fs = load("fsq.ndjson") or load("fsq.ndjson.gz")
    pin = Counter((round(x["lat"], 4), round(x["lng"], 4)) for x in fs)
    for x in fs:
        name = (x.get("name") or "").strip()
        if x.get("closed") and x["closed"] not in ("", "None"): skipped["fsq закрыто"] += 1; continue
        labs = x.get("labels") or []
        c = None
        for lab in labs:
            parts = [re.sub(r"[^a-z]+", "_", t.strip().lower()).strip("_") for t in lab.split(">")]
            c = ov_cat(*reversed(parts[1:] or parts))
            if c: break
        if not name or len(name) > 60 or BAD_NAME.search(name): skipped["fsq имя"] += 1; continue
        shared = pin[(round(x["lat"], 4), round(x["lng"], 4))] >= 4
        g = geocode(x.get("addr"), aidx, (x["lat"], x["lng"], 25 if shared else 6))
        if g: x["lat"], x["lng"] = g; geo["fsq по адресу"] += 1
        elif pin[(round(x["lat"], 4), round(x["lng"], 4))] >= 4: skipped["fsq общая точка"] += 1; continue
        if c is None or c in ("Офис", "-"): skipped["fsq без категории/офис"] += 1; continue
        # школы, садики, больницы, мечети, ТРЦ не закрываются годами — берём и старые записи; кафе и магазины — только свежие
        if (x.get("refreshed") or "")[:4] < "2020" and c not in STABLE: skipped["fsq устарело"] += 1; continue
        if dup(name, x["lat"], x["lng"]): skipped["fsq дубль"] += 1; continue
        p = [name, c, round(x["lat"], 5), round(x["lng"], 5), (x.get("addr") or "").strip(), "", x.get("phone") or "", "", ""]
        pois[(name.lower(), round(p[2], 3), round(p[3], 3))] = p; add_grid(p); added["fsq " + c] += 1
    print("добавлено из открытых баз:", sum(added.values()), dict(added.most_common()), flush=True)
    print("пропущено:", dict(skipped), "координаты уточнены:", dict(geo), flush=True)

def main(old_path, out_path):
    old = json.load(gzip.open(old_path)) if old_path else {"pois": [], "addr": [], "cams": []}
    pois = {(p[0].lower(), round(p[2], 3), round(p[3], 3)): p for p in old["pois"]}
    addr = {(a[0].lower(), str(a[1]).lower(), round(a[2], 4), round(a[3], 4)): a for a in old["addr"]}
    n0p, n0a = len(pois), len(addr)
    allels = load_export(EXPORT)
    print("объектов в выгрузке:", len(allels), flush=True)
    els = [e for e in allels if e["tags"].get("name")]
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
    els = [e for e in allels if e["tags"].get("addr:housenumber") and e["tags"].get("addr:street")]
    for e in els:
        t = e.get("tags", {}); la, ln = ll(e)
        if la is None: continue
        a = [t["addr:street"], t["addr:housenumber"], round(la, 5), round(ln, 5)]
        addr.setdefault((a[0].lower(), str(a[1]).lower(), round(la, 4), round(ln, 4)), a)
    # места, которых нет в OpenStreetMap, — добавляем вручную (jolda-map/extra_places.json)
    try:
        import os
        for p in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "extra_places.json"), encoding="utf-8")):
            pois[(p[0].lower(), round(p[2], 3), round(p[3], 3))] = p
    except Exception as e: print("extra:", e)
    try: merge_extra(pois, addr)
    except Exception as e: print("открытые базы:", e, flush=True)
    # категории по названию (старые записи «Здание» без тегов)
    for p in pois.values():
        p[1] = cat_by_name(p[0], p[1])
        if len(p) > 4 and re.search(r"https?:|www\.|goo\.gl", str(p[4])): p[4] = ""
    # улицы в OSM разбиты на десятки кусков — оставляем по одной точке на каждые ~1,5 км улицы
    keep, seen = {}, {}
    for k, p in pois.items():
        if p[1] != "Улица": keep[k] = p; continue
        lst = seen.setdefault(nkey(p[0]), [])
        if any(math.hypot((q[2] - p[2]) * 111, (q[3] - p[3]) * 69) < 1.5 for q in lst): continue
        lst.append(p); keep[k] = p
    print("улицы: %d кусков → %d" % (sum(1 for p in pois.values() if p[1] == "Улица"), sum(1 for p in keep.values() if p[1] == "Улица")), flush=True)
    pois = keep
    out = {"pois": list(pois.values()), "addr": list(addr.values()), "cams": old.get("cams", []), "license": "© OpenStreetMap contributors (ODbL); Overture Maps Foundation (CDLA-Permissive-2.0); Foursquare OS Places (Apache-2.0)", "built": time.strftime("%Y-%m-%d")}
    with gzip.open(out_path, "wt", encoding="utf-8") as f: json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("мест: %d → %d, адресов: %d → %d, ЖК: %d" % (n0p, len(pois), n0a, len(addr), sum(1 for p in pois.values() if p[1] == "ЖК")))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "-" else None, sys.argv[2] if len(sys.argv) > 2 else "astana-places.json.gz")
