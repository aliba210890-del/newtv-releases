# Все здания вокруг Астаны из Overture (контуры Microsoft/OSM/Google) → центроиды
import duckdb, subprocess, re, json, gzip, sys
rels = subprocess.run(["aws","s3","ls","--no-sign-request","s3://overturemaps-us-west-2/release/"],capture_output=True,text=True).stdout
rel = sorted(re.findall(r"PRE (\d{4}-\d{2}-\d{2}[^/]*)/", rels))[-1]
print("release", rel)
W,S,E,N = 70.45, 50.60, 72.45, 51.75
con = duckdb.connect(); con.execute("INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
q = f"""SELECT ST_Y(ST_Centroid(geometry)) la, ST_X(ST_Centroid(geometry)) ln, ST_Area_Spheroid(geometry) ar,
  sources[1].dataset src, class, subtype
FROM read_parquet('s3://overturemaps-us-west-2/release/{rel}/theme=buildings/type=building/*', filename=true, hive_partitioning=1)
WHERE bbox.xmin > {W} AND bbox.xmax < {E} AND bbox.ymin > {S} AND bbox.ymax < {N}"""
rows = con.execute(q).fetchall()
print("buildings", len(rows))
from collections import Counter
print(Counter(r[3] for r in rows).most_common())
out = [[round(r[0],6), round(r[1],6), int(r[2] or 0), (r[3] or "")[:1], r[4] or ""] for r in rows]
json.dump({"release": rel, "b": out}, gzip.open("ast-buildings.json.gz","wt"), separators=(",",":"))
# адреса Overture в рамке (если есть)
try:
    a = con.execute(f"""SELECT count(*) FROM read_parquet('s3://overturemaps-us-west-2/release/{rel}/theme=addresses/type=address/*', hive_partitioning=1)
      WHERE bbox.xmin > {W} AND bbox.xmax < {E} AND bbox.ymin > {S} AND bbox.ymax < {N}""").fetchone()
    print("overture addresses", a)
except Exception as e: print("addr err", e)
