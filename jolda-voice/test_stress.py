# Подбор голоса: какой голос был в старом русском наборе
import asyncio, os, edge_tts
G = "Добро пожаловать в такси Жолда! Пожалуйста, пристегните ремень безопасности. Приятной поездки!"
async def main():
    os.makedirs("vt", exist_ok=True)
    vs = await edge_tts.list_voices()
    open("vt/voices.txt", "w").write("\n".join(v["ShortName"] for v in vs if v["Locale"][:2] in ("ru", "kk", "uk")))
    for v in [v["ShortName"] for v in vs if v["Locale"].startswith("ru")] + ["uk-UA-PolinaNeural", "kk-KZ-AigulNeural"]:
        for tag, rate, pitch in [("n", "+0%", "+0Hz"), ("f", "+30%", "+30Hz")]:
            for a in range(3):
                try:
                    await edge_tts.Communicate(G, v, rate=rate, pitch=pitch).save(f"vt/{v}_{tag}.mp3"); break
                except Exception as e:
                    print("retry", v, e); await asyncio.sleep(2)
asyncio.run(main())
