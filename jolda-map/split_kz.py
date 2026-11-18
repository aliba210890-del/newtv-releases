# Нарезает базу мест всего Казахстана на куски 1°×2° (с запасом 0,25° по краям), чтобы сервер
# держал в памяти только кусок рядом с клиентом. Плюс список всех городов и сёл — для общего поиска.
#   python3 split_kz.py kz-places.json.gz out_dir
import gzip, json, os, sys, math

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
j = json.load(gzip.open(src))
LA, LO, PAD = 1.0, 2.0, 0.25
cells = {}
def keys(la, ln):
    ks = set()
    for dla in (-PAD, 0, PAD):
        for dln in (-PAD, 0, PAD):
            ks.add((math.floor((la + dla) / LA), math.floor((ln + dln) / LO)))
    return ks
def put(kind, item, la, ln):
    for k in keys(la, ln):
        c = cells.setdefault(k, {"pois": [], "addr": [], "ent": []})
        c[kind].append(item)
for p in j["pois"]: put("pois", p, p[2], p[3])
for a in j["addr"]: put("addr", a, a[2], a[3])
for e in j.get("ent", []): put("ent", e, e[0], e[1])
sru = j.get("sru", {})
idx = []
for (a, b), c in cells.items():
    if len(c["pois"]) + len(c["addr"]) < 20: continue
    used = {x[0] for x in c["addr"]} | {p[4] for p in c["pois"] if len(p) > 4 and p[4]}
    c["sru"] = {k: v for k, v in sru.items() if k in used}
    c["cams"] = []; c["license"] = j.get("license", ""); c["built"] = j.get("built", "")
    name = "kz_%d_%d.json.gz" % (a, b)
    with gzip.open(os.path.join(out, name), "wt", encoding="utf-8") as f: json.dump(c, f, ensure_ascii=False, separators=(",", ":"))
    idx.append([a, b, len(c["pois"]), len(c["addr"])])
json.dump({"la": LA, "lo": LO, "cells": sorted(idx), "built": j.get("built", "")}, open(os.path.join(out, "kz-index.json"), "w"))
# все города и сёла Казахстана — их добавим и в базу Астаны, чтобы «Караганда», «Шортанды», «Дамса» находились отовсюду
setl = [p for p in j["pois"] if p[1] in ("Город", "Посёлок")]
json.dump(setl, open(os.path.join(out, "kz-settlements.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("кусков:", len(idx), "мест:", len(j["pois"]), "адресов:", len(j["addr"]), "городов и сёл:", len(setl))
