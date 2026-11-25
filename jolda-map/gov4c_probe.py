# Разведка: geoserver кадастровой карты (WFS/WMS) — участки и недвижимость с адресами
import ssl, urllib.request, urllib.parse
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
G = "https://map.gov4c.kz/egkn/wms"
def get(u, n=3000):
    try: return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://map.gov4c.kz/egkn/"}), timeout=60, context=ctx).read().decode("utf-8", "ignore")[:n]
    except Exception as e: return "ERR " + str(e)
out = []
bb = "51.072,71.762,51.077,71.770"  # lat/lon для WFS 2.0 EPSG:4326
for lay in ["egkn:u_view", "egkn:ned_view", "egkn:nu_view", "egkn:uk_view", "egkn:ul_view", "egkn:part_view", "egkn:inv"]:
    for v in ["1.1.0", "2.0.0"]:
        q = {"service": "WFS", "version": v, "request": "GetFeature", ("typeNames" if v == "2.0.0" else "typeName"): lay, "outputFormat": "application/json", ("count" if v == "2.0.0" else "maxFeatures"): "3", "srsName": "EPSG:4326", "bbox": (bb + ",EPSG:4326") if v == "2.0.0" else "71.762,51.072,71.770,51.077,EPSG:4326"}
        out.append(f"WFS {lay} {v} " + get(G + "?" + urllib.parse.urlencode(q)))
    q = {"service": "WMS", "version": "1.1.1", "request": "GetFeatureInfo", "layers": lay, "query_layers": lay, "srs": "EPSG:4326", "bbox": "71.762,51.072,71.770,51.077", "width": "256", "height": "256", "x": "128", "y": "128", "info_format": "application/json", "feature_count": "5"}
    out.append(f"GFI {lay} " + get(G + "?" + urllib.parse.urlencode(q)))
out.append("CAPS " + get(G + "?service=WFS&request=GetCapabilities", 3000))
open("probe.txt", "w").write("\n".join(o.replace("\n", " ") for o in out))
