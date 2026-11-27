import asyncio, sys, os, json, edge_tts
VOICE = os.environ.get("VOICE", "ru-RU-DmitryNeural"); RATE = os.environ.get("RATE", "+12%")
os.makedirs("out", exist_ok=True)
async def one(i, t):
    c = edge_tts.Communicate(t, VOICE, rate=RATE, pitch="+2Hz")
    words = []
    with open(f"out/{i}.mp3", "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] in ("WordBoundary", "SentenceBoundary"): words.append({"t": ch["offset"] / 1e7, "d": ch["duration"] / 1e7, "w": ch["text"]})
    json.dump(words, open(f"out/{i}.json", "w"), ensure_ascii=False)
async def main():
    for line in open("promo-tts/lines.tsv", encoding="utf-8"):
        if "\t" in line:
            i, t = line.rstrip("\n").split("\t", 1); await one(i, t)
asyncio.run(main())
