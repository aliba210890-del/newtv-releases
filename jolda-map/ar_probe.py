import re, urllib.request, urllib.parse, json, ssl
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
out = []
def get(u, n=3000000):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}), timeout=60, context=ctx).read(n).decode("utf-8", "ignore")
    except Exception as e:
        return "ERR " + str(e)
B = "https://address-registry.itanalytics.kz"
p = get(B + "/")
t = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", p))
i = t.find("Населенные пункты Населенные"); out.append("DOC " + t[3000:14000])
j = json.loads(get(B + "/api/v1/localities?name=" + urllib.parse.quote("Жибек")))
loc = [x for x in j["result"] if "Аршал" in x["full_path_rus"]]
out.append("LOC " + json.dumps(loc, ensure_ascii=False)[:1500])
open("out.txt", "w").write("\n".join(out))
