# Подбор голоса и ударения «Жолда» (edge-tts)
import asyncio, os, edge_tts
G = "Добро пожаловать в такси {}! Пожалуйста, пристегните ремень безопасности. Приятной поездки!"
B = "Мы приехали. Спасибо, что выбрали {}! Не забудьте свои вещи. Хорошего дня!"
async def main():
    os.makedirs("vt", exist_ok=True)
    vs = await edge_tts.list_voices()
    print([v["ShortName"] for v in vs if v["Locale"].startswith("ru")])
    for name, w, wb in [("a", "Жолда", "Жолду"), ("b", "Жолдá", "Жолдý"), ("c", "Жол дá", "Жол дý"), ("d", "Жалдá", "Жалдý")]:
        for k, t in [("g", G.format(w)), ("b", B.format(wb))]:
            for a in range(4):
                try:
                    await edge_tts.Communicate(t, "ru-RU-SvetlanaNeural", rate="+30%", pitch="+30Hz").save(f"vt/{name}_{k}.mp3"); break
                except Exception as e:
                    print("retry", e); await asyncio.sleep(3)
asyncio.run(main())
