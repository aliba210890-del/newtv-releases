# Русские фразы Жолды с правильным ударением (ЖолдА пишем как «Жолдаа»), голос как во всём русском наборе
import asyncio, os, edge_tts
W = "Жолдаа"
T = {
 "greet_start": f"Добро пожаловать в такси {W}! Пожалуйста, пристегните ремень безопасности. Приятной поездки!",
 "bye_day": f"Мы приехали. Спасибо, что выбрали такси {W}! Не забудьте свои вещи. Хорошего дня!",
 "bye_eve": f"Мы приехали. Спасибо, что выбрали такси {W}! Не забудьте свои вещи. Хорошего вечера!",
 "bye_night": f"Мы приехали. Спасибо, что выбрали такси {W}! Не забудьте свои вещи. Доброй ночи!",
 "preview": f"Здравствуйте! Я голос навигатора {W}.",
}
async def main():
    os.makedirs("vt", exist_ok=True)
    for k, t in T.items():
        for a in range(5):
            try:
                await edge_tts.Communicate(t, "ru-RU-SvetlanaNeural", rate="+30%", pitch="+30Hz").save(f"vt/ru_{k}.mp3"); break
            except Exception as e:
                print("retry", e); await asyncio.sleep(3)
asyncio.run(main())
