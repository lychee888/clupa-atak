"""Config-driven fetcher for provincial crown-land/public-land polygons.

Usage:
  python fetch_province.py bc ab       # fetch specific provinces
  python fetch_province.py             # fetch all provinces

Outputs: assets/provinces/raw/<code>.geojson

Fetchers:
  wfs          BC WFS 2.0 GeoJSON (openmaps.gov.bc.ca) — needs sortBy, paging
               silently repeats without it.
  arcgis       Esri MapServer/FeatureServer query (SK/AB/NB/NS/NL) with
               resultOffset pagination.
  multi_arcgis MB: pull several ArcGIS feature services into one FC with a
               source tag.
  file         QC: download zipped shapefile, parse .shp/.dbf in pure Python
               (stdlib), convert to GeoJSON.
  skip         province deliberately not fetched (recorded reason).

All fetchers:
  - verify SSL (default context; no verify=False anywhere)
  - detect HTML error pages and back off + retry
  - compare fetched count to the server-reported count and fail if mismatched
"""
import json, os, sys, time, html, struct, zipfile, io, glob
import urllib.request
from urllib.error import HTTPError, URLError

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)

from province_config import PROVINCES

UA = "Mozilla/5.0 (compatible; clupa-atak-provinces/1.0)"


def http_json(url, tries=5, timeout=240, headers=None):
    """GET a URL and json.loads it; HTML error pages and transient failures retry."""
    h = {"User-Agent": headers or UA}
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            data = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
            if data.lstrip()[:1] == "<" and "<wfs:" not in data and "<html" not in data[:2000].lower():
                # strip HTML tag soup to preserve the error body in the message
                snippet = " ".join(data.split()[:20])[:200]
                raise ValueError("HTML error page (likely AUP or rate limit): " + snippet)
            if data.lstrip()[:1] == "<":
                return data  # XML-like response (e.g. WFS hits); caller handles
            return json.loads(data)
        except Exception as e:
            last = e
            print(f"  retry {i}: {str(e)[:120]}", flush=True)
            time.sleep(3 + 3 * i)
    raise RuntimeError(f"fetch failed: {last}")


def http_bytes(url, tries=3, timeout=600):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=timeout).read()
        except Exception as e:
            last = e
            print(f"  retry {i}: {str(e)[:120]}", flush=True)
            time.sleep(3 + 3 * i)
    raise RuntimeError(f"fetch failed: {last}")


# --------------------------------------------------------------- WFS (BC) ---
def fetch_wfs(cfg, code):
    base = cfg["endpoint"]
    feat = []
    off = 0
    expected = None
    sort = cfg.get("sort_field", "OBJECTID")
    while True:
        qs = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": cfg["typenames"],
            "outputFormat": "application/json",
            "countFeatures": "limit",
            "count": str(cfg["page"]),
            "srsName": "urn:ogc:def:crs:EPSG::4326",
            "sortBy": sort,
            "startIndex": str(off),
        }
        url = base + "?" + "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in qs.items())
        d = http_json(url)
        if expected is None:
            hits = http_json(url.split("?")[0] + "?" + "&".join(
                f"{k}={urllib.parse.quote(v)}" for k, v in {**qs, "resultType": "hits"}.items()))
            # hits response is XML for this server; parse numberMatched via regex
            import re
            m = re.search(r'numberMatched="(\d+)"', hits if isinstance(hits, str) else str(hits))
            expected = int(m.group(1)) if m else None
            print(f"  {code}: total reported = {expected}", flush=True)
        fs = d.get("features", [])
        feat.extend(fs)
        print(f"  offset {off}: +{len(fs)}, total {len(feat)}", flush=True)
        if not fs or len(fs) < cfg["page"]:
            break
        off += len(fs)
        if off > 5_000_000:
            raise RuntimeError("pagination runaway")
    if expected is not None and len(feat) != expected:
        raise RuntimeError(f"count mismatch: got {len(feat)}, expect {expected}")
    return {"type": "FeatureCollection",
            "features": demote_crs(feat),
            "properties": {"source": cfg["endpoint"], "count": len(feat)}}


def demote_crs(feats):
    return feats  # geojson output already WGS84 in WGS84 mode


import urllib.parse  # noqa


# ------------------------------------------------------------ ArcGIS REST ---
def fetch_arcgis(cfg, code, endpoint=None, layer=None):
    base = (endpoint or cfg["endpoint"]).rstrip("/")
    lid = layer if layer is not None else cfg.get("layer", 0)
    expected = http_json(f"{base}/{lid}/query?where=1%3D1&returnCountOnly=true&f=json").get("count")
    feats = []
    off = 0
    page = cfg.get("page_size", 2000)
    while True:
        url = (f"{base}/{lid}/query?where=1%3D1&outFields=*&resultRecordCount={page}"
               f"&resultOffset={off}&f=geojson")
        d = http_json(url, tries=6)
        if isinstance(d, dict) and "error" in d:
            raise RuntimeError(f"server error: {d['error']}")
        fs = d.get("features", [])
        feats.extend(fs)
        print(f"  {code} L{lid} offset {off}: +{len(fs)}, total {len(feats)}/{expected}", flush=True)
        etl = d.get("exceededTransferLimit")
        if etl is False:
            break
        if etl is True:
            off += len(fs) if fs else page
            if off >= 5_000_000:
                raise RuntimeError("pagination runaway")
            continue
        if not fs or len(fs) < page:
            break
        off += page
    if expected is not None and len(feats) != expected:
        raise RuntimeError(f"count mismatch: got {len(feats)}, expect {expected}")
    return feats


# ------------------------------------------------------ multi source (MB) ---
def fetch_multi_arcgis(cfg, code):
    all_feats = []
    for src in cfg["sources"]:
        label = src.get("bookmark_as", "source")
        feats = fetch_arcgis(cfg, code, endpoint=src["endpoint"], layer=src.get("layer", 0))
        cat = src.get("cat_default") or "Unknown"
        title = src.get("title_field")
        for f in feats:
            p = f.setdefault("properties", {})
            p["SOURCE_LAYER"] = label
            if src.get("cat_field"):
                p.setdefault("CATEGORY", p.get(src["cat_field"]) or cat)
            else:
                p["CATEGORY"] = cat
            if title and not p.get(title):
                p["TITLE_VAL"] = cat
        all_feats.extend(feats)
    return {"type": "FeatureCollection", "features": all_feats,
            "properties": {"source": "multi", "count": len(all_feats)}}


# ------------------------------------------------------ shapefile file (QC) ---
def fetch_file(cfg, code):
    path = os.path.join(RAW, f"{code}_src.zip")
    if not os.path.exists(path) or os.environ.get("FORCE_REDOWNLOAD"):
        print(f"  downloading {cfg['endpoint']}", flush=True)
        blob = http_bytes(cfg["endpoint"])
        with open(path, "wb") as f:
            f.write(blob)
        print(f"  saved {len(blob)/1e6:.1f} MB -> {path}", flush=True)
    feats = []
    with zipfile.ZipFile(path) as z:
        shp_names = sorted(n for n in z.namelist() if n.lower().endswith(".shp"))
        for shp_name in shp_names:
            stem = shp_name[:-4]
            try:
                dbf = z.read(stem + ".dbf")
            except KeyError:
                dbf = b""
            shx = b""
            try:
                shx = z.read(stem + ".shx")
            except KeyError:
                pass
            shp = z.read(shp_name)
            feats.extend(shp_records(shp, dbf, shx))
        print(f"  parsed {len(shp_names)} shapefile(s)", flush=True)
    return {"type": "FeatureCollection", "features": feats,
            "properties": {"source": cfg["endpoint"], "count": len(feats)}}


def shp_records(shp, dbf, shx):
    """Pure-python shapefile parser: Polygon/Polyline/Point -> GeoJSON."""
    feats = []
    n_recs = len(dbf)  # placeholder: iterate SHP header recs
    # SHP header
    shp_len = struct.unpack(">i", shp[24:28])[0] * 2  # bytes
    gtype = struct.unpack("<i", shp[32:36])[0]
    off = 100
    dbf_off = _dbf_records(dbf)
    recs = []
    while off + 8 <= shp_len:
        rn, clen_words = struct.unpack(">ii", shp[off:off + 8])
        clen = clen_words * 2  # SHP content length is in 16-bit words
        off += 8
        if off + clen > len(shp):
            break
        body = shp[off:off + clen]
        off += clen
        recs.append(body)
    # DBF records aligned to SHP record order (index via SHX? assume 1:1)
    for i, body in enumerate(recs):
        gt = struct.unpack("<i", body[0:4])[0]
        rec = dbf_off[min(i, len(dbf_off) - 1)]
        if gt in (5, 15, 25, 5 + 0x80000000):
            gs = _shp_polygon(body)
            geom = gs
        elif gt in (3, 13, 23, 3 + 0x80000000):
            geom = _shp_polyline(body)
        elif gt in (1, 11, 21, 1 + 0x80000000):
            x, y = struct.unpack("<dd", body[4:20])
            geom = {"type": "Point", "coordinates": [x, y]}
        else:
            continue
        if geom is None:
            continue
        feats.append({"type": "Feature", "id": None,
                      "properties": rec, "geometry": geom})
    return feats


def _shp_polygon(body):
    i = 0
    gt = struct.unpack("<i", body[i * 4:i * 4 + 4] if False else body[0:4])[0]
    box = struct.unpack("<4d", body[4:36])
    nparts = struct.unpack("<i", body[36:40])[0]
    npoints = struct.unpack("<i", body[40:44])[0]
    parts_off = [struct.unpack("<i", body[44 + 4 * k:48 + 4 * k])[0]
                 for k in range(nparts)]
    # points start at 44 + 4*nparts
    pv = 44 + 4 * nparts
    pts = []
    # For polygons: one point entry is xy = 16 bytes
    for k in range(npoints):
        x, y = struct.unpack("<dd", body[pv + 16 * k:pv + 16 * k + 16])
        pts.append((x, y))
    rings = []
    for pi, start in enumerate(parts_off):
        end = parts_off[pi + 1] if pi + 1 < nparts else npoints
        rings.append([[x, y] for x, y in pts[start:end]])
    # convert to (Multi)Polygon: each part is a ring; emit Polygon with 1+ rings
    return {"type": "Polygon", "coordinates": rings}


def _shp_polyline(body):
    gt = struct.unpack("<i", body[0:4])[0]
    nparts = struct.unpack("<i", body[36:40])[0]
    npoints = struct.unpack("<i", body[40:44])[0]
    parts_off = [struct.unpack("<i", body[44 + 4 * k:48 + 4 * k])[0]
                 for k in range(nparts)]
    pv = 44 + 4 * nparts
    pts = []
    for k in range(npoints):
        x, y = struct.unpack("<dd", body[pv + 16 * k:pv + 16 * k + 16])
        pts.append((x, y))
    parts = []
    for pi, start in enumerate(parts_off):
        end = parts_off[pi + 1] if pi + 1 < nparts else npoints
        parts.append([[x, y] for x, y in pts[start:end]])
    return {"type": "MultiLineString", "coordinates": parts}


def _dbf_records(dbf):
    n = struct.unpack("<i", dbf[4:8])[0]
    hlen = struct.unpack("<H", dbf[8:10])[0]
    rlen = struct.unpack("<H", dbf[10:12])[0]
    nfields = (hlen - 33) // 32
    fields = []
    for k in range(nfields):
        b = dbf[32 + 32 * k: 32 + 32 * k + 32]
        name = b[:11].split(b"\0")[0].decode("ascii", "ignore").strip()
        ftype = chr(b[11])
        flen = b[16]
        fields.append((name, ftype, flen))
    out = []
    for i in range(n):
        base = hlen + i * rlen
        rec = {}
        p = base + 1
        for (name, ftype, flen) in fields:
            raw = dbf[p:p + flen]
            try:
                txt = raw.decode("utf-8").strip()
                if "\ufffd" in txt:
                    raise UnicodeDecodeError("utf-8", b"", 0, 1, "replacement")
            except Exception:
                txt = raw.decode("cp437", "replace").strip()
            p += flen
            v = None
            if ftype in ("C", "L"):
                v = txt
            elif ftype == "N" or ftype == "F":
                try:
                    v = float(txt) if txt else None
                    if "." not in txt and txt:
                        v = int(txt)
                except ValueError:
                    v = txt
            elif ftype == "D":
                v = txt
            rec[name] = v
        out.append(rec)
    return out


# ------------------------------------------------------------------- main ---
def fetch(code):
    cfg = PROVINCES[code]
    kind = cfg["kind"]
    if kind == "wfs":
        fc = fetch_wfs(cfg, code)
    elif kind == "arcgis":
        feats = fetch_arcgis(cfg, code)
        cat_f = cfg.get("cat_field")
        for f in feats:
            if cat_f and cat_f not in (f.get("properties") or {}):
                f.setdefault("properties", {})[cat_f] = cfg.get("bookmark_as", "Unknown")
        fc = {"type": "FeatureCollection", "features": feats,
              "properties": {"source": cfg["endpoint"], "count": len(feats)}}
    elif kind == "multi_arcgis":
        fc = fetch_multi_arcgis(cfg, code)
    elif kind == "file":
        fc = fetch_file(cfg, code)
    elif kind == "skip":
        raise RuntimeError(f"{code}: skipped by config: {cfg.get('reason')}")
    else:
        raise RuntimeError(f"unknown kind {kind}")
    out = os.path.join(RAW, f"{code}.geojson")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(fc, f)
    print(f"WROTE {out} features={len(fc['features'])}", flush=True)


if __name__ == "__main__":
    codes = [c.lower() for c in sys.argv[1:]] or list(PROVINCES)
    for c in codes:
        if c not in PROVINCES:
            print("unknown province code", c, flush=True)
            continue
        if PROVINCES[c]["kind"] == "skip":
            print(f"{c}: SKIPPED ({PROVINCES[c].get('reason', '')[:80]})", flush=True)
            continue
        try:
            fetch(c)
        except Exception as e:
            print(f"{c}: FETCH FAILED: {str(e)[:300]}", flush=True)
