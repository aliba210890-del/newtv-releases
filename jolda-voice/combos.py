# Голос целыми фразами: «Через 300 метров поверните направо», «Поверните налево, а затем поверните направо» — одной записью, без склейки
import asyncio, os, sys, edge_tts
LG = sys.argv[1]
M = "left right sleft sright hleft hright uturn keepl keepr keeps straight ramp rampl rampr mergel merger ring1 ring2 ring3 ring4 ring5 ringexit".split()
T = "left right sleft sright keepl keepr straight uturn ring1 ring2 ring3".split()
D = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1500, 2000, 3000]
src = "jolda-voice/ru_base.tsv" if LG == "ru" else f"jolda-voice/{LG}.tsv"
rows = [l.rstrip("\n").split("\t") for l in open(src, encoding="utf-8") if l.strip()]
voice = rows[0][1]; B = {k: t for k, t in rows[1:]}
cap = lambda s: s[:1].upper() + s[1:]
low = lambda s: s[:1].lower() + s[1:]
def dist(d, m): return (B["d%d" % d].rstrip(",") + (", " if LG == "en" else " ") + low(B[m])).strip()
def then(a, b):
    a1 = cap(B[a]).rstrip(".")
    if LG == "ru": return a1 + ", а затем " + low(B[b])
    if LG == "kk": return a1 + ", содан кейін " + low(B[b])
    return a1 + ", then " + low(B[b])
J = {}
for d in D:
    for m in M + ["arrive_soon"]: J["c_%d_%s" % (d, m)] = dist(d, m)
for a in T:
    for b in T: J["t_%s_%s" % (a, b)] = then(a, b)
os.makedirs("out", exist_ok=True)
open("out/texts_%s.tsv" % LG, "w", encoding="utf-8").write("\n".join(k + "\t" + v for k, v in J.items()))
# ONLY=c_600_rampl,… — пересобрать только эти фразы (если какая-то не получилась при общей сборке)
if os.environ.get("ONLY"): J = {k: v for k, v in J.items() if k in os.environ["ONLY"].split(",")}
async def one(k, t):
    for a in range(5):
        try: await edge_tts.Communicate(t, voice, rate="-4%").save(f"out/{k}.mp3"); return
        except Exception as e: print("retry", k, e); await asyncio.sleep(3 + a * 3)
async def main():
    sem = asyncio.Semaphore(6)
    async def w(k, t):
        async with sem: await one(k, t)
    await asyncio.gather(*[w(k, t) for k, t in J.items()])
asyncio.run(main())
print(LG, len(J), "фраз")
