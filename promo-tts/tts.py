import asyncio, sys, os, json, edge_tts
VOICE = os.environ.get("VOICE", "ru-RU-DmitryNeural"); RATE = os.environ.get("RATE", "+12%")
os.makedirs("out", exist_ok=True)
async def one(i, t):
    try:
        c = edge_tts.Communicate(t, VOICE, rate=RATE, boundary="WordBoundary")
    except TypeError:
        c = edge_tts.Communicate(t, VOICE, rate=RATE)
    words = []
    with open(f"out/{i}.mp3", "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] in ("WordBoundary", "SentenceBoundary"): words.append({"t": ch["offset"] / 1e7, "d": ch["duration"] / 1e7, "w": ch["text"]})
    json.dump(words, open(f"out/{i}.json", "w"), ensure_ascii=False)
async def safe(i, t):
    for k in range(4):
        try: return await one(i, t)
        except Exception as e: print(i, "retry", e); await asyncio.sleep(3)
    raise SystemExit(i + " failed")
async def main():
    for line in open("promo-tts/lines.tsv", encoding="utf-8"):
        if "\t" in line:
            i, t = line.rstrip("\n").split("\t", 1); await safe(i, t)
asyncio.run(main())
