"""Чистит плейлист фильмов от рекламных заставок автора.

Использование: python clean_films.py <вход.m3u> <выход.m3u>
Убирает записи из группы «🔺 INFO 🔺», записи с «🔺 INFO 🔺» в названии
и ссылки на серверы автора (заставки).
"""
import re
import sys

AD_HOSTS = ("194.26.229.213", "github.com/Dimonovich")
AD_MARK = "🔺 INFO 🔺"


def is_ad(extinf: str, url: str) -> bool:
    group = re.search(r'group-title="([^"]*)"', extinf)
    if group and AD_MARK in group.group(1):
        return True
    name = extinf.rsplit(",", 1)[-1]
    if AD_MARK in name:
        return True
    return any(h in url for h in AD_HOSTS)


def main(src: str, dst: str) -> None:
    with open(src, encoding="utf-8-sig") as f:
        lines = [l.rstrip("\r\n") for l in f]

    out = ["#EXTM3U"]
    kept = removed = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            block = [line]
            j = i + 1
            # собрать служебные строки (#EXTVLCOPT и т.п.) до ссылки
            while j < len(lines) and (not lines[j].strip() or lines[j].startswith("#")):
                if lines[j].startswith("#EXTINF"):
                    break
                if lines[j].strip():
                    block.append(lines[j])
                j += 1
            url = lines[j].strip() if j < len(lines) and not lines[j].startswith("#") else ""
            if url:
                block.append(url)
                j += 1
                if is_ad(line, url):
                    removed += 1
                else:
                    out.extend(block)
                    kept += 1
            i = j
        else:
            i += 1

    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"kept={kept} removed={removed}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
