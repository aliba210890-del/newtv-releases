# Проверка ударения в слове «Жолда» у голосов Microsoft (edge-tts)
import asyncio, os, edge_tts
A = "́"
T = {
 "plain": "Жолда.",
 "acc": "Жолда" + A + ".",
 "zhal": "Жалда" + A + ".",
 "greet_plain": "Добро пожаловать в такси Жолда! Пожалуйста, пристегните ремень безопасности. Приятной поездки!",
 "bye_plain": "Мы приехали. Спасибо, что выбрали Жолду! Не забудьте свои вещи. Хорошего дня!",
}
async def main():
    os.makedirs("vt", exist_ok=True)
    for v in ["ru-RU-SvetlanaNeural", "ru-RU-DariyaNeural"]:
        for k, t in T.items():
            for a in range(4):
                try:
                    await edge_tts.Communicate(t, v, rate="-4%").save(f"vt/{v[6:9]}_{k}.mp3"); break
                except Exception as e:
                    print("retry", e); await asyncio.sleep(3)
    for v in ["en-GB-SoniaNeural", "en-US-AriaNeural"]:
        for k, t in {"en_plain": "Zholda.", "en_dah": "Zhol-dah.", "en_greet": "Welcome to Zholda taxi!"}.items():
            try: await edge_tts.Communicate(t, v).save(f"vt/{v[6:9]}_{k}.mp3")
            except Exception as e: print(e)
asyncio.run(main())
