# Разведка ArcGIS REST aisgzk.kz и map.gov4c.kz: слои с адресами
import re, urllib.request, json, ssl
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
out = []
def get(u, n=3000000):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40, context=ctx).read(n).decode("utf-8", "ignore")
    except Exception as e:
        return "ERR " + str(e)
def gj(u):
    t = get(u.replace("?f=json", "?f=pjson"))
    try: return json.loads(t)
    except Exception: pass
    h = get(u.replace("?f=json", ""))
    return {"_html": h}
B = "https://aisgzk.kz/arcgis/rest/services"
root = gj(B + "?f=json")
out.append("ROOT " + json.dumps(root)[:300])
if "_html" in root:
    h = root["_html"]; out.append("LINKS " + " ".join(sorted(set(re.findall(r'href="([^"]+)"', h)))[:80]))
svcs = [(s["name"], s["type"]) for s in root.get("services", [])]
for f in root.get("folders", []):
    j = gj(f"{B}/{f}?f=json"); svcs += [(s["name"], s["type"]) for s in j.get("services", [])]
out.append("SERVICES %d" % len(svcs))
for name, typ in svcs[:80]:
    j = gj(f"{B}/{name}/{typ}?f=json")
    layers = j.get("layers", [])
    out.append(f"SVC {name}/{typ} layers={[(l['id'], l['name']) for l in layers][:30]} err={j.get('_err','')[:80]}")
    for l in layers[:40]:
        lj = gj(f"{B}/{name}/{typ}/{l['id']}?f=json")
        flds = [(x.get("name"), x.get("alias")) for x in lj.get("fields", []) or []]
        if any(re.search(r"adr|addr|адрес|street|улиц|house|дом", (str(a) + str(b)), re.I) for a, b in flds):
            out.append(f"  ADDRLAYER {name}/{typ}/{l['id']} {l['name']} fields={flds[:40]}")
# map.gov4c.kz приложение: где API
p = get("https://map.gov4c.kz/")
for js in sorted(set(re.findall(r'src="([^"]+\.js)"', p)))[:10]:
    u = js if js.startswith("http") else "https://map.gov4c.kz/" + js.lstrip("./")
    t = get(u)
    for m in sorted(set(re.findall(r'(https?://[a-z0-9\.\-]+(?:/[A-Za-z0-9_\-\./]*)?)', t)))[:60]:
        if "gov4c" in m or "arcgis" in m.lower() or "api" in m.lower(): out.append("GOV4C " + m)
open("out.txt", "w").write("\n".join(out))
print(len(out))
