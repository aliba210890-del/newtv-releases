"""Свои каналы New TV (ntv_channels.json): убирает ролики, которые нельзя показать в приложении
(удалены, не публичные, встраивание запрещено, закрыты в Казахстане/Германии). Ключ — YOUTUBE_API_KEY."""
import json, sys
from karaoke_check import playable

def main(path, report):
    d = json.load(open(path, encoding="utf-8"))
    try:  # канал «Караоке» = по одному (уже проверенному) ролику на каждую песню из караоке
        k = json.load(open("karaoke.json", encoding="utf-8"))
        for c in d["channels"]:
            if c["id"] == "kar": c["ids"] = [s["ids"][0] for s in k["songs"] if s.get("ids")]
    except Exception as e: print("караоке:", e)
    ids = sorted({i for c in d["channels"] for i in c["ids"]})
    st = playable(ids)
    lines = [f"Свои каналы: роликов {len(ids)}, не подходят: {sum(1 for i in ids if st.get(i))}"]
    for c in d["channels"]:
        before = len(c["ids"])
        c["ids"] = [i for i in c["ids"] if not st.get(i)]
        lines.append(f"{c['name']}: было {before}, осталось {len(c['ids'])}")
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    open(report, "a", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))

if __name__ == "__main__":
    main(*sys.argv[1:3])
