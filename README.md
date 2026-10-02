# CLUPA for ATAK (Ontario Crown Land Use Policy Areas)

Ready-to-import map data for [ATAK](https://atakwiki.org/) showing Ontario
Crown Land Use Policy Area boundaries from the [Crown Land Use Policy Atlas
(CLUPA)](https://www.ontario.ca/page/crown-land-use-policy-atlas), with
optional per-area policy descriptions (land use intent, permitted uses and
guidelines).

Everything is built with Python 3 stdlib only (no pip dependencies) from
Ontario's open ArcGIS REST service. Data remains Crown copyright, Ontario
Ministry of Natural Resources; open-data licensed (see Source & licence).

## Import into ATAK (no build needed)

Most users: just download a pre-built file from the
[releases page](https://github.com/lychee888/clupa-atak/releases/latest) and
import it. Nothing to compile or run.

1. Download the .kmz to your device (copy to SD card or internal storage).
2. In ATAK: **Import Manager > Files > Import from SD card**
   (or just open/click the file).
3. Pick which one:
   - **`clupa_light.kmz`** (2.6 MB): the four designations people actually
     use (General Use Area, Enhanced Management Area, Provincial Park,
     Conservation Reserve) with boundaries generalized to ~100 m. 1,135
     areas. Imports in seconds and renders smoothly on any phone.
     Recommended for most users.
   - **`clupa_boundaries.kmz`** (67 MB): all 1,261 Crown land use area
     boundary polygons, named, with land use designation, full survey
     detail. Use when you need every designation category or
     survey-grade edges.
   - **`clupa_full_with_descriptions.kmz`** (70 MB): same as above plus the
     full policy text per area (land use intent, permitted uses with
     guidelines). Tap a polygon in ATAK to read its policy. Only pick this
     if you specifically want the policy text loaded on device.

The light file simplifies boundaries: drawn edges may differ from the true
boundary by up to ~100 m along coastlines and riverbanks (straight survey
lines on land are kept exact). For navigation and orientation that is
invisible; for legal boundary work use the full-detail files.

Device note: the layer is ~10.8 million polygon vertices (Ontario is large
and shape-rich). Import and first render take a while on phones; after the
layer is drawn, panning and zooming stay interactive on a reasonably modern
device. If a phone struggles, use the boundaries-only file or a regional
subset.

## What this map is (and is not)

- It shows the **land use policy area** boundaries Ontario publishes: what
  each Crown land area is designated for (General Use, Conservation
  Reserve, Enhanced Management, Provincial Park, and so on) plus the
  policy text that governs it.
- It is **not** an ownership map and **not** a survey-grade boundary
  source. Ontario states this dataset must not be used as Crown-land,
  private-land, or protected-area ownership boundaries. Always confirm
  actual land status with Ontario before relying on it.
- Coverage is Ontario only; other provinces publish their own Crown land
  data separately.
- Overlay policies (36 areas where a designation such as a conservation
  reserve modifies the base policy) are a planned addition; the current
  release covers the primary policy layer and may show incomplete guidance
  where an overlay applies.

## What you get

- `clupa_boundaries.kmz`: all 1,261 Ontario Crown land use policy area
  polygons, named, with `policy_id` + `designation` as ExtendedData.
  No descriptions.
- `clupa_full_with_descriptions.kmz`: same boundaries, plus a KML
  `<description>` per polygon carrying the atlas policy text:
  land area description, land use intent, permitted uses preface/addendum,
  up to the full list of permitted uses with guidelines
  (1,218 of 1,261 areas have published policy text; the other 43 areas are
  parks/reserves whose policy lives outside the CLUPA policy table).

## Repo layout

```
assets/
  fetch_layer.py           paginated downloader (SSL verification on,
                           exceededTransferLimit-aware, count-checked)
  distill_boundaries.py    trims raw boundary GeoJSON attributes
  build_atak_kmz.py        builds the two KMZ products below
dist/                      build outputs (gitignored - regenerate)
  clupa_boundaries.kmz          boundaries only (~70 MB)
  clupa_full_with_descriptions.kmz  boundaries + policy text (~70 MB)
docs/                      build/release notes
```

## Rebuilding from source data (optional)

```bash
python assets/fetch_layer.py 5 8 13   # boundary + policy + permitted-use layers
python assets/build_atak_kmz.py --descriptions   # full version
python assets/build_atak_kmz.py                  # boundaries-only version
```

The build fails loudly if inputs are missing or a download is truncated
(record count checked against the service), so a "successful" build means
all expected records came down.

## Source & licence

- ArcGIS REST services (same backend as the CLUPA web atlas):
  - Boundaries: `LIO_OPEN_DATA/LIO_Open06/MapServer/5` (CLUPA Provincial)
  - Policy text: `.../8` (CLUPA Policy) + `.../13` (CLUPA Policy + Permitted Use)
  - Overlay: `.../4` (CLUPA Overlay)
- [Ontario GeoHub dataset](https://geohub.lio.gov.on.ca/datasets/c71addd613b94c6bbdad9228d322b161)
- Open Government Licence - Ontario:
  https://www.ontario.ca/page/open-government-licence-ontario
