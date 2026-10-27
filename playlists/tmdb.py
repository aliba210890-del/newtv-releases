"""Постеры, рейтинг и жанры фильмов кинозала из TMDB (themoviedb.org, бесплатный ключ API).

Использование: python tmdb.py <плейлист.m3u> <кэш_tmdb.json> <кэш_wiki.json> <выход_meta.json>

Ключ берётся из переменной TMDB_API_KEY (ключ v3 или длинный токен v4). Без ключа или без сети
просто объединяет то, что уже есть в кэшах, — кинозал не ломается.
Каждый фильм ищется один раз; ненайденные — повторно через 30 дней.
Результат для categorize.py: {ключ: {"poster", "rating", "votes", "genres", "plot", "page"}}.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from categorize import FILM_GROUPS, key_of, parse, split_title

API = "https://api.themoviedb.org/3"
MISS_RETRY_DAYS = 30
MAX_NEW_PER_RUN = 1500
GENRES = {28: "Боевики", 12: "Приключения", 16: "Мультфильмы", 35: "Комедии", 80: "Детективы и криминал",
          99: "Документальные", 18: "Драмы", 10751: "Семейные", 14: "Фэнтези", 36: "Исторические", 27: "Ужасы",
          10402: "Мюзиклы", 9648: "Детективы и криминал", 10749: "Мелодрамы", 878: "Фантастика", 53: "Триллеры",
          10752: "Военные", 37: "Вестерны"}


def norm(s):
    return re.sub(r"[^0-9a-zа-я]+", "", (s or "").lower().replace("ё", "е"))


def get(path, key, **params):
    params.setdefault("language", "ru-RU")
    headers = {"Accept": "application/json", "User-Agent": "NewTV-playlist-bot/1.0"}
    if len(key) > 40:
        headers["Authorization"] = "Bearer " + key
    else:
        params["api_key"] = key
    url = API + path + "?" + urllib.parse.urlencode(params)
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise SystemExit("::warning::TMDB: ключ не подходит (401) — постеры не обновлены")
            if e.code == 429:
                time.sleep(5 * (k + 1)); continue
            return None
        except Exception:  # noqa: BLE001 — сеть: повторяем, потом сдаёмся
            time.sleep(2 * (k + 1))
    return None


def best_match(results, title, year):
    want = norm(title)
    best, score = None, -1
    for r in results or []:
        y = int((r.get("release_date") or "0000")[:4] or 0)
        names = {norm(r.get("title")), norm(r.get("original_title"))}
        s = 0
        if want in names:
            s += 10
        elif any(want and n and (want in n or n in want) for n in names):
            s += 3
        else:
            continue
        if year:
            if y and abs(y - year) <= 1:
                s += 5
            elif y:
                continue
        s += min(r.get("vote_count") or 0, 5000) / 5000
        if s > score:
            best, score = r, s
    return best


def lookup(title, year, key):
    params = {"query": title, "include_adult": "false"}
    if year:
        params["year"] = year
    r = get("/search/movie", key, **params)
    hit = best_match((r or {}).get("results"), title, year)
    if not hit and year:  # год у источника иногда на год больше/меньше
        params.pop("year")
        r = get("/search/movie", key, **params)
        hit = best_match((r or {}).get("results"), title, year)
    if r is None:
        return None  # сеть — не запоминаем как «не найдено»
    if not hit:
        return {"miss": int(time.time())}
    return {"id": hit["id"], "poster": hit.get("poster_path") or "", "rating": round(hit.get("vote_average") or 0, 1),
            "votes": hit.get("vote_count") or 0, "genres": [GENRES[g] for g in hit.get("genre_ids", []) if g in GENRES],
            "plot": (hit.get("overview") or "").strip()}


def main(src, tmdb_path, wiki_path, out_path):
    try:
        cache = json.load(open(tmdb_path, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    try:
        wiki = json.load(open(wiki_path, encoding="utf-8"))
    except (OSError, ValueError):
        wiki = {}
    _, items = parse(src)
    keys = {}
    for it in items:
        if it["group"] in FILM_GROUPS:
            t, y = split_title(it["name"])
            keys[key_of(t, y)] = (t, y)

    key = os.environ.get("TMDB_API_KEY", "").strip()
    if key:
        now, done = int(time.time()), 0
        for k, (t, y) in keys.items():
            c = cache.get(k)
            if c is not None and not (c.get("miss") and now - c["miss"] > MISS_RETRY_DAYS * 86400):
                continue
            if done >= MAX_NEW_PER_RUN:
                break
            res = lookup(t, y, key)
            done += 1
            if res is not None:
                cache[k] = res
            time.sleep(0.05)
        with open(tmdb_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=0, sort_keys=True)
        found = sum(1 for k in keys if cache.get(k) and not cache[k].get("miss"))
        print(f"TMDB: запросов {done}, найдено {found} из {len(keys)}")
    else:
        print("TMDB: ключа нет — постеры и рейтинг не обновляются")

    meta = {}
    for k in keys:
        w = wiki.get(k) or {}
        t = cache.get(k) or {}
        m = {}
        if w.get("plot") and not w.get("miss"):
            m.update(plot=w["plot"], page=w.get("page"))
        if t and not t.get("miss"):
            for f in ("poster", "rating", "votes", "genres"):
                if t.get(f):
                    m[f] = t[f]
            if not m.get("plot") and t.get("plot"):
                m["plot"] = t["plot"]  # описание TMDB — без пометки «Википедия»
        if m:
            meta[k] = m
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    print(f"описания/постеры: {len(meta)} фильмов")


if __name__ == "__main__":
    main(*sys.argv[1:5])
