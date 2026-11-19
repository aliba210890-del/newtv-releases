# Проверка поиска адресов по посёлкам вокруг Астаны (живой сервер)
import json, urllib.request, urllib.parse, re, math
from collections import defaultdict
T = json.load(open("jolda-check/addr-tests.json"))
KZL = {"ә": "а", "ғ": "г", "қ": "к", "ң": "н", "ө": "о", "ұ": "у", "ү": "у", "һ": "х", "і": "и"}
def norm(t):
    t = str(t or "").lower().replace("ё", "е"); t = "".join(KZL.get(c, c) for c in t); t = re.sub(r"[«»\"'.,()\-–—/№]", " ", t); return re.sub(r"\s+", " ", t).strip()
def dist(a, b, c, d): return math.hypot((c - a) * 110.5, (d - b) * 111.3 * math.cos(math.radians(a)))
st = defaultdict(lambda: defaultdict(int)); bad = []
for t in T:
    u = "https://joldataxi.kz/api/places?" + urllib.parse.urlencode({"q": t["q"], "lat": t["lat"], "lng": t["lng"]})
    try: items = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "jolda-check"}), timeout=30).read())["items"]
    except Exception as e: items = []
    hn = norm(t["h"]); sw = [w for w in norm(t["st"]).split() if len(w) >= 4 and not w.isdigit()] or norm(t["st"]).split()
    res = "нет"
    for it in items[:3]:
        n = norm(it["name"]); w = n.split()
        if n.endswith(" " + hn) and any(x[:4] in n for x in sw) and dist(t["lat"], t["lng"], it["lat"], it["lng"]) < 8:
            sub = it.get("sub", "")
            res = "уточнить" if "уточните" in sub else "примерно" if "примерно" in sub else "точно"
            break
    st[t["v"]][res] += 1
    if res == "нет": bad.append(t["v"] + " | " + t["q"] + " => " + " ; ".join(i["name"] for i in items[:2]))
tot = defaultdict(int)
for v, d in st.items():
    n = sum(d.values()); [tot.__setitem__(k, tot[k] + c) for k, c in d.items()]
    print(f"{v}: {n} — точно {d['точно']}, примерно {d['примерно']}, уточнить {d['уточнить']}, нет {d['нет']}")
print("ИТОГО", dict(tot), sum(tot.values()))
print("\n".join(bad[:80]))
