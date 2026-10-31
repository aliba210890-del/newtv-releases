# Слово «Жолда» отдельно в разных написаниях (edge-tts, голос как в приложении)
import asyncio, os, edge_tts
async def main():
    os.makedirs("vt", exist_ok=True)
    for name, w in [("1", "Жолдá."), ("2", "Жол дá."), ("3", "Жалдá."), ("4", "Жолдаа."), ("5", "Жал-дааа.")]:
        for a in range(4):
            try:
                await edge_tts.Communicate("Такси " + w + " Такси " + w, "ru-RU-SvetlanaNeural", rate="+10%", pitch="+30Hz").save(f"vt/w{name}.mp3"); break
            except Exception as e:
                print("retry", e); await asyncio.sleep(3)
asyncio.run(main())
