"""Караоке New TV: проверка и подбор роликов, которые можно показывать в приложении.

Использование: python karaoke_check.py <karaoke.json> <выход karaoke.json> <отчёт.txt>
Ключ — переменная окружения YOUTUBE_API_KEY.

Для каждой песни проверяет её ролики: публичный, встраивание разрешено, не закрыт в Казахстане и Германии.
Неподходящие убираются. Если у песни не осталось ни одного ролика — ищет новый караоке-ролик
(только со встраиванием) и проверяет его так же. Поиск дорогой по лимиту YouTube, поэтому не больше MAX_SEARCH за запуск;
остальные песни найдутся при следующем запуске.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/youtube/v3/"
REGIONS = ("KZ", "DE")
MAX_SEARCH = int(os.environ.get("MAX_SEARCH", "70"))
KAR_WORDS = re.compile(r"караоке|karaoke|минус|минусовка|instrumental|lyrics|текст", re.I)


def api(path, **params):
    params["key"] = os.environ["YOUTUBE_API_KEY"]
    url = API + path + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "newtv-karaoke-bot"}), timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        if "quota" in body.lower():
            raise SystemExit("YouTube: дневной лимит исчерпан")
        print("YouTube API", e.code, body)
        return None


def playable(ids):
    """{id: причина или ''} — '' значит можно показывать."""
    out = {}
    for n in range(0, len(ids), 50):
        chunk = ids[n:n + 50]
        r = api("videos", part="status,contentDetails", id=",".join(chunk)) or {}
        seen = set()
        for v in r.get("items", []):
            seen.add(v["id"])
            st, cd = v.get("status", {}), v.get("contentDetails", {})
            rr = cd.get("regionRestriction") or {}
            why = ""
            if st.get("privacyStatus") != "public":
                why = "не публичное"
            elif not st.get("embeddable", True):
                why = "встраивание запрещено"
            else:
                for reg in REGIONS:
                    if reg in rr.get("blocked", []) or ("allowed" in rr and reg not in rr["allowed"]):
                        why = "закрыто в " + reg
                        break
            out[v["id"]] = why
        for i in chunk:
            if i not in seen:
                out[i] = "удалено"
    return out


def main(src, dst, report):
    data = json.load(open(src, encoding="utf-8"))
    songs = data["songs"]
    all_ids = sorted({i for s in songs for i in s.get("ids", [])})
    st = playable(all_ids)
    lines, searches, fixed, missing = [], 0, 0, 0
    bad_total = sum(1 for i in all_ids if st.get(i))
    lines.append(f"Роликов проверено: {len(all_ids)}, не подходят: {bad_total}")
    for s in songs:
        good = [i for i in s.get("ids", []) if not st.get(i)]
        bad = [f"{i}: {st.get(i)}" for i in s.get("ids", []) if st.get(i)]
        if bad:
            lines.append(f"{s['a']} — {s['t']}: убраны {', '.join(bad)}")
        if not good and searches < MAX_SEARCH:
            searches += 1
            q = f"{s['a']} {s['t']} караоке" if re.search("[а-яёәіңғүұқөһ]", s["a"] + s["t"], re.I) else f"{s['a']} {s['t']} karaoke"
            r = api("search", part="snippet", type="video", videoEmbeddable="true", q=q, maxResults=8, regionCode="KZ") or {}
            cand = [it["id"]["videoId"] for it in r.get("items", []) if KAR_WORDS.search(it["snippet"]["title"])]
            if cand:
                st2 = playable(cand)
                good = [i for i in cand if not st2.get(i)][:3]
            if good:
                fixed += 1
                lines.append(f"  → найдено: {', '.join(good)}")
        if not good:
            missing += 1
            lines.append(f"  → НЕТ рабочего ролика")
        s["ids"] = good
    data["songs"] = [s for s in songs if s["ids"]]
    data["v"] = int(data.get("v", 1)) + 1
    json.dump(data, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    lines.insert(1, f"Поисков: {searches}, найдено замен: {fixed}, без ролика: {missing}, песен в списке: {len(data['songs'])}")
    open(report, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:3]))


if __name__ == "__main__":
    main(*sys.argv[1:4])
