"""Distill raw CLUPA layer5 GeoJSON into a lean boundary file for ATAK.

Keeps only the useful fields, renames them readably, and writes:
  dist/boundaries.geojson   (lean, ~5-10 MB)
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
KEEP = {
    "POLICY_IDENT": "policy_id",
    "NAME_ENG": "name",
    "DESIGNATION_ENG": "designation",
    "CATEGORY_ENG": "category",
    "OGF_ID": "ogf_id",
    "AOU_DESIGNATION": "aou_flag",
}
DROP = ("EFFECTIVE_DATETIME", "SYSTEM_DATETIME", "SHAPE", "SHAPE.AREA", "SHAPE.LEN",
        "VISIBILITY_IND", "DESIGNATION_FR", "NAME_FR", "CATEGORY_FR", "OVERLAY_IND",
        "RELATED_CLASS_SHORT_NAME")

def main():
    src = os.path.join(HERE, "..", "assets", "layer5.geojson")
    out = os.path.join(HERE, "..", "dist", "boundaries.geojson")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    d = json.load(open(src, encoding="utf-8"))
    feats = []
    for f in d["features"]:
        p = f.get("properties", {})
        np = {}
        for k, v in KEEP.items():
            if p.get(k) is not None:
                np[v] = p[k]
        feats.append({"type": "Feature",
                      "geometry": f["geometry"],
                      "properties": np})
    fc = {"type": "FeatureCollection",
          "name": "Ontario Crown Land Use Policy Areas (CLUPA)",
          "features": feats}
    json.dump(fc, open(out, "w", encoding="utf-8"))
    print("features:", len(feats), "size:", os.path.getsize(out))

if __name__ == "__main__":
    main()
