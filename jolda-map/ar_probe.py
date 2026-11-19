import re, urllib.request, urllib.parse, json, ssl
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
out = []
def get(u, n=8000000):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"}), timeout=60, context=ctx).read(n).decode("utf-8", "ignore")
    except Exception as e:
        return "ERR " + str(e)
B = "https://address-registry.itanalytics.kz/api/v1/"
# посёлок Жибек Жолы (Аршалы) — дети с.о.
j = json.loads(get(B + "localities?parent_id=154619&limit=50")); out.append("CHILD " + json.dumps([(x["id"], x["name_rus"], x["ats_type"]["value_ru"]) for x in j.get("result", [])], ensure_ascii=False))
vid = [x["id"] for x in j.get("result", []) if x["name_rus"].lower().startswith("жибек")]
vid = vid[0] if vid else 154619
g = json.loads(get(B + f"geonims?locality_id={vid}&limit=200")); out.append("GEONIMS %d " % len(g.get("result", [])) + json.dumps([x["name_rus"] for x in g.get("result", [])][:80], ensure_ascii=False))
b = json.loads(get(B + f"buildings?locality_id={vid}&limit=5")); out.append("BLD " + json.dumps(b, ensure_ascii=False)[:2500])
gr = json.loads(get(B + f"grounds?locality_id={vid}&limit=3")); out.append("GRD " + json.dumps(gr, ensure_ascii=False)[:2000])
# map.gov4c.kz: ссылки на API в скриптах
p = get("https://map.gov4c.kz/")
for js in sorted(set(re.findall(r'(?:src|href)="([^"]+\.js)"', p)))[:12]:
    u = js if js.startswith("http") else "https://map.gov4c.kz/" + js.lstrip("./")
    t = get(u)
    out.append(f"JS {u} len={len(t)}")
    for m in sorted(set(re.findall(r'["`\']((?:https?:)?//[^"`\'\s]{6,120}|/[a-zA-Z0-9_\-]*api[^"`\'\s]{0,100})["`\']', t)))[:80]:
        out.append("   " + m)
open("out.txt", "w").write("\n".join(out))
