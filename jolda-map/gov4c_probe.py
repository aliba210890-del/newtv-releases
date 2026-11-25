# Разведка: WFS кадастровой карты — поля и выборка участков
import ssl, urllib.request, urllib.parse
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
G = "https://map.gov4c.kz/geoserver/egkn/wms"
def get(u, n=3000):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://map.gov4c.kz/egkn/"}), timeout=90, context=ctx).read().decode("utf-8", "ignore")[:n]
    except Exception as e: return "ERR " + str(e)
out = []
for lay in ["egkn:u_view", "egkn:ned_view", "egkn:nu_view", "egkn:uk_view", "egkn:ul_view", "egkn:part_view"]:
    out.append(f"DESC {lay} " + get(G + "?" + urllib.parse.urlencode({"service": "WFS", "version": "1.1.0", "request": "DescribeFeatureType", "typeName": lay}), 4000))
    out.append(f"ANY {lay} " + get(G + "?" + urllib.parse.urlencode({"service": "WFS", "version": "1.1.0", "request": "GetFeature", "typeName": lay, "outputFormat": "application/json", "maxFeatures": "2"}), 3000))
    out.append(f"BB {lay} " + get(G + "?" + urllib.parse.urlencode({"service": "WFS", "version": "1.1.0", "request": "GetFeature", "typeName": lay, "outputFormat": "application/json", "maxFeatures": "2", "srsName": "EPSG:4326", "bbox": "51.06,71.74,51.09,71.79,urn:ogc:def:crs:EPSG::4326"}), 3000))
c = get(G + "?service=WFS&version=1.1.0&request=GetCapabilities", 10**7)
import re
out.append("FT " + " ".join(re.findall(r"<Name>(egkn:[^<]+)</Name>", c)))
for m in re.finditer(r"<FeatureType>.*?</FeatureType>", c, re.S):
    if "u_view" in m.group(0) or "ned_view" in m.group(0): out.append("FTD " + m.group(0)[:800])
open("probe.txt", "w").write("\n".join(o.replace("\n", " ") for o in out))
