# Разведка API адресного регистра (address-registry.itanalytics.kz): дома посёлка, есть ли координаты/кадастр
import re, urllib.request, urllib.parse, json, ssl
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
out = []
def get(u, n=3000000):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}), timeout=40, context=ctx).read(n).decode("utf-8", "ignore")
    except Exception as e:
        return "ERR " + str(e)
B = "https://address-registry.itanalytics.kz"
p = get(B + "/")
out.append("PAGE " + re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", p))[:3000])
out += ["HREF " + h for h in sorted(set(re.findall(r'(?:href|src)="([^"]+)"', p)))[:40]]
out += ["PATH " + h for h in sorted(set(re.findall(r'(/api/[A-Za-z0-9_/\-{}?=&.]+)', p)))[:60]]
for path in ["/api/localities?name=Жибек", "/api/v1/localities?name=Жибек", "/localities?name=Жибек", "/api/locality?name=Жибек"]:
    u = B + urllib.parse.quote(path, safe="/?=&")
    out.append("TRY " + path + " => " + get(u, 4000)[:1500].replace("\n", " "))
open("out.txt", "w").write("\n".join(out))
