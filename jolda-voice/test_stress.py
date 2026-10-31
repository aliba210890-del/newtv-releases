# Проверка: старый русский голос — Google (gTTS)?
from gtts import gTTS
import os
os.makedirs("vt", exist_ok=True)
G = "Добро пожаловать в такси {}! Пожалуйста, пристегните ремень безопасности. Приятной поездки!"
for tag, w in [("plain", "Жолда"), ("acc", "Жолда\u0301"), ("aa", "Жолдаа"), ("plus", "Жолд+а")]:
    try:
        gTTS(G.format(w), lang="ru").save(f"vt/g_{tag}.mp3")
    except Exception as e:
        open(f"vt/g_{tag}.err.txt", "w").write(str(e))
