# Дополнительные открытые базы мест для «Жолда» (кроме OpenStreetMap):
#  - Overture Maps Places (CDLA-Permissive-2.0) — свежие организации;
#  - Foursquare Open Source Places (Apache-2.0) — последний публичный выпуск, старые и новые заведения.
# Результат: overture.ndjson и fsq.ndjson (по одной записи на строку) — их сливает build_places.py.
import json, subprocess, sys, os
import duckdb

W, S, E, N = 70.00, 50.20, 72.90, 52.05


def run_overture():
    subprocess.run(["overturemaps", "download", "--bbox=%s,%s,%s,%s" % (W, S, E, N), "-f", "geoparquet", "--type=place", "-o", "overture.parquet"], check=True)
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")
    cols = [r[0] for r in con.execute("DESCRIBE SELECT * FROM 'overture.parquet'").fetchall()]
    print("overture columns:", cols, flush=True)
    has_os = "operating_status" in cols
    has_basic = "basic_category" in cols
    q = """SELECT names.primary AS name, to_json(names) AS names, taxonomy.primary AS cat, to_json(taxonomy.hierarchy) AS alt,
        {basic} AS basic, confidence, {status} AS status,
        ST_Y(ST_Centroid(geometry)) AS lat, ST_X(ST_Centroid(geometry)) AS lng,
        addresses[1].freeform AS addr, phones[1] AS phone, websites[1] AS web, to_json(sources) AS src
        FROM 'overture.parquet'""".format(basic="basic_category" if has_basic else "NULL", status="operating_status" if has_os else "NULL")
    n = 0
    with open("overture.ndjson", "w", encoding="utf-8") as f:
        for row in con.execute(q).fetchall():
            name, names, cat, alt, basic, conf, status, lat, lng, addr, phone, web, src = row
            if not name or lat is None: continue
            f.write(json.dumps({"name": name, "names": json.loads(names) if names else None, "cat": cat, "alt": json.loads(alt) if alt else None, "basic": basic,
                                "conf": conf, "status": status, "lat": lat, "lng": lng, "addr": addr, "phone": phone, "web": web,
                                "src": [s.get("dataset") for s in (json.loads(src) or [])] if src else None}, ensure_ascii=False) + "\n")
            n += 1
    print("overture:", n, flush=True)


def run_fsq():
    # Foursquare убрал старые выпуски из своего бакета; последний публичный выпуск лежит на Source Cooperative
    base = "s3://fused/fsq-os-places/"
    ls = lambda p: subprocess.run(["aws", "s3", "ls", "--no-sign-request", "--endpoint-url", "https://data.source.coop", base + p], capture_output=True, text=True).stdout
    dt = sorted(x.split()[-1].rstrip("/") for x in ls("").splitlines() if x.strip().startswith("PRE"))[-1]
    lst = ls(dt + "/places/")
    print("fsq release:", dt, "\n", lst[:1500], flush=True)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; SET s3_endpoint='data.source.coop'; SET s3_url_style='path'; SET s3_region='us-west-2';")
    src = base + dt + "/places/**/*.parquet"
    cols = [r[0] for r in con.execute("DESCRIBE SELECT * FROM read_parquet('%s') LIMIT 1" % src).fetchall()]
    print("fsq columns:", cols, flush=True)
    q = """SELECT name, latitude, longitude, address, locality, tel, website, date_created, date_refreshed, date_closed, to_json(fsq_category_labels) AS labels
        FROM read_parquet('{src}') WHERE country='KZ' AND latitude BETWEEN {S} AND {N} AND longitude BETWEEN {W} AND {E}""".format(src=src, S=S, N=N, W=W, E=E)
    n = 0
    with open("fsq.ndjson", "w", encoding="utf-8") as f:
        for row in con.execute(q).fetchall():
            name, lat, lng, addr, loc, tel, web, dc, dr, dcl, labels = row
            if not name or lat is None: continue
            f.write(json.dumps({"name": name, "lat": lat, "lng": lng, "addr": addr, "loc": loc, "phone": tel, "web": web, "created": str(dc or ""), "refreshed": str(dr or ""),
                                "closed": str(dcl or ""), "labels": json.loads(labels) if labels else None}, ensure_ascii=False) + "\n")
            n += 1
    print("fsq:", n, flush=True)


if __name__ == "__main__":
    for fn in (run_overture, run_fsq):
        try: fn()
        except Exception as e: print("ОШИБКА", fn.__name__, e, file=sys.stderr, flush=True)
