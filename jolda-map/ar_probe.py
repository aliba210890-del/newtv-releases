import re, urllib.request, urllib.parse, json, ssl
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
out = []
def get(u, n=8000000):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"}), timeout=60, context=ctx).read(n).decode("utf-8", "ignore")
    except Exception as e:
        return "ERR " + str(e)
B = "https://address-registry.itanalytics.kz/api/v1/"
j = {"result": []}
for c in ["113433100", "113433101", "113433000"]:
    r = json.loads(get(B + "localities?cato=" + c)); out.append("CATO " + c + " " + json.dumps([(x["id"], x["full_path_rus"], x["ats_type"]["value_ru"]) for x in r.get("result", [])], ensure_ascii=False)); j["result"] += r.get("result", [])
for x in j["result"]:
    if "Акмол" in x["full_path_rus"]: out.append(f"LOC {x['id']} {x['full_path_rus']} {x['ats_type']['value_ru']}")
for x in j["result"]:
    if "Акмол" in x["full_path_rus"] and x["ats_type"]["value_ru"] not in ("Сельский округ",):
        vid = x["id"]
        for ep in ["geonims", "buildings", "grounds"]:
            r = get(B + f"{ep}?locality_id={vid}&limit=3")
            out.append(f"{ep} {vid}: " + r[:1800])
        r = json.loads(get(B + f"geonims?locality_id={vid}&limit=500")); out.append("STREETS %d " % len(r.get("result", [])) + ", ".join(y["name_rus"] for y in r.get("result", [])))
open("out.txt", "w").write("\n".join(out))
