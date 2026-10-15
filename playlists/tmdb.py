"""Постеры, описания, рейтинг и жанры фильмов из TMDB (themoviedb.org).

Использование: python tmdb.py <плейлист.m3u> <кэш.json>
Ключ берётся из переменной окружения TMDB_API_KEY (секрет репозитория). Без ключа ничего не делает.
Найденное хранится в кэше (film_tmdb.json): каждый фильм ищется один раз,
ненайденные — повторно через 14 дней (новинки появляются в TMDB не сразу).
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://api.themoviedb.org/3"
MISS_RETRY_DAYS = 14
FILM_GROUPS = ("Фильмы", "Films_4k", "Новинки кино")

# жанры TMDB (id) → категории кинозала
GENRE_IDS = {28: "Боевики", 12: "Приключения", 16: "Мультфильмы", 35: "Комедии", 80: "Детективы и криминал",
             99: "Документальные", 18: "Драмы", 10751: "Семейные", 14: "Фэнтези", 36: "Исторические", 27: "Ужасы",
             10402: "Мюзиклы", 9648: "Детективы и криминал", 10749: "Мелодрамы", 878: "Фантастика",
             53: "Триллеры", 10752: "Военные", 37: "Вестерны"}


def get(path, **params):
    params["api_key"] = os.environ["TMDB_API_KEY"]
    url = API + path + "?" + urllib.parse.urlencode(params)
    for k in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "newtv-playlist-bot", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise SystemExit("TMDB: неверный ключ (401)")
            if e.code == 429:
                time.sleep(5)
                continue
            if k == 2:
                return None
        except Exception:  # noqa: BLE001
            if k == 2:
                return None
        time.sleep(2)
    return None


def norm(s):
    return re.sub(r"[^0-9a-zа-я]+", "", s.lower().replace("ё", "е"))


def split_title(name):
    m = re.match(r"^(.*?)\s*\((\d{4})\)\s*$", name)
    return (m.group(1).strip(), int(m.group(2))) if m else (name.strip(), None)


def key_of(title, year):
    return title.lower().replace("ё", "е") + "|" + (str(year) if year else "")


def find(title, year):
    best, best_score = None, -1
    for y in ([year, None] if year else [None]):
        params = {"query": title, "language": "ru-RU", "include_adult": "false"}
        if y:
            params["year"] = y
        r = get("/search/movie", **params)
        if not r:
            continue
        for it in (r.get("results") or [])[:8]:
            ry = int((it.get("release_date") or "0000")[:4] or 0)
            if year and ry and abs(ry - year) > 1:
                continue
            score = 0
            if norm(it.get("title", "")) == norm(title) or norm(it.get("original_title", "")) == norm(title):
                score += 10
            if year and ry == year:
                score += 5
            score += min(it.get("vote_count", 0), 1000) / 1000
            if it.get("poster_path"):
                score += 1
            if score > best_score:
                best, best_score = it, score
        if best and best_score >= 5:
            break
    if not best or best_score < 5:
        return None
    return {
        "id": best["id"],
        "poster": best.get("poster_path") or "",
        "plot": (best.get("overview") or "").strip(),
        "rating": round(best.get("vote_average") or 0, 1),
        "votes": best.get("vote_count") or 0,
        "genres": [GENRE_IDS[g] for g in best.get("genre_ids", []) if g in GENRE_IDS],
    }


def main(src, cache_path):
    if not os.environ.get("TMDB_API_KEY"):
        print("TMDB_API_KEY не задан — постеры и описания не обновляю")
        return
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
    print("TMDB: всего фильмов", len(set(names)), "ищу", len(todo))
    found = 0
    for i, (k, (t, y)) in enumerate(todo.items()):
        r = find(t, y)
        cache[k] = r if r else {"miss": now}
        found += bool(r)
        time.sleep(0.06)
        if i % 200 == 199:
            json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    print("TMDB: найдено", found, "из", len(todo))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
