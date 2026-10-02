# GitHub hygiene for this repo

- Repo: https://github.com/jarvis959/clupa-atak (create, then push below)
- Do NOT commit `assets/layer*.geojson` (~490 MB raw) or `dist/*.kmz`
  (~67 MB each) - both are gitignored; users regenerate with
  `python assets/fetch_layer.py 5 8 13` then the build scripts.
- Verified endpoint quirks that shaped the code:
  - `ws.lioservices.lrc.gov.on.ca` needs `User-Agent` set (.mozilla/5.0);
    empty UA => HTML "Application Error" page.
  - Layer 5 geojson query crashes server-side above ~50-100 rows/page
    (returns HTML error); page=100 with retry loop is stable.
  - Tables (L8/L13 etc.) must NOT use f=geojson (400 error: "output spatial
    reference is not supported with geoJSON format"); use f=json and
    convert, as fetch_layer.py does.
  - `www.gisapplication.lrc.gov.on.ca` (atlas viewer host) has an expired
    TLS cert and resets curl; do not use that host for data.
- Verified joins for descriptions:
  - boundaries(L5).POLICY_IDENT -> L8.POLICY_IDENT (policy text; 1218/1261 hit)
  - L8.OGF_ID -> L13.CLUPA_POLICY_ID (permitted uses; 857/1261 features)
  - L5.OGF_ID does NOT join to L8.OGF_ID; do not "fix" that.
- Locate data checks: python -m json.tool on any layerN.geojson
- After later feature-adds: full re-run of fetch (5,8,13) + both builds +
  XML parse validation of both KMZs (doc.kml must parse with control chars
  stripped; source data contains \x02 chars in policy text).
