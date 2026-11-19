import re, urllib.request, urllib.parse, json, ssl
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
out = []
def get(u, n=8000000):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"}), timeout=90, context=ctx).read(n).decode("utf-8", "ignore")
    except Exception as e:
        return "ERR " + str(e)
B = "https://address-registry.itanalytics.kz/api/v1/"
for nm in ["Бейбитшилик", "Сарыарка", "Казыбек би"]:
    r = json.loads(get(B + "geonims?limit=500&name=" + urllib.parse.quote(nm)))
    hits = [x for x in r.get("result", []) if "Аршал" in x["full_path_rus"]]
    out.append(f"GEO {nm} total={len(r.get('result', []))} arshaly=" + json.dumps([(x["id"], x["full_path_rus"], x.get("parent_id")) for x in hits], ensure_ascii=False))
    for x in hits[:2]:
        b = json.loads(get(B + f"buildings?geonim_id={x['id']}&limit=500"))
        res = b.get("result", [])
        out.append(f"  BLD geonim {x['id']} n={len(res)} sample=" + json.dumps(res[:2], ensure_ascii=False)[:1200])
        out.append("  NUMS " + ", ".join(sorted({str(y.get('number') or y.get('name_rus') or '') for y in res}))[:800])
open("out.txt", "w").write("\n".join(out))
