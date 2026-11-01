"""Чистка черновика караоке: мусор в названиях, не-караоке ролики (уроки пианино), обрывки дуэтов, повторы."""
import html, json, re, sys

BAD_VIDEO = re.compile(r"piano|tutorial|разбор|ноты|midi|fl studio|épisode|episode|母", re.I)
CUT = [r"by\s+music studio", r"от\s+langer miami", r"оригинал\s*\+?", r"поем онлайн.*", r"подпишись.*", r"инстаграм.*", r"inst\s+tik.*",
       r"🎤.*", r"🎶", r"сделано в студии", r"казакша", r"казахское", r"\byoutube\b", r"\bfull\b", r"\d{3,4}p\b", r"лирикс", r"мәтін", r"сөзі",
       r"\bback\s*ver\b", r"backver", r"\+\s*вокал\s*\+?", r"вокал", r"перевод на русский.*", r"текст", r"онлайн", r"\btrend\w*", r"тренды.*", r"\bkz\b", r"караоке", r"karaoke"]
FOLD = str.maketrans("әіңғүұқөһё", "аингууконе")

def fold(s):
    return re.sub(r"[^0-9a-zа-я]+", "", s.lower().translate(FOLD))

def clean_title(t, artist_names):
    t = html.unescape(html.unescape(t)).replace("& 39;", "'").replace("&39;", "'")
    for c in CUT:
        t = re.sub(c, " ", t, flags=re.I)
    for n in artist_names:                      # только целым словом: «Мот» не должен резать «Мотылёк»
        t = re.sub(r"(?<!\w)" + re.escape(n) + r"(?!\w)", " ", t, flags=re.I)
    t = re.sub(r"[~●•|\"«»“”*]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" .,!-–—+&:")
    if re.search(r"(^|\s)ов$|^ов\s|^гр$|^hi$", t, re.I):
        return ""
    if re.match(r"^(и|feat\.?|ft\.?|&|x)\s", t, re.I) or re.search(r"\s(и|&|feat\.?)$", t, re.I) or len(fold(t)) < 2:
        return ""
    if re.search(r"\bfeat\b|\bи\s+[А-ЯA-Z]", t) and len(t.split()) <= 4 and not re.search(r"[a-zа-я]{4,}\s[a-zа-я]{4,}", t.lower()):
        return ""
    return t[:48]

def main(src, dst):
    d = json.load(open(src, encoding="utf-8"))
    artists = {s["a"] for s in d["songs"]}
    arts = json.load(open("playlists/karaoke_artists.json", encoding="utf-8"))
    names = {e.split("|")[0]: e.split("|") for v in arts.values() for e in v}
    other = [n for v in names.values() for n in v]
    global OTHER_K
    OTHER_K = {fold(n) for n in other}
    by = {}
    for s in d["songs"]:
        t = clean_title(s["t"], names.get(s["a"], [s["a"]]) + other)
        if not t or BAD_VIDEO.search(s["t"]) or fold(t) in OTHER_K:
            continue
        k = fold(t)
        lst = by.setdefault(s["a"], [])
        dup = next((x for x in lst if x["k"] == k or (len(k) > 4 and (x["k"].startswith(k) or k.startswith(x["k"])))), None)
        if dup:
            dup["ids"] = (dup["ids"] + [i for i in s["ids"] if i not in dup["ids"]])[:3]
            if len(t) < len(dup["t"]): dup["t"] = t; dup["k"] = k
            continue
        lst.append(dict(s, t=t, k=k))
    out, rep = [], []
    for a, lst in by.items():
        if len(lst) < 4:
            rep.append(f"убран исполнитель {a}: всего {len(lst)} песен"); continue
        for x in lst[:15]:
            x.pop("k"); out.append(x)
        rep.append(f"{a}: {min(len(lst),15)} — " + "; ".join(x["t"] for x in lst[:15]))
    d["songs"] = out
    json.dump(d, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"песен: {len(out)}, исполнителей: {len({s['a'] for s in out})}")
    print("\n".join(rep))

if __name__ == "__main__":
    main(*sys.argv[1:3])
