# Пробы голосов для Жолда: одна и та же фраза разными голосами
import asyncio, os, edge_tts
os.makedirs("vt", exist_ok=True)
RU = "Добро пожаловать в такси Жолдаа! Пожалуйста, пристегните ремень безопасности. Через триста метров поверните направо. Вы приехали. Спасибо, что выбрали Жолдаа!"
KK = "Жолдаа таксиіне қош келдіңіз! Қауіпсіздік белдігін тағыңыз. Үш жүз метрден кейін оңға бұрылыңыз. Сіз келдіңіз."
async def main():
    vs = await edge_tts.list_voices()
    for v in vs:
        if v["Locale"] in ("ru-RU", "kk-KZ"):
            t = RU if v["Locale"] == "ru-RU" else KK
            for rate in ["-4%", "+4%"]:
                fn = f"vt/{v['ShortName']}_{'slow' if rate[0]=='-' else 'fast'}.mp3"
                try: await edge_tts.Communicate(t, v["ShortName"], rate=rate).save(fn); print(fn, v["Gender"])
                except Exception as e: print("err", fn, e)
asyncio.run(main())
