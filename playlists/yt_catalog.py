"""Свой законный кинозал New TV: полные фильмы с официальных YouTube-каналов правообладателей.

Использование: python yt_catalog.py <каналы.json> <выход.m3u> <кэш.json>
Ключ — переменная окружения YOUTUBE_API_KEY (секрет репозитория). Без ключа выдаёт прежний список из кэша.

Фильмы показываются в приложении через официальный плеер YouTube (законно, реклама YouTube сохраняется).
Список каналов — в каналы.json: {"channels": [{"name": "...", "handle": "@...", "group": "...", "min_minutes": 55}]}.
Каталог обновляется не чаще раза в сутки, чтобы не тратить дневной лимит YouTube.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3/"
REFRESH_HOURS = 20
SKIP_WORDS = ("трейлер", "trailer", "тизер", "фрагмент", "#shorts", "отрывок", "анонс", "backstage", "за кадром", "интервью")
REGION = "DE"  # главная аудитория — Германия и Европа: пропускаем видео, закрытые там

GENRES = [("Комедии", ("комедия", "комедийный")), ("Военные", ("военный", "война", "военная драма")),
          ("Детективы", ("детектив", "криминал")), ("Приключения", ("приключения", "приключенческий")),
          ("Сказки", ("сказка", "фэнтези")), ("Мелодрамы", ("мелодрама",)), ("Фантастика", ("фантастика", "фантастический")),
          ("Исторические", ("исторический", "историческая")), ("Музыкальные", ("музыкальный", "мюзикл")),
          ("Драмы", ("драма",)), ("Семейные", ("семейный", "детский"))]


def api(path, **params):
    params["key"] = os.environ["YOUTUBE_API_KEY"]
    url = API + path + "?" + urllib.parse.urlencode(params)
    for k in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "newtv-playlist-bot"}), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code in (400, 403):
                raise SystemExit(f"YouTube API {e.code}: {body}")
            time.sleep(3 * (k + 1))
        except Exception:  # noqa: BLE001
            time.sleep(3 * (k + 1))
    return None


def iso_minutes(d):
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    if not m:
        return 0
    dd, h, mi, s = (int(x or 0) for x in m.groups())
    return dd * 1440 + h * 60 + mi + s / 60


def channel_id(ch, cache):
    key = "id:" + (ch.get("handle") or ch["name"])
    if cache.get(key):
        return cache[key]
    cid = None
    if ch.get("id"):
        cid = ch["id"]
    elif ch.get("handle"):
        r = api("channels", part="id,snippet", forHandle=ch["handle"])
        items = (r or {}).get("items") or []
        if items:
            cid = items[0]["id"]
            cache["title:" + ch["handle"]] = items[0]["snippet"]["title"]
            print("канал", ch["handle"], "→", items[0]["snippet"]["title"], cid)
    if not cid and ch.get("search"):
        r = api("search", part="snippet", type="channel", q=ch["search"], maxResults=3)
        for it in (r or {}).get("items") or []:
            print("поиск канала", repr(ch["search"]), "→", it["snippet"]["title"], it["snippet"]["channelId"])
        items = (r or {}).get("items") or []
        if items:
            cid = items[0]["snippet"]["channelId"]
            cache["title:" + (ch.get("handle") or ch["name"])] = items[0]["snippet"]["title"]
    if cid:
        cache[key] = cid
    else:
        print("::warning::канал не найден:", ch.get("handle") or ch["name"])
    return cid


def fetch_channel(cid, min_minutes, limit=5000, include=None, exclude=None):
    r = api("channels", part="contentDetails", id=cid)
    items = (r or {}).get("items") or []
    if not items:
        return []
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, token = [], None
    while True:
        p = {"part": "contentDetails", "playlistId": uploads, "maxResults": 50}
        if token:
            p["pageToken"] = token
        r = api("playlistItems", **p)
        if not r:
            break
        ids += [it["contentDetails"]["videoId"] for it in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token or len(ids) >= limit:
            break
    out = []
    for n in range(0, len(ids), 50):
        r = api("videos", part="snippet,contentDetails,status", id=",".join(ids[n:n + 50]))
        for v in (r or {}).get("items", []):
            sn, cd, st = v["snippet"], v["contentDetails"], v.get("status", {})
            if not st.get("embeddable", True) or st.get("privacyStatus") != "public":
                continue
            rr = cd.get("regionRestriction") or {}
            if REGION in rr.get("blocked", []) or ("allowed" in rr and REGION not in rr["allowed"]):
                continue
            if iso_minutes(cd.get("duration")) < min_minutes:
                continue
            title = sn.get("title", "")
            if any(w in title.lower() for w in SKIP_WORDS):
                continue
            # у телеканалов в загрузках и новости, и шоу: берём только нужное (например, «телехикая», «бөлім»)
            if include and not re.search(include, title, re.I):
                continue
            if exclude and re.search(exclude, title, re.I):
                continue
            th = sn.get("thumbnails", {})
            img = (th.get("maxres") or th.get("standard") or th.get("high") or th.get("medium") or {}).get("url", "")
            out.append({"id": v["id"], "title": title, "desc": sn.get("description", ""), "img": img})
    return out


EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿⬀-⯿️‍]+")


FOREIGN_JUNK = re.compile(r"\s*[-–—:(|]\s*(?:jetzt\s+)?(?:den\s+)?ganze[nr]?\s+film.*$|\s*[-–—]\s*kostenlos.*$|\s*\|?\s*(?:free\s+)?(?:full\s+)?movie.*$|\s+bei moviedome.*$", re.I)


def parse_foreign(title, part=0):
    """Заголовки зарубежных каналов: «Hook | Room for Rent | Thriller | Free Movie», «Mulan - Legende … - Ganzen Film kostenlos …»."""
    parts = [x.strip() for x in title.split("|")]
    t = parts[part] if len(parts) > part else parts[0]
    ep = None
    for x in parts[1:]:
        m = re.match(r"^(\d+)\s*сери[яи]$", x, re.I)
        if m:
            ep = m.group(1)
    if " / " in t:  # «Մոր սիրտը 1957 - Հայկական Ֆիլմ / Mor sirty / Сердце матери» — берём русское название, если есть
        alts = [re.sub(r"\s*\(\s*на русском[^)]*\)", "", x).strip() for x in t.split(" / ")]
        cyr = [x for x in alts if re.search("[а-яё]", x, re.I)]
        t = cyr[-1] if cyr else alts[0]
    t = re.sub(r"\s*-\s*(?:Հայկական ֆիլմ|haykakan film)\s*$", "", t, flags=re.I)
    t = re.sub(r"[«»\"]?\s*(?:көркем фильмі|к/ф|х/ф|художественный фильм)\s*", " ", t, flags=re.I)
    t = re.sub(r"\s*\([^)]*(?:ganze[nr]? film|komplett|full movie)[^)]*\)?.*$", "", t, flags=re.I)
    t = FOREIGN_JUNK.sub("", t)
    t = re.sub(r"\s+-\s+(?:spannende[rs]?|packende[rs]?|romantische[rs]?|lustige[rs]?)\s+\w+$", "", t, flags=re.I)
    t = re.sub(r"\s*\((?:[^()]*ganzer film[^()]*|[^()]*komplett[^()]*)\)\s*", " ", t, flags=re.I)
    if ":" in t and re.search(r"wahnsinn|klassiker|so (?:gut|spannend)|muss man|unglaublich", t.split(":")[0], re.I):
        t = t.split(":", 1)[1]
    years = re.findall(r"\b(19[2-9]\d|20[0-2]\d)\b", title)
    t = re.sub(r"\s*\((?:19|20)\d\d\)", "", t)
    t = re.sub(r"\s*\([^()]*(?:реж|ж\.\)|г\.\))[^()]*\)?\s*$", "", t)  # («Маленький принц…», реж: …, 2019 ж.)
    t = re.sub(r"\s+(?:19|20)\d\d\s*$", "", t)
    t = re.sub(r"\s+", " ", t).strip(' "«»-–—:')
    if t.isupper() and len(t) > 3:
        t = t[:1] + t[1:].lower()
    if ep:
        t += f" — {ep} серия"
    return t, (int(years[0]) if years else None), title.lower()


def parse_title(title):
    """Название, год и текст для поиска жанра из заголовка видео. Номер серии остаётся в названии.
    «Иван Васильевич меняет профессию (FullHD, комедия, реж. Леонид Гайдай, 1973 г.)»,
    «Тихий дон 2 серия (1957) Драма», «Ну, погоди! Каникулы 🐺 Субботник 🐰 Премьера на канале Союзмультфильм HD»."""
    low = title.lower()
    years = re.findall(r"\b(19[2-9]\d|20[0-2]\d)\b", title)
    year = int(years[-1]) if years else None
    t = title
    if EMOJI.search(t):  # мультфильмы Союзмультфильма: «Серия 🐺 Эпизод ⭐ …»
        parts = [x.strip(" -—|.,") for x in EMOJI.split(t)]
        parts = [re.sub(r"\s*(смотреть онлайн|онлайн|мультик|мультфильм)\b.*$", "", x, flags=re.I).strip(" -—") for x in parts]
        parts = [x for x in parts if x and not re.search(r"премьер|союзмультфильм|мультфильм для|мультики|\bhd\b|сборник|^\d{4}$", x, re.I)]
        t = " — ".join(parts[:2]) if parts else t
    t = re.sub(r"\s*[|│/].*$", "", t).strip()
    if "—" in t and re.search(r"советск|фильм|детектив|комеди|драм|мелодрам|боевик|который|которая", t.split("—")[0], re.I) and not EMOJI.search(title):
        t = t.split("—", 1)[1].strip()
    t = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]\s*", " ", t)  # (FullHD, комедия, реж. …, 1973 г.) / (1957)
    t = re.sub(r"\s+(драма|комедия|мелодрама|детектив|сказка|боевик|приключения)\s*$", "", t, flags=re.I)
    t = re.sub(r"\b(премьера|full ?hd|4k|4к|hd)\b", "", t, flags=re.I)
    m = re.search(r"(\d+)\s*-?\s*я?\s*сери[яи]|сери[яи]\s*(\d+)", t, re.I)
    ep = (m.group(1) or m.group(2)) if m else None
    if m:
        t = (t[:m.start()] + t[m.end():])
    name = re.sub(r"\s+", " ", t).strip(' "«»-—,.')
    if ep:
        name += f" — {ep} серия"
    return name or title.strip(), year, low


SPAM = re.compile(r"подпис|колокольч|ставь|лайк|поделись|likee|товар|магазин|сборник|все серии|серии подряд|плейлист|канал|"
                  r"приложени|скачай|смотрите|смотри |премьер|новая серия|новую серию|новые серии|в сборник вошли|instagram|vk\.com|"
                  r"vkontakte|telegram|телеграм|tiktok|одноклассник|яндекс|дзен|соцсет|социальн|сайт|©|rutube|youtube|"
                  r"subscribe|abonniere|subskryb|підпис|жазыл|арнамыз|бөліс|мульт.{0,15}для детей|для малышей|мультики для|мультик\b|"
                  r"дошкольник|не пропустить|мерч|riki|игры с|facebook|whatsapp|twitter|мобильді|қосымша|հետևեք|կայքը|ֆիլմեր|"
                  r"ganzer film|kostenlos|in voller länge|moviedome|netzkino|watch other|our site|full movie|free movie|"
                  r"киножурнал|хочу вс[её] знать|научно-популярный сериал|по ссылке|anzeige|strompreise|znajdziesz tu|witamy w", re.I)
SERIES_ABOUT = [  # описание сериала, если у ролика нет нормального своего
    ("оранжевая корова", "Мультсериал «Союзмультфильма» о весёлой семье коров и забавных приключениях их детей."),
    ("новое простоквашино", "Новые истории о коте Матроскине, псе Шарике, почтальоне Печкине и жителях деревни Простоквашино."),
    ("простоквашино", "Истории о дяде Фёдоре, коте Матроскине, псе Шарике и почтальоне Печкине из деревни Простоквашино."),
    ("фиксики", "Мультсериал о фиксиках — маленьких человечках, которые живут внутри техники и тайно её чинят. Дети узнают, как устроены вещи вокруг."),
    ("ну, погоди! каникулы", "Новые приключения Волка и Зайца из знаменитого мультфильма «Ну, погоди!» — теперь на каникулах."),
    ("ну, погоди", "Знаменитый мультфильм о Волке, который гоняется за Зайцем и всегда остаётся ни с чем."),
    ("умка", "Мультсериал о белом медвежонке Умке и его друзьях на Севере — по мотивам знаменитого советского мультфильма."),
    ("крутиксы", "Мультсериал о звериной суперкоманде, которая стоит на страже мира и порядка."),
    ("чебурашка", "Новые истории о Чебурашке и крокодиле Гене от студии «Союзмультфильм»."),
    ("смешарики", "Мультсериал о добрых круглых героях — Кроше, Ёжике, Нюше, Бараше, Лосяше и их друзьях."),
]


def series_about(name):
    low = name.lower()
    for k, v in SERIES_ABOUT:
        if low.startswith(k) or (" " + k) in low:
            return v
    return ""


def clean_desc(d):
    """Описание ролика без рекламы канала: «Подпишись», ссылки, хэштеги, таймкоды, списки других мультиков.
    Если осмысленного текста не осталось — пусто (лучше без описания, чем с мусором)."""
    d = re.sub(r"https?://\S+|www\.\S+", "", d)
    d = re.sub(r"#\S+|@\S+", "", d)
    d = re.sub(r"^.*?Սյուժե\s*", "", d, flags=re.S)       # армянские: «Сюжет» — дальше идёт описание
    parts = []
    for seg in re.split(r"\n|[►▶👉👇🔻⭐🔹🔸▫▪•|*]+|\s[-–—]{2,}\s", d):
        parts.extend(re.split(r"(?<=[.!?:])\s+", seg))
    keep = []
    for x in parts:
        x = EMOJI.sub(" ", x)
        x = re.sub(r"\s+", " ", x).strip(" -–—:;,.!")
        if not x or SPAM.search(x) or re.search(r"\d{1,2}:\d{2}", x):
            continue
        if len(x.split()) < 4 or not re.search(r"[^\W\d_]{3}", x):
            continue
        keep.append(x + ("" if x[-1] in ".!?…" else "."))
    t = " ".join(keep)
    if len(t) < 60:
        return ""
    if len(t) > 650:
        cut = t[:650]
        end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        t = cut[:end + 1] if end > 200 else cut.rsplit(" ", 1)[0] + "…"
    return t.replace('"', "“")


FOREIGN_GENRES = {   # жанр по названию (а если там нет — по описанию); порядок важен: «Horrorkomödie» — это Horror
    "de": [("Weihnachtsfilme", r"weihnacht|christmas"), ("Horror", r"horror|grusel"), ("Thriller", r"thriller|krimi|crime|mystery"),
           ("Action", r"action|martial"), ("Sci-Fi", r"sci-?fi|science.?fiction"), ("Western", r"western"),
           ("Komödie", r"komödie|comedy|komödi"), ("Liebesfilme", r"liebesfilm|romanze|romanti|romance|liebesdrama"),
           ("Abenteuer", r"abenteuer|adventure"), ("Drama", r"drama"), ("Dokumentation", r"doku")],
    "en": [("Christmas", r"christmas|holiday"), ("Horror", r"horror"), ("Thriller", r"thriller|crime|mystery|suspense"),
           ("Action", r"action|martial"), ("Sci-Fi", r"sci-?fi|science.?fiction"), ("Western", r"western"),
           ("Comedy", r"comedy|comedic"), ("Romance", r"romance|romantic|rom-?com"), ("Adventure", r"adventure"),
           ("Drama", r"drama"), ("Documentary", r"documentary")],
}
FOREIGN_OTHER = {"de": "Weitere Filme", "en": "More Movies"}


def foreign_genre(lang, title, desc):
    for text in (title.lower(), desc.lower()[:300]):
        for g, rx in FOREIGN_GENRES[lang]:
            if re.search(rx, text):
                return g
    return FOREIGN_OTHER[lang]


def series_of(ch, raw_title, name):
    """Название мультсериала, к которому относится серия (или пусто).
    Сериалы потом показываются в приложении одной карточкой, а серии — внутри неё."""
    rule = ch.get("series")
    if not rule:
        return ""
    if rule == "emoji":            # Союзмультфильм: «Оранжевая корова 🐮 Рок-группа ⭐ Премьера…»
        return name.split(" — ")[0].strip() if " — " in name and EMOJI.search(raw_title) else ""
    if rule == "kz":               # Balapan / Qazaqstan TV: «Қызық әлем. 2-маусым. 38 бөлім», ««СЫРҒАЛЫМ-2». Телехикая. 32-бөлім»
        m = re.match(r"^\s*«?(.+?)»?\s*(?:\.\s*|\s+)(?:\d+\s*-?\s*маусым|телехикая|\d+\s*-?\s*бөлім)", raw_title, re.I)
        if not m:
            return ""
        t = re.sub(r"[\s-]+\d+$", "", m.group(1).strip(' .«»"-!'))
        t = t.strip(' .-')
        if t.count("»") > t.count("«"):
            t = "«" + t
        return t.title() if t.isupper() else t[:1].upper() + t[1:]
    return rule                    # одно название на весь канал: «Фиксики», «Peppa Wutz»


def genre_of(text):
    for g, words in GENRES:
        if any(w in text for w in words):
            return g
    return None


def main(cfg_path, dst, cache_path):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    try:
        cache = json.load(open(cache_path, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    fresh = time.time() - cache.get("updated", 0) < REFRESH_HOURS * 3600
    known = cache.get("videos") or {}
    missing = [ch for ch in cfg["channels"] if cache.get("id:" + (ch.get("handle") or ch["name"])) not in known]
    if os.environ.get("YOUTUBE_API_KEY") and (not fresh or missing):
        videos = dict(known) if fresh else {}
        for ch in (missing if fresh else cfg["channels"]):
            cid = channel_id(ch, cache)
            if not cid:
                continue
            vids = fetch_channel(cid, ch.get("min_minutes", 55), ch.get("max", 5000), ch.get("include"), ch.get("exclude"))
            print(ch.get("handle") or ch["name"], "— фильмов:", len(vids))
            videos[cid] = vids
        if sum(len(v) for v in videos.values()):
            cache["videos"] = videos
            if not fresh:
                cache["updated"] = int(time.time())
        json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True)
    elif not os.environ.get("YOUTUBE_API_KEY"):
        print("YOUTUBE_API_KEY не задан — беру список из кэша")

    rows, seen = [], set()
    for ch in cfg["channels"]:
        cid = cache.get("id:" + (ch.get("handle") or ch["name"]))
        vids = (cache.get("videos") or {}).get(cid, [])
        inc, exc = ch.get("include"), ch.get("exclude")
        for v in vids:
            if (inc and not re.search(inc, v["title"], re.I)) or (exc and re.search(exc, v["title"], re.I)):
                continue  # фильтр применяется и к уже сохранённому списку
            name, year, text = parse_foreign(v["title"], ch.get("title_part", 0)) if ch.get("foreign") else parse_title(v["title"])
            k = (name.lower(), year)
            if k in seen:
                continue
            seen.add(k)
            group = ch["group"]
            if ch.get("genres") in FOREIGN_GENRES:      # «Deutsch · Filme» → «Deutsch · Thriller» и т. д.
                group = group.split(" · ")[0] + " · " + foreign_genre(ch["genres"], v["title"], v.get("desc", ""))
            rows.append({"ch": ch, "v": v, "name": name, "year": year, "group": group, "ser": series_of(ch, v["title"], name)})
    # мультсериалы: серия — в сериал, только если в нём хотя бы 5 серий; одно написание названия на сериал
    cnt, disp = {}, {}
    for r in rows:
        if r["ser"]:
            key = r["ser"].lower().replace("ё", "е")
            cnt[key] = cnt.get(key, 0) + 1
            disp.setdefault(key, {}).setdefault(r["ser"], 0)
            disp[key][r["ser"]] += 1
    for r in rows:
        key = r["ser"].lower().replace("ё", "е")
        if not r["ser"] or cnt.get(key, 0) < 5:
            r["ser"] = ""
            continue
        r["ser"] = max(disp[key].items(), key=lambda x: x[1])[0]
        if r["group"] == "Мультфильмы":
            r["group"] = "Мультсериалы"
    # маленькие жанры (меньше 8 фильмов) — в «Weitere Filme» / «More Movies»
    gcnt = {}
    for r in rows:
        gcnt[r["group"]] = gcnt.get(r["group"], 0) + 1
    for r in rows:
        lang = r["ch"].get("genres")
        if lang in FOREIGN_OTHER and gcnt[r["group"]] < 8:
            r["group"] = r["group"].split(" · ")[0] + " · " + FOREIGN_OTHER[lang]
    lines, n = [], 0
    for r in rows:
        v, name, year = r["v"], r["name"], r["year"]
        label = name + (f" ({year})" if year else "")
        attrs = f'group-title="{r["group"]}"'
        if v.get("img"):
            attrs += f' tvg-logo="{v["img"]}" poster="{v["img"]}"'
        if r["ser"]:
            attrs += f' x-series="{r["ser"]}"'
        d = (series_about(name) if r["ch"]["group"] == "Мультфильмы" else "") or clean_desc(v.get("desc", ""))
        if d:
            attrs += f' description="{d}"'
        lines.append(f"#EXTINF:-1 {attrs},{label}")
        lines.append("https://www.youtube.com/watch?v=" + v["id"])
        n += 1
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    print("свой кинозал (YouTube):", n, "фильмов")


if __name__ == "__main__":
    main(*sys.argv[1:4])
