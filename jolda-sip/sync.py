#!/usr/bin/env python3
"""Берёт из Jolda линии парка (GoIP и диспетчеры) и пишет их в Asterisk. Новый диспетчер в «Сотрудниках» получает линию за минуту."""
import json, os, subprocess, time, urllib.request

E = os.environ.get
CONF = E("JCONF", "/etc/jolda-tel.conf")
ETC = E("JETC", "/etc/asterisk")


def conf():
    c = {"URL": "https://joldataxi.kz", "KEY": ""}
    for ln in open(CONF, encoding="utf-8"):
        if "=" in ln and not ln.startswith("#"):
            k, v = ln.strip().split("=", 1)
            c[k] = v
    return c


def build(d):
    p = ["; создано sync.py из Jolda — не править руками"]
    for g in d["goip"]:
        u = g["user"]
        p += ["[%s](goip)" % u, "auth=%s" % u, "aors=%s" % u, "[%s](goip-aor)" % u,
              "[%s]" % u, "type=auth", "auth_type=userpass", "username=%s" % u, "password=%s" % g["pass"], ""]
    for x in d["disp"]:
        e = x["ext"]
        p += ["[%s](disp)" % e, "auth=%s" % e, "aors=%s" % e, "[%s](disp-aor)" % e,
              "[%s]" % e, "type=auth", "auth_type=userpass", "username=%s" % e, "password=%s" % x["pass"], ""]
    dial = "&".join("PJSIP/%s" % x["ext"] for x in d["disp"])
    e = ["; создано sync.py из Jolda", "[from-goip]",
         "exten => _X.,1,Goto(in,1)", "exten => s,1,Goto(in,1)",
         "exten => in,1,NoOp(Входящий ${CALLERID(num)})",
         " same => n,Dial(%s,40)" % dial, " same => n,Hangup()", ""]
    return "\n".join(p) + "\n", "\n".join(e) + "\n"


def write_if_changed(path, text):
    try:
        if open(path, encoding="utf-8").read() == text:
            return False
    except OSError:
        pass
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, 0o640)
    os.replace(tmp, path)
    return True


def once(c):
    r = urllib.request.Request(c["URL"].rstrip("/") + "/api/tel/lines", headers={"x-tel-key": c["KEY"], "user-agent": "jolda-sip/1"})
    d = json.loads(urllib.request.urlopen(r, timeout=30).read().decode())
    pj, ex = build(d)
    a = write_if_changed(os.path.join(ETC, "pjsip_jolda.conf"), pj)
    b = write_if_changed(os.path.join(ETC, "extensions_jolda.conf"), ex)
    if a:
        subprocess.run(["asterisk", "-rx", "module reload res_pjsip.so"], capture_output=True)
    if b:
        subprocess.run(["asterisk", "-rx", "dialplan reload"], capture_output=True)
    return a or b


if __name__ == "__main__":
    c = conf()
    import sys
    if "--once" in sys.argv:
        print("изменено" if once(c) else "без изменений")
        raise SystemExit
    while True:
        try:
            if once(c):
                print("линии обновлены", flush=True)
        except Exception as e:
            print("ошибка", e, flush=True)
        time.sleep(45)
