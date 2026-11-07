# Разведка: какие наборы на data.egov.kz есть про адреса/улицы/дома Астаны и Акмолинской области
import re, html, urllib.request, urllib.parse, json, os
K = os.environ.get("K", "")
out = []
def get(u):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).read().decode("utf-8", "ignore")
    except Exception as e:
        return "ERR " + str(e)
seen = {}
for q in ["улиц Астана", "наименования улиц", "переименование улиц", "населенные пункты", "елді мекен", "адресный", "Астана адрес", "жилые дома", "многоквартирные", "КСК", "ОСИ", "здания", "Ақмола облысы елді мекендер", "ономастика", "кадастр"]:
    for pg in (1, 2):
        t = get("https://data.egov.kz/datasets/search?" + urllib.parse.urlencode({"text": q, "page": pg}))
        for m in re.finditer(r'datasets/view\?index=([a-z0-9_\-]+)[^>]*>(.*?)</a>', t, re.S):
            name = re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", m.group(2)))).strip()
            if name and m.group(1) not in seen:
                seen[m.group(1)] = name; out.append(f"{q} | {m.group(1)} | {name[:140]}")
open("out.txt", "w").write("\n".join(out))
print(len(out))
