# Слой карты «все дома»: контуры зданий (Microsoft через Overture), которых нет в OSM, + номера домов из регистра
import duckdb, subprocess, re, json, gzip
rels = subprocess.run(["aws", "s3", "ls", "--no-sign-request", "s3://overturemaps-us-west-2/release/"], capture_output=True, text=True).stdout
rel = sorted(re.findall(r"PRE (\d{4}-\d{2}-\d{2}[^/]*)/", rels))[-1]
W, S, E, N = 70.20, 50.45, 72.70, 51.90
con = duckdb.connect(); con.execute("INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2'; SET geometry_always_xy = true;")
q = f"""SELECT ST_AsGeoJSON(geometry) g FROM read_parquet('s3://overturemaps-us-west-2/release/{rel}/theme=buildings/type=building/*', hive_partitioning=1)
WHERE bbox.xmin > {W} AND bbox.xmax < {E} AND bbox.ymin > {S} AND bbox.ymax < {N} AND sources[1].dataset <> 'OpenStreetMap'"""
n = 0
with open("bld.geojsonseq", "w") as f:
    for (g,) in con.execute(q).fetchall():
        f.write(json.dumps({"type": "Feature", "properties": {}, "geometry": json.loads(g)}) + "\n"); n += 1
print("buildings", n)
P = json.load(gzip.open("astana-places.json.gz", "rt")); m = 0
with open("hn.geojsonseq", "w") as f:
    for a in P["addr"]:
        if len(a) > 4 and a[4] == 1:
            f.write(json.dumps({"type": "Feature", "properties": {"housenumber": a[1]}, "geometry": {"type": "Point", "coordinates": [a[3], a[2]]}}, ensure_ascii=False) + "\n"); m += 1
print("housenumbers", m)
