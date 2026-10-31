# Проверка ударения в слове «Жолда» у голосов Microsoft (edge-tts)
import asyncio, os, edge_tts
V = {
 "w1": "Жолда.", "w2": "Жалда.", "w3": "Жалдаа.", "w4": "Жол-да.", "w5": "Жолдá.", "w6": "Жолда\u0301.", "w7": "Жалд+а.", "w8": "Жол дá.", "w9": "Жолдааа.", "w10": "Джолда.", "w11": "такси Жалдаа.", "w12": "Жалда́!",
}
async def main():
    os.makedirs("vt", exist_ok=True)
    for v in ["ru-RU-SvetlanaNeural", "ru-RU-DmitryNeural"]:
        for k, t in V.items():
            for a in range(4):
                try:
                    await edge_tts.Communicate(t, v).save(f"vt/{v[6:9]}_{k}.mp3"); break
                except Exception as e:
                    print("retry", v, e); await asyncio.sleep(3)
asyncio.run(main())
