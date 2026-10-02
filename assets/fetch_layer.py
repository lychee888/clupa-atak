"""Robust paginated downloader for CLUPA ArcGIS layers.

- Geometry-bearing layers use f=geojson; the server chokes on large pages,
  so page size stays small.
- Attribute-only tables are fetched as esri JSON and converted into a
  FeatureCollection with null geometry.
- Pagination continues while the service reports exceededTransferLimit
  (a short page alone is NOT a reliable end signal), and stops on
  feature-count mismatch vs the service count.
- SSL verification is ON (default context). The service presents a valid
  certificate; do not disable verification.
"""
import json, os, sys, time
import urllib.request

BASE = "https://ws.lioservices.lrc.gov.on.ca/arcgis2/rest/services/LIO_OPEN_DATA/LIO_Open06/MapServer"
OUTDIR = os.path.dirname(os.path.abspath(__file__))

GEOMETRY_LAYERS = {5, 4}  # feature layers; all others are attribute tables


def curl(url, tries=5):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=240).read().decode("utf-8", "replace")
            if data.lstrip()[:1] == "<":
                raise ValueError("HTML Application Error page from server")
            return json.loads(data)
        except Exception as e:
            last = e
            print("  retry", i, repr(e)[:100], flush=True)
            time.sleep(3 + 3 * i)
    raise RuntimeError(f"curl failed: {last}")


def esri_table_to_geojson(d):
    feats = []
    for f in d.get("features", []):
        feats.append({"type": "Feature", "id": None, "geometry": None,
                      "properties": f.get("attributes", {})})
    return {"type": "FeatureCollection", "features": feats}


def service_count(layer):
    d = curl(f"{BASE}/{layer}/query?where=1%3D1&returnCountOnly=true&f=json")
    return d.get("count")


def fetch_layer(layer, page=None):
    with_geometry = layer in GEOMETRY_LAYERS
    if page is None:
        page = 100 if with_geometry else 500

    expected = service_count(layer)
    feats = []
    off = 0
    while True:
        url = f"{BASE}/{layer}/query?where=1%3D1&outFields=*&resultRecordCount={page}&resultOffset={off}"
        url += "&returnGeometry=true&f=geojson" if with_geometry else "&returnGeometry=false&f=json"
        d = curl(url)
        if isinstance(d, dict) and "error" in d:
            raise RuntimeError(f"server error: {d['error']}")
        fs = d.get("features", [])
        if not with_geometry:
            fs = esri_table_to_geojson(d)["features"]
        feats.extend(fs)
        print(f"L{layer} off={off} got={len(fs)} total={len(feats)} "
              f"(exceededTransferLimit={d.get('exceededTransferLimit')})", flush=True)
        etl = d.get("exceededTransferLimit")
        if etl is False:
            break
        if etl is True:
            off += len(fs) if fs else page
            if off >= 4_000_000:  # absurd runaway guard
                raise RuntimeError("pagination runaway")
            continue
        # etl None (older servers): fall back to short-page heuristic
        if not fs or len(fs) < page:
            break
        off += page

    if expected is not None and len(feats) != expected:
        raise RuntimeError(
            f"download incomplete: got {len(feats)}, service reports {expected}")

    fc = {"type": "FeatureCollection", "features": feats}
    with open(os.path.join(OUTDIR, f"layer{layer}.geojson"), "w", encoding="utf-8") as f:
        json.dump(fc, f)
    print(f"WROTE layer{layer}.geojson features={len(feats)} (service count={expected})", flush=True)
    return len(feats)


if __name__ == "__main__":
    layers = [int(x) for x in sys.argv[1:]] or [5]
    for L in layers:
        n = fetch_layer(L)
        print(f"DONE layer {L}: {n}", flush=True)
