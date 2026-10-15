"""Шифрует плейлист для сервера New TV, чтобы в открытом репозитории не лежал читаемый список.

Использование: python encrypt.py <плейлист.m3u> <выход.enc> [адрес сервера]

Открытый ключ берётся с сервера (/api/pubkey); расшифровать файл может только сервер.
Файл перешифровывается, только если плейлист изменился (сравнивается хеш),
чтобы репозиторий не рос от одинаковых обновлений.
"""
import base64
import gzip
import hashlib
import json
import os
import sys
import urllib.request

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

API = "https://newtv-api.aliba210890.workers.dev"


def main(src, dst, api=API):
    data = open(src, "rb").read()
    h = hashlib.sha256(data).hexdigest()
    n = data.count(b"#EXTINF")
    try:
        old = json.load(open(dst, encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    req = urllib.request.Request(api + "/api/pubkey", headers={"User-Agent": "newtv-playlist-bot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        pk = json.load(r)
    if old.get("h") == h and old.get("kid") == pk["kid"]:
        print(dst, "без изменений")
        return
    pub = serialization.load_der_public_key(base64.b64decode(pk["spki"]))
    key = AESGCM.generate_key(bit_length=256)
    iv = os.urandom(12)
    ct = AESGCM(key).encrypt(iv, gzip.compress(data, 9, mtime=0), None)
    wk = pub.encrypt(key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    out = {"v": 1, "kid": pk["kid"], "h": h, "n": n,
           "k": base64.b64encode(wk).decode(), "iv": base64.b64encode(iv).decode(), "d": base64.b64encode(ct).decode()}
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print(dst, "зашифрован:", n, "записей,", len(ct), "байт")


if __name__ == "__main__":
    main(*sys.argv[1:])
