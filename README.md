# CLUPA for ATAK (Ontario Crown Land Use Policy Areas)

Ready-to-import map data for [ATAK](https://atakwiki.org/) showing Ontario Crown
Land Use Policy Area boundaries from the [Crown Land Use Policy Atlas
(CLUPA)](https://www.ontario.ca/page/crown-land-use-policy-atlas), with optional
per-area policy descriptions (land use intent, permitted uses and guidelines).

Everything is built with Python 3 stdlib only (no pip dependencies) from
Ontario's open ArcGIS REST service. Data remains Crown copyright, Ontario
Ministry of Natural Resources; open-data licensed (see Source & licence).

## Repo layout

```
assets/
  fetch_layer.py           paginated downloader for the LIO open data service
  distill_boundaries.py    trims raw boundary GeoJSON to useful fields
  build_atak_kmz.py        builds the two KMZ products below
dist/                      build outputs (gitignored - regenerate)
  clupa_boundaries.kmz          boundaries only (~65 MB)
  clupa_full_with_descriptions.kmz  boundaries + policy text (~68 MB)
  boundaries.geojson            lean GeoJSON of all 1,261 areas
docs/                      screenshots + imports notes
```

## Quick start (build from source data)

```bash
python assets/fetch_layer.py 5 8 13   # download boundaries + policy layers
python assets/build_atak_kmz.py --descriptions   # full version
python assets/build_atak_kmz.py                  # boundaries-only version
```

Then import into ATAK: **Import Manager > Files > Import from SD card**
(or copy the .kmz onto the device and open it). Both files import the same
way; descriptions are optional extras.

## What you get

- `clupa_boundaries.kmz`: all 1,261 Ontario Crown land use policy area
  polygons, named, with `policy_id` + `designation` as ExtendedData.
  No descriptions.
- `clupa_full_with_descriptions.kmz`: same boundaries, plus a KML
  `<description>` per polygon carrying the atlas policy text:
  land area description, land use intent, permitted uses preface/addendum,
  up to the full list of permitted uses with guidelines
  (1,218 of 1,261 areas have published policy text; the rest are unnamed
  administrative areas with no atlas entry).

## Source & licence

- ArcGIS REST services (same backend as the CLUPA web atlas):
  - Boundaries: `LIO_OPEN_DATA/LIO_Open06/MapServer/5` (CLUPA Provincial)
  - Policy text: `.../8` (CLUPA Policy) + `.../13` (CLUPA Policy + Permitted Use)
  - Overlay: `.../4` (CLUPA Overlay)
- [Ontario GeoHub dataset](https://geohub.lio.gov.on.ca/datasets/c71addd613b94c6bbdad9228d322b161)
- Open Government Licence - Ontario:
  https://www.ontario.ca/page/open-government-licence-ontario
