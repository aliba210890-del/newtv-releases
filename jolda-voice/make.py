# Озвучка фраз навигатора Жолда (казахский и английский) голосами Microsoft Neural через edge-tts
import asyncio, sys, edge_tts, os
async def main():
    os.makedirs("out", exist_ok=True)
    for lg in ["kk", "en"]:
        rows = [l.rstrip("\n").split("\t") for l in open(f"jolda-voice/{lg}.tsv", encoding="utf-8") if l.strip()]
        voice = rows[0][1]
        for k, t in rows[1:]:
            for a in range(4):
                try:
                    await edge_tts.Communicate(t, voice, rate="-4%").save(f"out/{lg}_{k}.mp3"); break
                except Exception as e:
                    print("retry", lg, k, e); await asyncio.sleep(3)
            print(lg, k, os.path.getsize(f"out/{lg}_{k}.mp3"))
asyncio.run(main())
