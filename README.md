# CLUPA for ATAK (Ontario CLUPA + provincial Crown/public land) (Compiled 2026-10-01)

Ready-to-import map data for [ATAK](https://atakwiki.org/) showing Ontario
Crown Land Use Policy Area boundaries from the [Crown Land Use Policy Atlas
(CLUPA)](https://www.ontario.ca/page/crown-land-use-policy-atlas), with
optional per-area policy descriptions (land use intent, permitted uses and
guidelines).  Since v1.2, the same format is also built for eight other
provinces' Crown / public land layers (BC, AB, SK, MB, QC, NB, NS, NL; PEI
unavailable — see the province table).

Everything is built with Python 3 stdlib only (no pip dependencies) from
Ontario's open ArcGIS REST service. Data remains Crown copyright, Ontario
Ministry of Natural Resources; open-data licensed (see Source & licence).

## Import into ATAK 

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
     areas.
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

Device note: the two full-detail files are ~10.8 million polygon vertices
(Ontario is large and shape-rich). Import and first render take a while on
phones; after the layer is drawn, panning and zooming stay interactive on a
reasonably modern device. The light file has no such constraint.

Toggles and colors: all files group polygons in folders by designation, so
ATAK's layer manager can show/hide General Use vs Enhanced Management vs
Provincial Park vs Conservation Reserve independently. Colors: green =
General Use, amber = Enhanced Management, blue = Provincial Park, purple =
Conservation Reserve, grey = Other.

## Provincial coverage (v1.2)

One KMZ per province in two variants: **full** (raw source geometry) and
**light** (Douglas-Peucker simplified to ~100 m; the same simplifier as
Ontario's `clupa_light.kmz`).  Folder colours follow Ontario's scheme:
green = general use, amber = tenures/licences, blue = park, purple =
conservation/reserve, grey = other.

| Code | Province | Source dataset | Full (`_crown_full.kmz` size) | Light (`_crown_light.kmz` size) | Notes |
|------|----------|----------------|------------------------------|--------------------------------|-------|
| `bc` | British Columbia | TANTALIS Crown Tenures (WFS, openmaps.gov.bc.ca) | 77.9 MB / 66,400 polygons | 7.1 MB / 52,794 polygons | All active Crown tenures incl. licences, leases, ROWs. This is tenure data, not "public land", so it shows where a *tenure* exists, not which land is vacant public. |
| `ab` | Alberta | Green/White Area (ASRD administrative area MapServer) | 0.8 MB / 39 polygons | 0.08 MB / 39 polygons | Free equivalent of Altalis DIDs. **Green Area** = unpatented / vacant Crown land, **White Area** = surveyed, mostly private/sold. Two polygons each; big, not survey-detailed. |
| `sk` | Saskatchewan | Agricultural Crown Land quarter sections (gis.saskatchewan.ca) | 5.9 MB / 59,985 polygons | 3.9 MB / 59,982 polygons | Covers **agricultural** Crown land only (quarter sections). Forestry/Crown-at-large parcels are not published as free data. |
| `mb` | Manitoba | DataMB ArcGIS feature services (Parks + Provincial Forests + Cottage Lots + Wildlife Management Areas) | 1.8 MB / 307 polygons | 0.12 MB / 306 polygons | A public-land *portfolio* assembled from four free services. Manitoba does not publish an all-in-one "Crown land" polygon layer as open data. |
| `qc` | Quebec | PATP (Plans d'affectation du territoire public) shapefile | 68.2 MB / 7,874 polygons | 3.0 MB / 5,355 polygons | Vocation-based affectation of the public domain (utilisation multiple / protection stricte etc.). Coordinates converted from EPSG:32198 to WGS84. |
| `nb` | New Brunswick | GeoNB DNR Crown Land MapServer | 15.7 MB / 10,002 polygons | 0.8 MB / 7,387 polygons | Parcel-level Crown land (with integer holder code; no names, no licence types). |
| `ns` | Nova Scotia | GeoNova PLAN/CrownLands WM MapServer | 16.8 MB / 18,524 polygons | 1.2 MB / 13,831 polygons | Province's own Crown lands holdings. |
| `pe` | **Prince Edward Island** | — | **NOT AVAILABLE** | **NOT AVAILABLE** | No parcel-level Crown land polygon layer is published as open data. PEI publishes a PDF atlas and property parcels but without an ownership attribute; a Crown land boundary dataset exists only in the paid PEI GeoLinc subscription. |
| `nl` | Newfoundland and Labrador | Land Use Atlas "Crown Titles" MapServer | 31.5 MB / 78,943 polygons | 2.8 MB / 38,605 polygons | Crown titles, i.e. issued Crown land parcels, grouped by title type. |

### Import notes per province

- **All provinces** group polygons in folders so ATAK's layer manager can
  show/hide general-use vs tenures vs parks vs conservation land
  independently.  Colours match Ontario's so a user loading two provinces
  at once sees a consistent legend.
- **Alberta** is a *shape-level* Green/White Area, not parcels: it shows
  *which half of the province is unpatented Crown land* (huge areas ~
  340,000 km²).  Use it to decide whether land at a point is likely Crown
  or private; for parcel-precision use Altalis (paid) or the Green Area
  shape plus your own disposition CAD.
- **Manitoba** is put together from four services because no single open
  dataset covers it; expect visible category boundaries between Parks and
  Provincial Forests to be inconsistent across releases.

## What this map is (and is not)

- It shows the **land use policy area** boundaries Ontario publishes: what
  each Crown land area is designated for (General Use, Conservation
  Reserve, Enhanced Management, Provincial Park, and so on) plus the
  policy text that governs it.
- It is **not** an ownership map and **not** a survey-grade boundary
  source. Ontario states this dataset must not be used as Crown-land,
  private-land, or protected-area ownership boundaries. Always confirm
  actual land status with Ontario before relying on it.
- The **provincial (non-Ontario) files** are an *approximation* — for several
  provinces only a subset of the area (e.g. Saskatchewan's agricultural
  Crown land, Alberta's Green/White shape) is publicly available.  See the
  per-province notes above.  Data remains licensed under each province's
  own open-government licence.
- Coverage is Ontario + the provinces in the table; the territories are
  not covered.
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
  provinces/
    province_config.py     endpoints + field mappings, one dict per province
    fetch_province.py      config-driven per-province fetcher
    build_kmz_province.py  full + 100 m-simplified KMZ per province
    qc_lambert.py          EPSG:32198 -> WGS84 (used for the Quebec source)
    raw/                   downloads (gitignored - regenerate)
dist/                      build outputs (gitignored - regenerate)
  clupa_boundaries.kmz          boundaries only (~70 MB)
  clupa_full_with_descriptions.kmz  boundaries + policy text (~70 MB)
  <code>_crown_full.kmz / _crown_light.kmz  provincial files, one pair per province
docs/                      build/release notes
```

## Rebuilding from source data (optional)

Ontario:

```bash
python assets/fetch_layer.py 5 8 13   # boundary + policy + permitted-use layers
python assets/build_atak_kmz.py --descriptions   # full version
python assets/build_atak_kmz.py                  # boundaries-only version
```

Provinces:

```bash
python assets/provinces/fetch_province.py          # all (or pass codes)
python assets/provinces/build_kmz_province.py bc   # one province, or all
```

Both builds fail loudly if inputs are missing or a download is truncated
(record count checked against the service), so a "successful" build means
all expected records came down.

## Source & licence

Ontario:

- ArcGIS REST services (same backend as the CLUPA web atlas):
  - Boundaries: `LIO_OPEN_DATA/LIO_Open06/MapServer/5` (CLUPA Provincial)
  - Policy text: `.../8` (CLUPA Policy) + `.../13` (CLUPA Policy + Permitted Use)
  - Overlay: `.../4` (CLUPA Overlay)
- [Ontario GeoHub dataset](https://geohub.lio.gov.on.ca/datasets/c71addd613b94c6bbdad9228d322b161)
- Open Government Licence - Ontario:
  https://www.ontario.ca/page/open-government-licence-ontario

Provinces (each under its own open-government licence, endpoint details in
`assets/provinces/province_config.py`):

- BC: openmaps.gov.bc.ca WFS, WHSE_TANTALIS.TA_CROWN_TENURES_SVW
  (Open Government Licence – BC)
- AB: geospatial.alberta.ca MapServer, `asrd_administrative_area/1`
- SK: gis.saskatchewan.ca `Agriculture/CrownLand_AG/MapServer/2`
- MB: geoportal.gov.mb.ca → DataMB ArcGIS feature services (4 services)
- QC: diffusion.mern.gouv.qc.ca PATP shapefile (Licence ouverte du Québec)
- NB: geonb.snb.ca `GeoNB_DNR_Crown_Land/MapServer/3`
- NS: nsgiwa.novascotia.ca `PLAN/PLANCrownLandsWM84V1/MapServer/0`
- NL: gov.nl.ca/landuseatlasmaps `LandUseDetails/MapServer/3` (Crown Titles)
