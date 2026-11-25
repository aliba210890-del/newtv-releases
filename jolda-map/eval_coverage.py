# Сравнение двух баз по посёлкам вокруг Астаны: сколько домов на крыше/примерно/без точки и насколько сдвинулись
import sys, gzip, json, math, collections
A, B = (json.load(gzip.open(p, "rt")) for p in sys.argv[1:3])
def hav(a, b, c, e):
    p = math.pi / 180
    return 12742 * math.asin(math.sqrt(math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((e - b) * p / 2) ** 2))
V = {"Караоткель (Ильинка)": (51.12304, 71.21277, 3), "Аршалы": (50.83041, 72.18116, 3), "Шортанды": (51.69743, 70.98716, 3), "Талапкер": (51.2409, 71.15571, 2.5),
     "Акмол": (51.07147, 70.98119, 2.5), "Кажымукан": (51.26432, 71.08561, 2.5), "Арайлы": (51.2971, 71.00766, 2.5), "Жалтырколь": (51.06, 71.20, 2.5),
     "Жибек Жолы": (51.0745, 71.7659, 3), "Косшы": (50.97541, 71.35495, 3.5), "Кабанбай батыра": (50.85268, 71.35457, 2.5)}
def stat(D, la, ln, r):
    c = collections.Counter()
    for a in D["addr"]:
        if abs(a[2] - la) < 0.06 and abs(a[3] - ln) < 0.09 and hav(la, ln, a[2], a[3]) < r:
            c[a[4] if len(a) > 4 else 0] += 1
    return c
pa = {(a[0], a[1]): (a[2], a[3]) for a in A["addr"] if len(a) > 4 and a[4] == 1}
moved = collections.defaultdict(list)
for a in B["addr"]:
    if len(a) > 4 and a[4] == 1 and (a[0], a[1]) in pa:
        o = pa[(a[0], a[1])]
        for nm, (la, ln, r) in V.items():
            if hav(la, ln, a[2], a[3]) < r: moved[nm].append(hav(o[0], o[1], a[2], a[3]) * 1000)
print("посёлок | было: точно/примерно/без точки | стало | сдвиг «примерно», медиана м")
for nm, (la, ln, r) in V.items():
    s1, s2 = stat(A, la, ln, r), stat(B, la, ln, r)
    m = sorted(moved[nm]); md = f"{m[len(m)//2]:.0f}" if m else "-"
    print(f"{nm} | {s1[0]}/{s1[1]}/{s1[2]} | {s2[0]}/{s2[1]}/{s2[2]} | {md}")
