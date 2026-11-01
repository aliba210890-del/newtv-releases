"""Караоке New TV: каталог по исполнителям (черновик, в приложение не идёт).

Для каждого исполнителя один поиск на YouTube «<исполнитель> караоке» (до 50 роликов), берём только
караоке-ролики с этим исполнителем в названии, разрешённые к встраиванию и не закрытые в KZ/DE.
Из названия ролика вынимаем название песни, повторы склеиваем, оставляем до PER песен.
Выход: karaoke_draft.json (тот же формат, что karaoke.json, плюс поле lang) и отчёт.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from karaoke_check import api, playable, KAR_WORDS

PER = int(os.environ.get("PER", "15"))
LANG_G = {"kk": "Қазақша · Әндер", "ru": "Русские хиты", "de": "Deutsch · Lieder", "en": "English · Songs"}
JUNK = re.compile(r"\((?:[^)]*)\)|\[(?:[^\]]*)\]|караоке|karaoke|минусовка|минус|instrumental|lyrics|текст(?: песни)?|бэк|backing|version|версия|\bhd\b|\b4k\b|official|\bkaraoke version\b|\bс текстом\b|\bkz\b|сөзі|минус бэк|cover|кавер|\bmv\b", re.I)

def norm(s):
    return re.sub(r"[^0-9a-zа-яёәіңғүұқөһ]+", "", s.lower().replace("ё", "е"))

def song_title(title, names):
    t = title
    for n in sorted(names, key=len, reverse=True):
        t = re.sub(re.escape(n), " ", t, flags=re.I)
    t = JUNK.sub(" ", t)
    t = re.sub(r"[|/«»\"“”_#]+", " ", t)
    t = re.sub(r"\s*[-–—:•·]+\s*", " - ", t)
    parts = [p.strip(" .,!-") for p in t.split(" - ") if p.strip(" .,!-")]
    parts = [p for p in parts if len(p) > 1 and not re.fullmatch(r"(feat\.?|ft\.?|и|&|x)", p, re.I)]
    return parts[0] if parts else ""

def main(dst, report):
    art = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "karaoke_artists.json"), encoding="utf-8"))
    songs, lines = [], []
    if os.path.exists(dst):                       # продолжаем: кто уже собран — не ищем снова (лимит YouTube в сутки)
        songs = json.load(open(dst, encoding="utf-8")).get("songs", [])
    done = {s["a"] for s in songs}
    only = os.environ.get("ONLY")
    try:
        collect(art, songs, lines, done, only)
    except SystemExit as e:
        lines.append(f"ОСТАНОВЛЕНО: {e} — остальные исполнители соберутся при следующем запуске")
        print(lines[-1])
    data = {"v": 1, "artists": True, "songs": songs}
    json.dump(data, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lines.insert(0, f"Песен в черновике: {len(songs)}, исполнителей: {len({s['a'] for s in songs})}")
    open(report, "w", encoding="utf-8").write("\n".join(lines) + "\n")

def collect(art, songs, lines, done, only):
    for lang, lst in art.items():
        if only and lang not in only.split(","):
            continue
        for entry in lst:
            names = entry.split("|"); name = names[0]
            if name in done: continue
            q = f"{names[0]} караоке" if lang in ("ru", "kk") else f"{names[0]} karaoke"
            r = api("search", part="snippet", type="video", videoEmbeddable="true", q=q, maxResults=50, regionCode="KZ") or {}
            keys = [norm(n) for n in names]
            got = {}
            for it in r.get("items", []):
                title = it["snippet"]["title"]
                nt = norm(title)
                if not KAR_WORDS.search(title) or not any(k and k in nt for k in keys):
                    continue
                st = song_title(title, names)
                k = norm(st)
                if not k or k in keys or len(k) < 2:
                    continue
                got.setdefault(k, {"t": st, "ids": []})["ids"].append(it["id"]["videoId"])
            ids = [i for v in got.values() for i in v["ids"]]
            ok = playable(ids) if ids else {}
            n = 0
            for v in got.values():
                good = [i for i in v["ids"] if not ok.get(i)][:3]
                if good and n < PER:
                    songs.append({"g": LANG_G[lang], "lang": lang, "a": name, "t": v["t"][:60], "ids": good}); n += 1
            lines.append(f"{name}: {n} песен" + (" — МАЛО" if n < 5 else "") + ("" if not n else "  [" + "; ".join(s["t"] for s in songs[-n:]) + "]"))
            print(lines[-1][:160], flush=True)

if __name__ == "__main__":
    main(*sys.argv[1:3])
