"""Раскладывает кинозал New TV по категориям (жанры фильмов, мультфильмы по годам).

Использование: python categorize.py <вход.m3u> <выход.m3u> <кэш.json>

Жанр и год берутся из Википедии/Wikidata по названию и году фильма.
Найденное запоминается в кэше (film_genres.json), поэтому каждый раз
ищутся только новые фильмы. Если сеть недоступна или найдено слишком мало,
плейлист остаётся с прежними категориями — кинозал не ломается.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

UA = "NewTV-playlist-bot/1.0 (https://github.com/aliba210890-del/newtv-releases)"
SPARQL = "https://query.wikidata.org/sparql"
API = "https://www.wikidata.org/w/api.php"
MISS_RETRY_DAYS = 30

FILM_GROUPS = ("Фильмы", "Films_4k", "Новинки кино")
NEW_GROUP = "Новинки кино"
UHD_GROUP = "Films_4k"
CARTOON_GROUP = "Наши Мультфильмы"
# категории, которые совсем убираем из кинозала (решение Алибека, окт. 2026)
REMOVE_GROUPS = {"Наши Мультфильмы", "ТОМ И ДЖЕРРИ"}

# жанр Wikidata (английское название) → категория. Порядок = приоритет, если жанров несколько.
GENRES = [
    ("Мультфильмы", ("animat", "anime", "cartoon")),
    ("Ужасы", ("horror", "slasher", "zombie")),
    ("Фантастика", ("science fiction", "sci-fi", "superhero", "cyberpunk", "space", "dystopia", "post-apocalyptic")),
    ("Фэнтези", ("fantasy", "sword and sorcery")),
    ("Боевики", ("action", "martial arts", "spy", "heist", "disaster")),
    ("Комедии", ("comedy", "comedic", "parody", "satir")),
    ("Триллеры", ("thriller", "suspense")),
    ("Детективы и криминал", ("crime", "detective", "mystery", "gangster", "noir", "police")),
    ("Военные", ("war film", "war drama", "military", "world war")),
    ("Мелодрамы", ("romance", "romantic", "melodrama", "love")),
    ("Приключения", ("adventure", "swashbuckler", "survival")),
    ("Семейные", ("family", "children", "teen", "coming-of-age")),
    ("Исторические", ("histor", "biograph", "biopic", "period", "epic")),
    ("Вестерны", ("western",)),
    ("Мюзиклы", ("musical", "music", "dance")),
    ("Спорт", ("sport",)),
    ("Документальные", ("documentary",)),
    ("Драмы", ("drama",)),
]
GENRE_ORDER = ["Боевики", "Комедии", "Фантастика", "Фэнтези", "Ужасы", "Триллеры", "Детективы и криминал",
               "Драмы", "Мелодрамы", "Приключения", "Семейные", "Мультфильмы", "Военные", "Исторические",
               "Вестерны", "Мюзиклы", "Спорт", "Документальные", "Другие фильмы"]
MAX_GENRES = 2  # фильм может попасть в две категории (например, «Комедии» и «Мелодрамы»)

DECADES = [(0, 1959, "Мультфильмы 1930–50-х"), (1960, 1969, "Мультфильмы 1960-х"), (1970, 1979, "Мультфильмы 1970-х"),
           (1980, 1989, "Мультфильмы 1980-х"), (1990, 2009, "Мультфильмы 1990–2000-х"), (2010, 9999, "Новые мультфильмы")]
CARTOON_SERIES = "Мультсериалы"
CARTOON_OTHER = "Мультфильмы: разное"


def http_json(url, data=None, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001 — сеть: повторяем, потом сдаёмся
            if k == tries - 1:
                print("  сеть:", type(e).__name__, str(e)[:120])
                return None
            time.sleep(3 * (k + 1))


# ---------- разбор плейлиста ----------

def parse(path):
    with open(path, encoding="utf-8-sig") as f:
        lines = [l.rstrip("\r\n") for l in f]
    header = next((l for l in lines if l.startswith("#EXTM3U")), "#EXTM3U")
    items, i = [], 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF"):
            block, j = [lines[i]], i + 1
            while j < len(lines) and (not lines[j].strip() or (lines[j].startswith("#") and not lines[j].startswith("#EXTINF"))):
                if lines[j].strip():
                    block.append(lines[j])
                j += 1
            if j < len(lines) and not lines[j].startswith("#"):
                block.append(lines[j].strip())
                j += 1
                g = re.search(r'group-title="([^"]*)"', block[0])
                items.append({"block": block, "group": g.group(1) if g else "", "name": block[0].rsplit(",", 1)[-1].strip()})
            i = j
        else:
            i += 1
    return header, items


def with_group(block, group):
    first = block[0]
    if 'group-title="' in first:
        first = re.sub(r'group-title="[^"]*"', 'group-title="' + group.replace('"', "'") + '"', first, count=1)
    else:
        first = first.replace("#EXTINF:-1", '#EXTINF:-1 group-title="' + group + '"', 1)
    return [first] + block[1:]


def split_title(name):
    m = re.match(r"^(.*?)\s*\((\d{4})\)\s*$", name)
    return (m.group(1).strip(), int(m.group(2))) if m else (name.strip(), None)


def variants(title):
    t = title.strip().strip('"«»')
    out = {t, t.replace("ё", "е").replace("Ё", "Е")}
    out.add(re.sub(r'[«»"]', "", t))
    out.add(t.replace(" - ", " — ").replace(" – ", " — "))
    return [v for v in out if v]


def key_of(title, year):
    return title.lower().replace("ё", "е") + "|" + (str(year) if year else "")


# ---------- поиск в Wikidata ----------

def sparql_batch(pairs):
    """pairs: [(key, title, year)] → {key: {"y": year, "g": [жанры en], "t": [типы en]}}"""
    vals, back = [], {}
    for key, title, _ in pairs:
        for v in variants(title):
            lit = json.dumps(v, ensure_ascii=False) + "@ru"
            vals.append(lit)
            back.setdefault(v, []).append(key)
    q = """SELECT ?lbl ?item ?year ?g ?t WHERE {
  VALUES ?lbl { %s }
  ?item rdfs:label|skos:altLabel ?lbl .
  OPTIONAL { ?item wdt:P577 ?d . BIND(YEAR(?d) AS ?year) }
  OPTIONAL { ?item wdt:P136 ?gi . ?gi rdfs:label ?g . FILTER(LANG(?g) = "en") }
  OPTIONAL { ?item wdt:P31 ?ti . ?ti rdfs:label ?t . FILTER(LANG(?t) = "en") }
}""" % " ".join(vals)
    res = http_json(SPARQL, urllib.parse.urlencode({"query": q, "format": "json"}).encode())
    if res is None:
        return None
    items = {}
    for b in res["results"]["bindings"]:
        lbl, item = b["lbl"]["value"], b["item"]["value"]
        it = items.setdefault((lbl, item), {"years": set(), "g": set(), "t": set()})
        if "year" in b:
            it["years"].add(int(b["year"]["value"]))
        if "g" in b:
            it["g"].add(b["g"]["value"].lower())
        if "t" in b:
            it["t"].add(b["t"]["value"].lower())
    found = {}
    for (lbl, _), it in items.items():
        for key in back.get(lbl, []):
            pick(found, key, it, dict((p[0], p[2]) for p in pairs)[key])
    return found


def is_screen_work(it):
    t = " ".join(it["t"])
    return bool(it["g"]) or any(w in t for w in ("film", "animat", "cartoon", "movie", "anime"))


def pick(found, key, it, year):
    if not is_screen_work(it):
        return
    if year:
        if not any(abs(y - year) <= 1 for y in it["years"]):
            return
    elif not any("animat" in s or "cartoon" in s for s in it["t"] | it["g"]):
        return  # без года берём только мультфильмы — иначе легко перепутать с книгой или песней
    score = len(it["g"]) + (5 if year and year in it["years"] else 0)
    old = found.get(key)
    if old is None or score > old["_s"]:
        found[key] = {"y": min(it["years"]) if it["years"] else None, "g": sorted(it["g"]), "t": sorted(it["t"]), "_s": score}


def search_one(title, year):
    """Запасной поиск по Wikidata (если точное название не совпало)."""
    r = http_json(API + "?" + urllib.parse.urlencode({"action": "wbsearchentities", "search": title, "language": "ru",
                                                     "uselang": "ru", "type": "item", "limit": 7, "format": "json"}))
    if not r or not r.get("search"):
        return None
    ids = [s["id"] for s in r["search"]]
    ents = http_json(API + "?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(ids),
                                                        "props": "claims", "format": "json"}))
    if not ents:
        return None
    best = None
    for qid in ids:
        cl = ents.get("entities", {}).get(qid, {}).get("claims", {})
        years = set()
        for c in cl.get("P577", []):
            v = c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("time", "")
            m = re.match(r"[+-](\d{4})", v)
            if m:
                years.add(int(m.group(1)))
        if year and not any(abs(y - year) <= 1 for y in years):
            continue
        gids = [c["mainsnak"]["datavalue"]["value"]["id"] for c in cl.get("P136", []) if c.get("mainsnak", {}).get("datavalue")]
        tids = [c["mainsnak"]["datavalue"]["value"]["id"] for c in cl.get("P31", []) if c.get("mainsnak", {}).get("datavalue")]
        if gids or tids:
            best = (years, gids, tids)
            break
    if not best:
        return None
    labels = http_json(API + "?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join((best[1] + best[2])[:50]),
                                                          "props": "labels", "languages": "en", "format": "json"})) or {}
    lab = lambda q: labels.get("entities", {}).get(q, {}).get("labels", {}).get("en", {}).get("value", "").lower()
    it = {"years": best[0], "g": {lab(q) for q in best[1]} - {""}, "t": {lab(q) for q in best[2]} - {""}}
    if not is_screen_work(it):
        return None
    if not year and not any("animat" in s or "cartoon" in s for s in it["t"] | it["g"]):
        return None
    return {"y": min(it["years"]) if it["years"] else None, "g": sorted(it["g"]), "t": sorted(it["t"])}


def lookup(todo, cache):
    """todo: {key: (title, year)}. Обновляет кэш на месте. Возвращает False, если сеть недоступна."""
    keys = list(todo)
    print("ищу в Wikidata:", len(keys))
    ok_batches = 0
    for n in range(0, len(keys), 25):
        part = [(k, todo[k][0], todo[k][1]) for k in keys[n:n + 25]]
        found = sparql_batch(part)
        if found is None:
            if ok_batches == 0 and n >= 50:
                return False
            continue
        ok_batches += 1
        for k, _, _ in part:
            if k in found:
                found[k].pop("_s", None)
                cache[k] = found[k]
        time.sleep(1)
    if ok_batches == 0:
        return False
    misses = [k for k in keys if k not in cache or cache[k].get("miss")]
    print("запасной поиск:", len(misses))
    for k in misses:
        title, year = todo[k]
        r = search_one(title, year)
        cache[k] = r if r else {"miss": int(time.time())}
        time.sleep(0.3)
    return True


# ---------- категории ----------

def film_genres(info):
    words = info.get("g", []) + [t for t in info.get("t", []) if "animat" in t or "documentary" in t]
    out = []
    for cat, keys in GENRES:
        if any(any(k in w for k in keys) for w in words) and cat not in out:
            out.append(cat)
    # «Драмы» добавляем, только если других жанров нет — иначе почти всё было бы драмой
    if len(out) > 1 and "Драмы" in out:
        out.remove("Драмы")
    return out[:MAX_GENRES]


def cartoon_group(name, info):
    if re.search(r"\(\s*ч\.?\s*\d+\s*\)|выпуск\s*№?\s*\d|\d+\s*сери[яи]|^\d+\)?$", name, re.I):
        return CARTOON_SERIES
    y = info.get("y") if info and not info.get("miss") else None
    if not y:
        return CARTOON_OTHER
    for a, b, g in DECADES:
        if a <= y <= b:
            return g
    return CARTOON_OTHER


TMDB_IMG = "https://image.tmdb.org/t/p/"


def enrich(block, meta):
    """Подставить описание (Википедия) и, если есть, постер и рейтинг в строку #EXTINF."""
    if not meta or meta.get("miss"):
        return block
    first, name = block[0].rsplit(",", 1)
    attrs = ""
    if meta.get("poster"):
        first = re.sub(r'\s*tvg-logo="[^"]*"', "", first)
        attrs += ' tvg-logo="' + TMDB_IMG + "w342" + meta["poster"] + '" poster="' + TMDB_IMG + "w780" + meta["poster"] + '"'
    if meta.get("rating") and meta.get("votes", 0) >= 5:
        attrs += ' rating="' + str(meta["rating"]) + '"'
    plot = re.sub(r"\s+", " ", meta.get("plot") or "").replace('"', "\u201c").strip()
    if plot and meta.get("page"):
        plot += " (Источник: Википедия)"  # лицензия CC BY-SA требует указать источник
    if plot:
        attrs += ' description="' + plot + '"'
    return [first + attrs + "," + name] + block[1:]


def main(src, dst, cache_path, tmdb_path=None):
    header, items = parse(src)
    try:
        tmdb = json.load(open(tmdb_path, encoding="utf-8")) if tmdb_path else {}
    except (OSError, ValueError):
        tmdb = {}
    items = [it for it in items if it["group"] not in REMOVE_GROUPS]
    try:
        with open(cache_path, encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}

    now = int(time.time())
    todo = {}
    for it in items:
        if it["group"] in FILM_GROUPS or it["group"] == CARTOON_GROUP:
            title, year = split_title(it["name"])
            if it["group"] == CARTOON_GROUP and cartoon_group(it["name"], None) == CARTOON_SERIES:
                continue
            k = key_of(title, year)
            c = cache.get(k)
            if c is None or (c.get("miss") and now - c["miss"] > MISS_RETRY_DAYS * 86400):
                todo[k] = (title, year)
    if todo:
        lookup(todo, cache)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=0, sort_keys=True)

    films = [it for it in items if it["group"] in FILM_GROUPS]
    def cats_of(k):
        t = tmdb.get(k) or {}
        if t.get("genres"):  # TMDB точнее и знает новинки; Wikidata — запасной вариант
            g = [x for x in t["genres"] if x != "Драмы"] or t["genres"]
            return list(dict.fromkeys(g))[:MAX_GENRES]
        return film_genres(cache.get(k) or {})

    for it in films:  # постеры, описания, рейтинг
        it["block"] = enrich(it["block"], tmdb.get(key_of(*split_title(it["name"]))))

    known = sum(1 for it in films if cats_of(key_of(*split_title(it["name"]))))
    print(f"фильмов: {len(films)}, с жанром: {known}")
    if films and known < len(films) * 0.3:
        print("слишком мало жанров — оставляю прежние категории")
        out = [header]
        for it in items:
            out.extend(it["block"])
        with open(dst, "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
        return

    groups = {}  # категория → список блоков

    seen_in = {}  # без повторов внутри одной категории

    def put(g, block):
        # все мультфильмы — одной категорией «Мультфильмы» (по годам и сериалам не делим: есть поиск)
        if g.startswith("Мультфильм") or g.startswith("Мультсериал") or g == "Новые мультфильмы":
            g = "Мультфильмы"
        url = next((l for l in block if l and not l.startswith("#")), "")
        s = seen_in.setdefault(g, set())
        if url and url in s:
            return
        s.add(url)
        groups.setdefault(g, []).append(with_group(block, g))

    # 1) новинки — как были; 2) 4K — отдельной полкой; 3) все фильмы — по жанрам (без повторов: 4K-версия важнее)
    best = {}
    for it in films:
        title, year = split_title(it["name"])
        k = key_of(title, year)
        if it["group"] == NEW_GROUP:
            put(NEW_GROUP, it["block"])
        elif it["group"] == UHD_GROUP:
            put("Фильмы в 4K", it["block"])
        if k not in best or it["group"] == UHD_GROUP:
            best[k] = it
    for k, it in best.items():
        cats = cats_of(k)
        if not cats and it["group"] in (NEW_GROUP, UHD_GROUP):
            continue  # жанр не нашёлся (обычно совсем новые фильмы) — фильм и так есть в «Новинках» или «4K»
        for c in cats or ["Другие фильмы"]:
            put(c, it["block"])

    for it in items:
        if it["group"] == CARTOON_GROUP:
            title, year = split_title(it["name"])
            put(cartoon_group(it["name"], cache.get(key_of(title, year))), it["block"])
        elif it["group"] not in FILM_GROUPS:
            # документальные циклы («Как это сделано», «Разрушители легенд»…) — одной категорией «Документальные»,
            # в приложении каждый цикл — карточкой (x-series), выпуски внутри
            show = re.sub(r"\s*\(\d{4}\)\s*$", "", it["group"]).replace('"', "'")
            b = list(it["block"])
            if 'x-series="' not in b[0]:
                b[0] = b[0].replace("#EXTINF:-1", '#EXTINF:-1 x-series="' + show + '"', 1)
            put("Документальные", b)

    order = [NEW_GROUP, "Фильмы в 4K"] + GENRE_ORDER + [g for _, _, g in DECADES] + [CARTOON_SERIES, CARTOON_OTHER]
    rest = [g for g in groups if g not in order]
    out = [header]
    for g in order + rest:
        for block in groups.get(g, []):
            out.extend(block)
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print("категории:", ", ".join(f"{g} {len(groups[g])}" for g in order + rest if g in groups))


if __name__ == "__main__":
    main(*sys.argv[1:5])
