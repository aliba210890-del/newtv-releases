#!/usr/bin/env python3
"""Автозвонок клиентам Jolda (как автоинформатор в ESTaxi).

Работает на компьютере парка рядом с Asterisk (WSL Ubuntu). Каждые 3 секунды спрашивает у Jolda,
кому позвонить («за вами выехала машина…», «машина подъехала…»), скачивает готовую озвучку голосом
Jolda (wav 8 кГц) и кладёт звонок в очередь Asterisk. Звонок идёт через симку GoIP (обычно Алтел).

Настройка: /etc/jolda-autocall.conf
  KEY=<ключ парка из Jolda, parks.tel_key>
  LINE=goip2          # линия GoIP с симкой для автозвонков (Алтел)
  URL=https://joldataxi.kz
Запуск как служба: см. telephony/README.md («Автозвонок клиентам»).
"""
import json, os, shutil, time, urllib.request, urllib.error

E = os.environ.get
CONF = E("JCONF", "/etc/jolda-autocall.conf")
AST = E("JAST", "/var")  # для проверки на другом компьютере
SOUNDS = AST + "/lib/asterisk/sounds/jolda"
SPOOL = AST + "/spool/asterisk/outgoing"
DONE_DIR = AST + "/spool/asterisk/outgoing_done"
TMP = AST + "/spool/asterisk/tmp-jolda"


def conf():
    c = {"URL": "https://joldataxi.kz", "LINE": "", "KEY": ""}
    with open(CONF, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                c[k.strip()] = v.strip()
    return c


def req(c, path, body=None, raw=False):
    r = urllib.request.Request(c["URL"].rstrip("/") + path, data=None if body is None else json.dumps(body).encode(),
                               headers={"x-tel-key": c["KEY"], "content-type": "application/json", "user-agent": "jolda-autocall/1"})
    with urllib.request.urlopen(r, timeout=40) as resp:
        d = resp.read()
    return d if raw else json.loads(d.decode())


def dial_number(phone):
    n = "".join(ch for ch in phone if ch.isdigit())
    if len(n) == 11 and n[0] == "7":
        n = "8" + n[1:]
    elif len(n) == 10:
        n = "8" + n
    return n


def place_call(c, job, wav):
    os.makedirs(SOUNDS, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    name = "c%d" % job["id"]
    with open(os.path.join(SOUNDS, name + ".wav"), "wb") as f:
        f.write(wav)
    num = dial_number(job["phone"])
    body = (
        "Channel: PJSIP/%s@%s\n"
        "CallerID: Jolda\n"
        "MaxRetries: 1\nRetryTime: 40\nWaitTime: 35\n"
        "Context: jolda-autocall\nExtension: s\nPriority: 1\n"
        "Setvar: JFILE=%s/%s\n"
        "Setvar: JID=%d\n"
        "Archive: yes\n" % (num, c["LINE"], SOUNDS, name, job["id"])
    )
    # файл пишем во временную папку и переносим целиком: Asterisk не должен прочитать его наполовину
    tmp = os.path.join(TMP, name + ".call")
    with open(tmp, "w") as f:
        f.write(body)
    shutil.move(tmp, os.path.join(SPOOL, name + ".call"))
    return name


def check_done(c, pending):
    """Asterisk кладёт отработанный файл в outgoing_done со строкой Status: Completed/Failed/Expired."""
    for name, (jid, t0) in list(pending.items()):
        path = os.path.join(DONE_DIR, name + ".call")
        status = None
        if os.path.exists(path):
            with open(path, errors="ignore") as f:
                for ln in f:
                    if ln.startswith("Status:"):
                        status = ln.split(":", 1)[1].strip()
            os.remove(path)
        elif time.time() - t0 > 300:
            status = "NoResult"
        if status:
            try:
                req(c, "/api/tel/done", {"id": jid, "ok": status == "Completed", "note": status})
            except Exception as e:
                print("done error", e, flush=True)
            try:
                os.remove(os.path.join(SOUNDS, name + ".wav"))
            except OSError:
                pass
            del pending[name]


def main():
    c = conf()
    if len(c["KEY"]) < 24:
        raise SystemExit("В %s не указан KEY" % CONF)
    fixed = c["LINE"]  # линия из настроек; если пусто — берём ту, что указана в Jolda (parks.tel_line)
    print("Jolda автозвонок запущен", flush=True)
    pending, line_at = {}, 0
    while True:
        try:
            check_done(c, pending)
            if not fixed and time.time() - line_at > 60:
                p = req(c, "/api/tel/ping")
                line_at = time.time()
                if p.get("line") != c["LINE"]:
                    c["LINE"] = p.get("line") or ""
                    print("линия автозвонка:", c["LINE"] or "не задана", flush=True)
                if not p.get("auto"):
                    c["LINE"] = ""
            if not c["LINE"]:
                time.sleep(10)
                continue
            r = req(c, "/api/tel/next")
            job = r.get("job")
            if job:
                wav = req(c, "/api/tel/audio?id=%d" % job["id"], raw=True)
                name = place_call(c, job, wav)
                pending[name] = (job["id"], time.time())
                print("звоним", job["kind"], job["phone"], flush=True)
                continue
            if r.get("again"):
                continue
        except urllib.error.HTTPError as e:
            print("Jolda ответила", e.code, e.read()[:200], flush=True)
            time.sleep(10)
        except Exception as e:
            print("ошибка", e, flush=True)
            time.sleep(10)
        time.sleep(3)


if __name__ == "__main__":
    main()
