# Русские названия для мест, записанных только по-казахски («Иманжүсіп Құтпанұлы орта мектебі» → «Средняя школа им. Иманжусип Кутпанулы»),
# и одна точка на одно место (в открытых базах школа или садик часто лежит 2–3 раза в 20–100 м друг от друга).
# Казахское название остаётся вариантом для поиска: найдётся и «мектеп», и «школа».
import re, math, sys, gzip, json

KZ_LET = "әғқңөұүһіӘҒҚҢӨҰҮҺІ"
TR = str.maketrans("әғқңөұүһіӘҒҚҢӨҰҮҺІ", "агкноуухиАГКНОУУХИ")
KZ_RE = re.compile(r"[әғқңөұүһіӘҒҚҢӨҰҮҺІ]|(?<![а-яё])(мектеп|мектебі|балабақша|бөбекжай|емхана|дәріхана|аурухана|дүкен|колледжі|мешіт|әкімдігі|кітапхана|орталығы|асхана|саябақ)", re.I)
# ключевое слово → русское; порядок важен (длинные раньше). Шаблон «X слово» → «Слово X»
WORDS = [
    (r"жалпы\s+білім\s+беретін\s+орта\s+мектеп(і|тері)?", "общеобразовательная средняя школа"),
    (r"жалпы\s+білім\s+беретін\s+мектеп(і)?", "общеобразовательная школа"),
    (r"орта\s+мектеп(і|тің)?|орта\s+мектебі", "средняя школа"),
    (r"негізгі\s+мектеп(і)?", "основная школа"),
    (r"бастауыш\s+мектеп(і)?", "начальная школа"),
    (r"мектеп-лицей(і)?", "школа-лицей"),
    (r"мектеп-гимназия(сы)?", "школа-гимназия"),
    (r"мектеп-интернат(ы)?", "школа-интернат"),
    (r"мектеп(і|тің|ке)?|мектебі", "школа"),
    (r"бөбекжай-балабақша(сы)?", "ясли-сад"),
    (r"балабақша(сы|лар)?", "детский сад"),
    (r"бөбекжай(ы)?", "ясли"),
    (r"емхана(сы)?", "поликлиника"),
    (r"аурухана(сы)?", "больница"),
    (r"дәріхана(сы)?|дəріхана|дәіхана", "аптека"),
    (r"мешіт(і)?", "мечеть"),
    (r"колледж(і)?", "колледж"),
    (r"кітапхана(сы)?", "библиотека"),
    (r"әкімдігі", "акимат"),
    (r"әкімінің\s+аппараты", "аппарат акима"),
    (r"мәдениет\s+үйі", "дом культуры"),
    (r"асхана(сы)?", "столовая"),
    (r"саябағы|саябақ", "парк"),
    (r"дүкен(і)?", "магазин"),
    (r"монша(сы)?", "баня"),
    (r"шаштараз(ы)?", "парикмахерская"),
    (r"орталығы", "центр"),
    (r"ауылдық\s+округі", "сельский округ"),
]
PLACE = [(r"ауылдық\s+округ(і|інің)?", "сельского округа"), (r"аудандық", "районный"), (r"ауданы(ның)?", "района"), (r"қаласы(ның)?", "города"), (r"ауылы(ның)?", "села"), (r"ауылдық", "сельская")]
ORD = {"бірінші": "1", "екінші": "2", "үшінші": "3", "төртінші": "4", "бесінші": "5", "алтыншы": "6", "жетінші": "7", "сегізінші": "8", "тоғызыншы": "9", "оныншы": "10"}
FIX = {"Қазақстан": "Казахстан", "Қазақстанның": "Казахстана", "Астана қ.": "Астана"}
HEAD = re.compile(r"^(средняя школа|общеобразовательная( средняя)? школа|основная школа|начальная школа|школа-лицей|школа-гимназия|школа-интернат|школа|ясли-сад|детский сад|ясли|поликлиника|больница|аптека|мечеть|колледж|библиотека|акимат|аппарат акима|дом культуры|столовая|парк|магазин|баня|парикмахерская|центр)$")

def is_kz(name):
    return bool(KZ_RE.search(name))

def ru_name(name):
    """Казахское название → русское. Возвращает None, если менять нечего."""
    s = name.strip()
    # «Городская больница №1 / №1 қалалық аурухана» — берём русскую половину
    if " / " in s:
        parts = [x.strip() for x in s.split(" / ")]
        r = [x for x in parts if not is_kz(x)]
        if r: return r[0] if r[0] != s else None
    if not is_kz(s): return None
    for a, b in FIX.items(): s = s.replace(a, b)
    num = ""
    m = re.search(r"№\s*(\d+[а-яА-Яa-zA-Z]?)", s)
    if m: num = m.group(1)
    for w, d in ORD.items():
        if re.search(r"(?<![а-яёәғқңөұүһі])" + w + r"(?![а-яёәғқңөұүһі])", s, re.I) and not num: num = d; s = re.sub(w, " ", s, flags=re.I)
    m2 = re.match(r"^(\d+)\s+(?=[^\d])", s)  # «12 жалпы білім беретін мектеп»
    city = bool(re.search(r"қалалық", s, re.I))
    if city:
        s = re.sub(r"қалалық", " ", s, flags=re.I)
        m3 = re.search(r"(?<![\d№])(\d+)\s*$|(?<![\d№])\b(\d+)\b", s)
        if m3 and not num: num = m3.group(1) or m3.group(2); s = s.replace(num, " ", 1)
    head, hm = "", None
    for pat, rus in WORDS:
        hm = re.search(r"(?<![а-яёәғқңөұүһі\-])(" + pat + r")(?![а-яёәғқңөұүһі\-])", s, re.I)
        if hm: head = rus; break
    if not head:  # казахских слов-вывесок нет: короткое имя собственное — только буквы; длинное казахское название оставляем как есть
        if len(s.split()) > 3 and re.search(r"(ның|нің|дың|дің|тың|тің|лығы|лігі|сы|сі)(?![а-яёәғқңөұүһі])", s): return None
        out = re.sub(r"\s+", " ", s.translate(TR)).strip()
        return out if out != name else None
    if m and m.group(0) in s: s = s.replace(m.group(0), " ")
    elif m2 and not num: num = m2.group(1); s = s[m2.end():]
    s = re.sub(r"(?<![а-яёәғқңөұүһі\-])(" + [p for p, r in WORDS if r == head][0] + r")(?![а-яёәғқңөұүһі\-])", " ", s, count=1, flags=re.I)
    # «Астана қаласының …», «Жібек жолы ауылының …», «Есіл ауданы …» → в скобки после названия
    where = []
    for pat, kind in [(r"([А-ЯЁӘҒҚҢӨҰҮҺІA-Z][\wәғқңөұүһі\-]*(?:\s+[\wәғқңөұүһі\-]+)?)\s+қаласы(ның)?", "г."), (r"([А-ЯЁӘҒҚҢӨҰҮҺІA-Z][\wәғқңөұүһі\-]*(?:\s+[а-яёәғқңөұүһі\-]+)?)\s+ауылы(ның)?", "с."), (r"([А-ЯЁӘҒҚҢӨҰҮҺІA-Z][\wәғқңөұүһі\-]*)\s+ауданы(ның)?", "р-н"), (r"([А-ЯЁӘҒҚҢӨҰҮҺІA-Z][\wәғқңөұүһі\-]*)\s+ауылдық", "с.")]:
        mm = re.search(pat, s)
        if mm: where.append((kind, mm.group(1).translate(TR))); s = s[:mm.start()] + " " + s[mm.end():]
    for pat, rus in PLACE: s = re.sub(r"(?<![а-яёәғқңөұүһі])(" + pat + r")(?![а-яёәғқңөұүһі])", " ", s, flags=re.I)
    s = re.sub(r"\s*атындағы|\s*атындагы", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip(" ,-–").translate(TR)
    hd = ("городская " + head) if city and head in ("поликлиника", "больница", "библиотека") else head
    h = hd[0].upper() + hd[1:] + ((" №" + num) if num else "")
    rest = s
    if rest:
        qm = re.search(r"[«\"](.+?)[»\"]", rest)
        if rest.lower() == head.lower() or HEAD.match(rest.lower()): rest = ""
        elif qm: rest = "«" + qm.group(1).strip() + "»" + ((" " + rest.replace(qm.group(0), "").strip()) if rest.replace(qm.group(0), "").strip() else "")
        elif re.fullmatch(r"[\d\s]+", rest): pass
        elif re.match(r"^[А-ЯЁ][а-яё\-]+\s+[А-ЯЁ][а-яё\-]+$", rest) and head in ("средняя школа", "школа", "общеобразовательная школа", "общеобразовательная средняя школа", "основная школа", "школа-лицей", "школа-гимназия", "колледж", "библиотека", "дом культуры", "парк"):
            rest = "им. " + rest
        elif head in ("детский сад", "ясли-сад", "ясли", "магазин", "столовая", "аптека", "баня", "парикмахерская"):
            rest = "«" + rest.strip("«»\" ") + "»"
    out = h + ((" " + rest) if rest else "") + "".join(" (" + (w if k in ("г.", "с.") else w + " " + k) + ")" for k, w in where)
    out = re.sub(r"\s+", " ", out).strip()
    if not out or out == name: return None
    return out[0].upper() + out[1:]

def nk(s):
    s = s.lower().replace("ё", "е").translate(TR)
    s = re.sub(r"[«»\"'.,()\-–—/№]", " ", s)
    s = re.sub(r"\b(школа|детский|сад|садик|гимназия|лицей|средняя|общеобразовательная|им|имени|мектеп\w*|балабақша\w*|балабакша\w*|орта|ясли|кгу|гу|коммунальное|государственное|учреждение)\b", " ", s)
    s = s.replace("ы", "и").replace("э", "е").replace("й", "и")
    s = re.sub(r"\s+", " ", s).strip()
    return s

GENERIC = {"детсад": "Детский сад", "садик": "Детский сад", "школа": "Школа", "аптека": "Аптека"}
def localize(pois):
    """pois — список записей [имя, категория, lat, lng, улица, дом, телефон, часы, варианты]. Меняет на месте, возвращает число переименованных."""
    n = 0
    for p in pois:
        if p[1] in ("Улица", "Посёлок", "Город"): continue
        if p[0].strip().lower() in GENERIC: p[0] = GENERIC[p[0].strip().lower()]
        r = ru_name(p[0])
        if not r: continue
        while len(p) < 9: p.append("")
        if p[0] not in str(p[8]): p[8] = (str(p[8]) + " " + p[0]).strip()
        p[0] = r; n += 1
    return n

DEDUP = {"Школа", "Детсад", "Аптека", "Больница", "Поликлиника", "Клиника", "Колледж", "Университет", "Храм/мечеть", "Госучреждение", "Банк", "ТРЦ", "Магазин", "Супермаркет", "Кафе", "Ресторан", "Спорткомплекс", "Баня/сауна", "Отель", "База отдыха", "АЗС", "Стоматология"}

def dedupe(pois, maxm=150):
    pois, a = _dedupe_name(pois, maxm)
    pois, b = _dedupe_spot(pois)
    return pois, a + b

SPOT = {"Школа", "Детсад", "Больница", "Поликлиника", "Колледж", "Храм/мечеть"}
def _dedupe_spot(pois, maxm=8):
    """Школа/садик/мечеть на одной и той же точке под разными именами («Казакская Школа» = «Средняя школа им. …») — одна запись."""
    score = lambda p: (2 if re.search(r"(школа|сад|мечеть|больница|поликлиника|колледж|лицей|гимназия)", p[0], re.I) else 0) * 100 + sum(1 for x in p[4:8] if str(x).strip()) * 10 + len(p[0])
    drop, grid = set(), {}
    order = sorted([i for i, p in enumerate(pois) if p[1] in SPOT], key=lambda i: -score(pois[i]))
    for i in order:
        p = pois[i]; c = (p[1], int(p[2] * 2000), int(p[3] * 1300)); hit = None
        for da in (-1, 0, 1):
            for db in (-1, 0, 1):
                for j in grid.get((p[1], c[1] + da, c[2] + db), ()):
                    q = pois[j]
                    if math.hypot((q[2] - p[2]) * 111320, (q[3] - p[3]) * 70000) < maxm and not (re.search(r"\d", nk(p[0])) and re.search(r"\d", nk(q[0])) and nk(p[0]) != nk(q[0])): hit = j
        if hit is None: grid.setdefault(c, []).append(i); continue
        q = pois[hit]; drop.add(i)
        while len(q) < 9: q.append("")
        q[8] = (str(q[8]) + " " + p[0] + " " + (str(p[8]) if len(p) > 8 else "")).strip()
    return [p for i, p in enumerate(pois) if i not in drop], len(drop)

def _dedupe_name(pois, maxm=150):
    """Одно место — одна точка: та же категория, то же имя (без «школа/мектеп…»), ближе maxm метров. Оставляем запись с адресом/телефоном."""
    by = {}
    for i, p in enumerate(pois):
        if p[1] not in DEDUP: continue
        k = (p[1], nk(p[0]))
        if not k[1]: continue
        by.setdefault(k, []).append(i)
    drop = set()
    score = lambda p: sum(1 for x in p[4:8] if str(x).strip()) * 10 + len(str(p[8]) if len(p) > 8 else "")
    for k, idx in by.items():
        if len(idx) < 2: continue
        idx.sort(key=lambda i: -score(pois[i]))
        kept = []
        for i in idx:
            p = pois[i]
            lim = 450 if p[1] in ("Школа", "Детсад", "Храм/мечеть", "Колледж") else maxm
            q = next((pois[j] for j in kept if math.hypot((pois[j][2] - p[2]) * 111320, (pois[j][3] - p[3]) * 111320 * math.cos(math.radians(p[2]))) < lim), None)
            if q is not None:
                drop.add(i)
                al = (str(p[8]) if len(p) > 8 else "") + " " + p[0]
                while len(q) < 9: q.append("")
                for w in al.split():
                    if w.lower() not in str(q[8]).lower() and w.lower() not in q[0].lower(): q[8] = (str(q[8]) + " " + w).strip()
                continue
            kept.append(i)
    return [p for i, p in enumerate(pois) if i not in drop], len(drop)

if __name__ == "__main__":
    j = json.load(gzip.open(sys.argv[1]))
    n = localize(j["pois"]); j["pois"], d = dedupe(j["pois"])
    print("переименовано", n, "дублей убрано", d)
    with gzip.open(sys.argv[2], "wt", encoding="utf-8") as f: json.dump(j, f, ensure_ascii=False, separators=(",", ":"))
