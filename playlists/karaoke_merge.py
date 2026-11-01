"""Каталог по исполнителям (karaoke_draft_clean.json) → в рабочий karaoke.json. Остальные песни остаются как были."""
import json, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
from karaoke_clean import fold
cur = json.load(open("playlists/karaoke.json", encoding="utf-8"))
new = json.load(open("playlists/karaoke_draft_clean.json", encoding="utf-8"))
arts = {s["a"] for s in new["songs"]}
keys = {fold(s["a"] + s["t"]) for s in new["songs"]}
out = [dict(s) for s in new["songs"]] + [s for s in cur["songs"] if s["a"] not in arts and fold(s["a"] + s["t"]) not in keys]
if len(out) != len(cur["songs"]) or any(a != b for a, b in zip(out, cur["songs"])):
    cur["songs"] = out; cur["v"] = int(cur.get("v", 1)) + 1
    json.dump(cur, open("playlists/karaoke.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("песен:", len(out))
