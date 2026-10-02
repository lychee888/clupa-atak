"""Per-province endpoint configuration for the provincial CLUPA-style pipeline.

Each province entry describes a single "crown/public land polygons" source that
has been probed live (2026-10-02) and is downloadable free of charge without
API keys. The fetcher implementations live in fetch_province.py.

Dictionary keys per province:
  code          two-letter province code, used for filenames
  name          display name
  kind          fetcher algorithm: wfs | arcgis | socrata | file
  endpoint      base service URL(s)
  ...           fetcher-specific kwargs (see fetch_province.py)

Field mappings (property names -> KMZ output) live in build_kmz_province.py.
"""

PROVINCES = {
    "bc": {
        "name": "British Columbia",
        "kind": "wfs",
        "endpoint": "https://openmaps.gov.bc.ca/geo/pub/WHSE_TANTALIS.TA_CROWN_TENURES_SVW/ows",
        "typenames": "pub:WHSE_TANTALIS.TA_CROWN_TENURES_SVW",
        # sortBy is REQUIRED for offset/limits: unsorted queries silently repeat
        "sort_field": "OBJECTID",
        "page": 2000,
        "title_field": "TENURE_LOCATION",
        "cat_field": "TENURE_TYPE",
        "folder_field": "TENURE_TYPE",
        "desc_fields": (
            "TENURE_PURPOSE",
            "TENURE_SUBPURPOSE",
            "TENURE_SUBTYPE",
            "TENURE_STATUS",
            "CROWN_LANDS_FILE",
        ),
        "notes": "WFS 2.0, GeoJSON output, paging needs sortBy=OBJECTID.",
    },
    "ab": {
        "name": "Alberta",
        "kind": "arcgis",
        "endpoint": "https://geospatial.alberta.ca/titan/rest/services/boundary/asrd_administrative_area/MapServer",
        "layer": 1,  # Green White Area
        "title_field": "GWA_NAME",
        "cat_field": "GWA_NAME",
        "bookmark_as": "Green/White Area",
        "notes": "Green/White Area (unpatented crown land extent); replaces paid Altalis DIDs.",
    },
    "sk": {
        "name": "Saskatchewan",
        "kind": "arcgis",
        "endpoint": "https://gis.saskatchewan.ca/arcgis/rest/services/Agriculture/CrownLand_AG/MapServer",
        "layer": 2,  # Agricultural Crown Land quarter-section envelope
        "title_field": "LLD",
        "cat_field": "LLD",
        "notes": "Agricultural Crown Land quarter sections.",
    },
    "mb": {
        "name": "Manitoba",
        "kind": "multi_arcgis",
        "sources": [
            {
                "endpoint": "https://services.arcgis.com/mMUesHYPkXjaFGfS/arcgis/rest/services/Manitoba_Parks/FeatureServer",
                "layer": 0,
                "title_field": "NAME_E",
                "cat_field": "BIOME",
                "cat_default": "Manitoba Park",
                "bookmark_as": "Manitoba Parks",
            },
            {
                "endpoint": "https://services.arcgis.com/mMUesHYPkXjaFGfS/arcgis/rest/services/Manitoba_Provincial_Forests___Version_6/FeatureServer",
                "layer": 1,
                "title_field": "PROV_FOREST_NAME",
                "cat_field": "PROV_FOREST_NAME",
                "cat_default": "Provincial Forest",
                "bookmark_as": "Provincial Forests",
            },
            {
                "endpoint": "https://services.arcgis.com/mMUesHYPkXjaFGfS/arcgis/rest/services/Manitoba_Cottage_Lot_Program_Inventory/FeatureServer",
                "layer": 0,
                "title_field": None,
                "cat_default": "Cottage Lot Inventory",
                "bookmark_as": "Cottage Lot Inventory",
            },
            {
                "endpoint": "https://services.arcgis.com/mMUesHYPkXjaFGfS/arcgis/rest/services/bdy_wildlife_mgmt_areas_py_shp/FeatureServer",
                "layer": 0,
                "title_field": "NAME_E",
                "cat_default": "Wildlife Management Area",
                "bookmark_as": "Wildlife Management Areas",
            },
        ],
        "notes": "Public-land portfolio assembled from DataMB ArcGIS feature services.",
    },
    "qc": {
        "name": "Quebec",
        "kind": "file",
        "endpoint": "https://diffusion.mern.gouv.qc.ca/Diffusion/RGQ/Vectoriel/Theme/Local/PATP/SHP/PATP_Affectation.zip",
        "shp_member_glob": "*.shp",
        "title_field": "NOM_ZONE",
        "cat_field": "VOCATION",
        "notes": "PATP (Plans d'affectation du territoire public) shapefile, ~100 MB; "
                 "parks/conservation/affectation of public domain.",
    },
    "nb": {
        "name": "New Brunswick",
        "kind": "arcgis",
        "endpoint": "https://geonb.snb.ca/arcgis/rest/services/GeoNB_DNR_Crown_Land/MapServer",
        "layer": 3,
        "page_size": 500,
        "title_field": "HOLDER",
        "cat_field": "HOLDER",
        "notes": "GeoNB DNR Crown Land polygon (10,002 features).",
    },
    "ns": {
        "name": "Nova Scotia",
        "kind": "arcgis",
        "endpoint": "https://nsgiwa.novascotia.ca/arcgis/rest/services/PLAN/PLANCrownLandsWM84V1/MapServer",
        "layer": 0,
        "title_field": "PGPI",
        "cat_field": "FCode",
        "notes": "GeoNova PLANCrownLandsWM84V1 (18,526 parcels). Socrata export "
                 "https://data.novascotia.ca/api/geospatial/3nka-59nz is an alternative.",
    },
    "pe": {
        "name": "Prince Edward Island",
        "kind": "skip",
        "reason": "No parcel-level Crown land polygon layer is published as open "
                  "data. The Peer Governmeent publishes a fixed PDF atlas but no "
                  "machine-readable Crown land boundaries; property_parcels on "
                  "gis.princeedwardisland.ca has no ownership attribute to filter "
                  "Crown vs private.",
    },
    "nl": {
        "name": "Newfoundland and Labrador",
        "kind": "arcgis",
        "endpoint": "https://www.gov.nl.ca/landuseatlasmaps/rest/services/LandUseDetails/MapServer",
        "layer": 3,  # Crown Titles
        "title_field": "TITLENO",
        "cat_field": "TITLETYPE",
        "title_field_extra": "APPLICANT",
        "notes": "Land Use Atlas 'Crown Titles' layer; ~79,000 parcels.",
    },
}
