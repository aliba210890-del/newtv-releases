"""Чистит плейлист Dimonovich (фильмы, ТВ) от рекламных заставок автора.

Использование: python clean_playlist.py <вход.m3u> <выход.m3u>
Убирает записи из группы «🔺 INFO 🔺», записи с «🔺 INFO 🔺» в названии
и ссылки на заставки автора. Обычные каналы с его сервера остаются.
Строка #EXTM3U (с адресом программы передач) сохраняется.
"""
import re
import sys

AD_URLS = ("194.26.229.213/zastavka/", "194.26.229.213/intro/", "github.com/Dimonovich/TV/releases/")
AD_MARK = "🔺 INFO 🔺"


def is_ad(extinf: str, url: str) -> bool:
    group = re.search(r'group-title="([^"]*)"', extinf)
    if group and AD_MARK in group.group(1):
        return True
    name = extinf.rsplit(",", 1)[-1]
    if AD_MARK in name:
        return True
    return any(u in url for u in AD_URLS)


def main(src: str, dst: str) -> None:
    with open(src, encoding="utf-8-sig") as f:
        lines = [l.rstrip("\r\n") for l in f]

    header = next((l for l in lines if l.startswith("#EXTM3U")), "#EXTM3U")
    out = [header]
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
