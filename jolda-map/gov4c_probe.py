# Разведка: слои района 01_011 (Аршалынский) и 01_012 — какие с адресами домов
import ssl, urllib.request, urllib.parse
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
G = "https://map.gov4c.kz/geoserver/egkn/wms"
def get(u, n=2500):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://map.gov4c.kz/egkn/"}), timeout=90, context=ctx).read().decode("utf-8", "ignore")[:n]
    except Exception as e: return "ERR " + str(e)
def gf(lay, extra=None, n=2500):
    q = {"service": "WFS", "version": "1.1.0", "request": "GetFeature", "typeName": lay, "outputFormat": "application/json", "maxFeatures": "2"}
    if extra: q.update(extra)
    return get(G + "?" + urllib.parse.urlencode(q), n)
out = []
for d in ["01_011", "01_012", "01_001", "01_172"]:
    for kind in ["pch", "rst", "ugl", "ugpol", "uk"]:
        out.append(f"{kind}_{d} " + gf(f"egkn:{kind}_{d}", n=1500))
for f in ["district_id=11", "district_id=12", "kad_nomer LIKE '01011%'", "kad_nomer LIKE '01-011%'"]:
    out.append(f"U_CQL {f} " + gf("egkn:u_view", {"CQL_FILTER": f}))
    out.append(f"NU_CQL {f} " + gf("egkn:nu_view", {"CQL_FILTER": f}))
out.append("DISTRICTS " + gf("egkn:districts", {"maxFeatures": "400", "propertyName": "id,code,name_ru,name,kod,rn_code"}, 40000))
open("probe.txt", "w").write("\n".join(o.replace("\n", " ") for o in out))
