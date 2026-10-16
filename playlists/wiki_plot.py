"""Описания фильмов кинозала из русской Википедии (бесплатно, лицензия CC BY-SA — с указанием источника).

Использование: python wiki_plot.py <плейлист.m3u> <кэш.json>
Результат — кэш {ключ фильма: {"plot": "...", "page": "Название статьи"}}; categorize.py
подставляет описание в плейлист. Каждый фильм ищется один раз, ненайденные — повторно через 14 дней.
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://ru.wikipedia.org/w/api.php"
UA = "NewTV-playlist-bot/1.0 (https://github.com/aliba210890-del/newtv-releases)"
MISS_RETRY_DAYS = 14
FILM_GROUPS = ("Фильмы", "Films_4k", "Новинки кино")
MAX_CHARS = 650
FILM_WORDS = ("фильм", "мультфильм", "кинофильм", "картина", "аниме", "мюзикл", "комедия", "драма", "триллер", "боевик",
              "мелодрама", "вестерн", "кинокомедия", "киноальманах", "телефильм")


def get(**params):
    params.update(format="json", formatversion="2")
    url = API + "?" + urllib.parse.urlencode(params)
    for k in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001 — сеть: повторяем, потом сдаёмся
            time.sleep(2 * (k + 1))
    return None


def norm(s):
    return re.sub(r"[^0-9a-zа-я]+", "", s.lower().replace("ё", "е"))


def split_title(name):
    m = re.match(r"^(.*?)\s*\((\d{4})\)\s*$", name)
    return (m.group(1).strip(), int(m.group(2))) if m else (name.strip(), None)


def key_of(title, year):
    return title.lower().replace("ё", "е") + "|" + (str(year) if year else "")


def clean(text):
    t = text.strip().replace("\u0301", "")  # знаки ударения
    # убрать иностранные названия и произношения в скобках: (англ. ...), (фр. ...)
    t = re.sub(r"\s*\((?:[^()]*?\b(?:англ|фр|нем|исп|итал|яп|кит|кор|лат|рус|тур|хинди|швед|норв|дат|польск)\.[^()]*)\)", "", t)
    t = re.sub(r"\s*\[\d+\]", "", t)
    t = re.sub(r"\s+", " ", t)
    if len(t) > MAX_CHARS:
        cut = t[:MAX_CHARS]
        end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        t = cut[:end + 1] if end > 200 else cut.rsplit(" ", 1)[0] + "…"
    return t


def good(page_title, extract, title, year):
    """Это действительно статья о нужном фильме?"""
    pt, ex = page_title.lower(), extract.lower()
    if norm(title) not in norm(page_title) and norm(title) not in norm(extract[:200]):
        return False
    if not any(w in pt or w in ex[:400] for w in FILM_WORDS):
        return False
    if "значения" in pt:  # страница-неоднозначность
        return False
    if year and not any(str(y) in page_title or str(y) in extract[:500] for y in (year, year - 1, year + 1)):
        return False
    return True


def find(title, year):
    queries = [f"{title} фильм {year}" if year else f"{title} фильм"]
    if year:
        queries.append(f"{title} {year}")
    for q in queries:
        r = get(action="query", list="search", srsearch=q, srlimit=6, srnamespace=0)
        hits = [h["title"] for h in ((r or {}).get("query") or {}).get("search", [])]
        if not hits:
            continue
        ex = get(action="query", prop="extracts", exintro=1, explaintext=1, exlimit=20, redirects=1, titles="|".join(hits))
        pages = {p["title"]: p.get("extract") or "" for p in ((ex or {}).get("query") or {}).get("pages", [])}
        for h in hits:  # по порядку релевантности поиска
            text = pages.get(h, "")
            if text and good(h, text, title, year):
                return {"plot": clean(text), "page": h}
    return None


SPARQL = "https://query.wikidata.org/sparql"
SEARCH_LIMIT = 150  # медленный запасной поиск — не больше стольких фильмов за запуск


def http_json(url, data=None):
    for k in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:  # noqa: BLE001
            time.sleep(3 * (k + 1))
    return None


def variants(title):
    t = title.strip().strip('"«»')
    return list({t, t.replace("ё", "е"), re.sub(r'[«»"]', "", t)})


def wikidata_pages(pairs):
    """pairs: [(key, title, year)] → {key: название статьи в русской Википедии} (одним запросом на 25 фильмов)."""
    vals, back, years = [], {}, {}
    for key, title, year in pairs:
        years[key] = year
        for v in variants(title):
            vals.append(json.dumps(v, ensure_ascii=False) + "@ru")
            back.setdefault(v, []).append(key)
    q = """SELECT ?lbl ?page ?year WHERE {
  VALUES ?lbl { %s }
  ?item rdfs:label|skos:altLabel ?lbl .
  ?art schema:about ?item ; schema:isPartOf <https://ru.wikipedia.org/> ; schema:name ?page .
  OPTIONAL { ?item wdt:P577 ?d . BIND(YEAR(?d) AS ?year) }
}""" % " ".join(vals)
    res = http_json(SPARQL, urllib.parse.urlencode({"query": q, "format": "json"}).encode())
    if res is None:
        return None
    cand = {}
    for b in res["results"]["bindings"]:
        for key in back.get(b["lbl"]["value"], []):
            y = int(b["year"]["value"]) if "year" in b else None
            want = years[key]
            ok = (y is not None and want and abs(y - want) <= 1) or (not want)
            if ok:
                cand.setdefault(key, set()).add(b["page"]["value"])
    return cand


def extracts(titles):
    out = {}
    titles = list(titles)
    for n in range(0, len(titles), 20):
        ex = get(action="query", prop="extracts", exintro=1, explaintext=1, exlimit=20, redirects=1, titles="|".join(titles[n:n + 20]))
        q = (ex or {}).get("query") or {}
        alias = {r["from"]: r["to"] for r in q.get("redirects", [])}
        pages = {p["title"]: p.get("extract") or "" for p in q.get("pages", [])}
        for t in titles[n:n + 20]:
            out[t] = pages.get(alias.get(t, t), "")
        time.sleep(0.2)
    return out


def main(src, cache_path):
    try:
        cache = json.load(open(cache_path, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    names = []
    for line in open(src, encoding="utf-8"):
        if line.startswith("#EXTINF"):
            g = re.search(r'group-title="([^"]*)"', line)
            if g and g.group(1) in FILM_GROUPS:
                names.append(line.rsplit(",", 1)[-1].strip())
    now = int(time.time())
    todo = {}
    for n in names:
        t, y = split_title(n)
        k = key_of(t, y)
        c = cache.get(k)
        if c is None or (c.get("miss") and now - c["miss"] > MISS_RETRY_DAYS * 86400):
            todo[k] = (t, y)
    print("Википедия: фильмов", len(set(names)), "ищу", len(todo))
    keys = list(todo)
    found = 0
    # 1) быстро: Wikidata даёт название статьи сразу для 25 фильмов, текст — по 20 статей за запрос
    left = []
    for n in range(0, len(keys), 25):
        part = [(k, todo[k][0], todo[k][1]) for k in keys[n:n + 25]]
        cand = wikidata_pages(part)
        if cand is None:
            left.extend(k for k, _, _ in part)
            continue
        titles = {t for ts in cand.values() for t in ts}
        texts = extracts(titles) if titles else {}
        for k, t, y in part:
            best = None
            for page in sorted(cand.get(k, ())):
                text = texts.get(page, "")
                if text and good(page, text, t, y):
                    best = {"plot": clean(text), "page": page}
                    break
            if best:
                cache[k] = best
                found += 1
            else:
                left.append(k)
        if n % 250 == 0:
            print(" …", n + len(part), "найдено", found, flush=True)
            json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
        time.sleep(0.5)
    # 2) медленный поиск по тексту — только для части оставшихся
    for i, k in enumerate(left):
        if i >= SEARCH_LIMIT:
            break
        t, y = todo[k]
        r = find(t, y)
        cache[k] = r if r else {"miss": now}
        found += bool(r)
    for k in left[SEARCH_LIMIT:]:
        cache.setdefault(k, None)
        if cache[k] is None:
            del cache[k]  # не искали — попробуем в следующий раз
    json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    print("Википедия: найдено", found, "из", len(todo), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
