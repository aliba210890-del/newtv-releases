# Разведка: сайты застройщиков Астаны — главная, robots, sitemap. Сырые ответы в zhk_probe.tgz
import urllib.request, os, ssl, re, tarfile
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
SITES = ["bi.group", "www.bi.group", "bazis.kz", "sensata.kz", "rams-qazaqstan.kz", "rams.kz", "elitestroy.kz", "ordainvest.kz",
         "highvill.kz", "capitalpark.kz", "kazakhstan-construction.kz", "mabetex.kz", "arnau.kz", "qurylysmarket.kz", "dskoncept.kz",
         "nurstroy.kz", "eurasiagroup.kz", "favoritestroy.kz", "atlant-astana.kz", "taimas.kz", "bnes.kz", "alpha-stroy.kz", "verny-capital.kz",
         "smartstroy.kz", "kapitalstroy.kz", "cbb.kz", "km-construction.kz", "aqsai.kz", "basis-group.kz"]
os.makedirs("zp", exist_ok=True)
log = open("zp/log.txt", "w")
def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (JoldaMapBot; +https://joldataxi.kz)"}), timeout=25, context=ctx)
    return r.geturl(), r.read()
for s in SITES:
    for path in ["/", "/robots.txt", "/sitemap.xml"]:
        u = "https://" + s + path
        try:
            fu, b = get(u)
            fn = "zp/" + re.sub(r"[^a-z0-9.]+", "_", s + path)
            open(fn, "wb").write(b[:3_000_000])
            log.write(f"OK {u} -> {fu} {len(b)}\n")
        except Exception as e:
            log.write(f"ERR {u} {str(e)[:120]}\n")
        log.flush()
log.close()
with tarfile.open("zhk_probe.tgz", "w:gz") as t: t.add("zp")
