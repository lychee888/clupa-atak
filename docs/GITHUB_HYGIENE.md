# GitHub hygiene for this repo

- Repo: https://github.com/lychee888/clupa-atak
- Do NOT commit `assets/layer*.geojson` (~490 MB raw) or `dist/*.kmz`
  (~67 MB each) - both are gitignored; users regenerate with
  `python assets/fetch_layer.py 5 8 13` then the build scripts.
- Same rule for provincial data (v1.2): `assets/provinces/raw/*` and in
  particular the ~100 MB Quebec zip are gitignored; regenerate with
  `python assets/provinces/fetch_province.py` then
  `python assets/provinces/build_kmz_province.py`.
- Verified endpoint quirks that shaped the code:

  Ontario (`ws.lioservices.lrc.gov.on.ca`):
  - needs `User-Agent Mozilla/5.0`; empty UA -> HTML "Application Error".
  - layer-5 geojson query crashes server-side above ~50-100 rows/page;
    page=100 with retry loop is stable.
  - tables must NOT use f=geojson (400); use f=json (fetch_layer.py does).
  - `www.gisapplication.lrc.gov.on.ca` has an expired TLS cert; do not use.

  BC (`openmaps.gov.bc.ca`):
  - WFS GeoJSON output needs both `outputFormat=application/json` and the
    special `f=json` param.
  - WITHOUT `sortBy=<field>`, every page repeats the first N rows —
    startIndex is silently ignored for unsorted queries. sortBy=OBJECTID
    + startIndex gives true paging.
  - `resultType=hits` returns XML with numberMatched, not JSON.
  - the server is strict and undocumented; a 400 usually means a
    parameter-name or case error.

  Alberta (`geospatial.alberta.ca`):
  - ArcGIS MapServer; layer indexes 0..6 in `asrd_administrative_area`.
  - geodiscover.alberta.ca's `/geoportal/rest/` metadata pages sometimes
    return 401; go to the MapServer URL directly instead.
  - Altalis DIDs are the paid parcel product and were intentionally NOT
    used - the Green/White Area layer is the free equivalent.

  Saskatchewan (`gis.saskatchewan.ca`):
  - plain ArcGIS; maxRecordCount 2000 + resultOffset paging works.
  - the newer geohub.saskatchewan.ca only exposes Crown Conservation
    Easements; go to the raw ArcGIS server for the real acreage.

  Manitoba (`geoportal.gov.mb.ca`):
  - the geoportal API caps every response at 100 items regardless of the
    limit param, and rejects `offset`; easier to hit the underlying
    ArcGIS feature services directly (Manitoba_Government AGOL org).

  Quebec (`diffusion.mern.gouv.qc.ca`):
  - PATP shapefile ships in EPSG:32198 (NAD83 / Quebec Lambert); convert
    to WGS84 with `qc_lambert.py` before building KML.
  - DBF text fields are CP-437 (DOS Canadian), not UTF-8 and not
    CP-1252; decoding with UTF-8-then-CP-1252 corrupts accented chars.
  - the zip has two shapefiles: `_s` polygons + `_p` points; only `_s`
    is useful for boundary KMZs.

  New Brunswick (`geonb.snb.ca`):
  - ArcGIS MapServer; layer 3 of GeoNB_DNR_Crown_Land.
  - GeoJSON queries at resultRecordCount=2000 intermittently return 500;
    page_size 500 is stable (see `page_size` in province_config.py).

  Nova Scotia (`nsgiwa.novascotia.ca`):
  - plain ArcGIS; works first try.
  - Socrata (`data.novascotia.ca/api/geospatial/...` GeoJSON export) is a
    valid alternative if the ArcGIS host ever changes.

  Newfoundland and Labrador (`gov.nl.ca/landuseatlasmaps`):
  - MapServer behind the Land Use Atlas Web AppBuilder app; layer 3 =
    Crown Titles, layer 11 = Land Use Details, 12+ = Indigenous Areas.
  - maxRecordCount=2000 paging OK; the host is slow under concurrent
    load, use a single-thread fetcher.

- Locate data checks: python -m json.tool on any layerN.geojson
- After later feature-adds: full re-run of fetch (5,8,13) + both builds +
  XML parse validation of both KMZs (doc.kml must parse with control chars
  stripped; source data contains \x02 chars in policy text).
- Every provincial KMZ was validated by xml.etree parse of doc.kml
  (placemarks counted) before packaging; light-variant placemark counts
  differ from full when a polygon's simplified ring drops below 4 points.
