"""Build a KMZ for ATAK from the distilled CLUPA boundaries + optional policy descriptions.

Usage:
  python build_atak_kmz.py              # boundaries only (no descriptions)
  python build_atak_kmz.py --descriptions  # embed policy text per polygon

The output KMZ opens in ATAK via Import > File. Polygons keep their
policy_id/name/designation attributes; with --descriptions the KML
description contains the full CLUPA policy text (land area description,
land use intent, permitted uses preface/addendum, up to 40 permitted
uses with guidelines, and the official policy URL).

No third-party dependencies: Python 3 stdlib only (zipfile + xml).
"""
import json, os, sys, zipfile, html
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
L5 = os.path.join(ROOT, "assets", "layer5.geojson")
L8 = os.path.join(ROOT, "assets", "layer8.geojson")   # policy text
L13 = os.path.join(ROOT, "assets", "layer13.geojson")  # policy + permitted use
OUT_BOUND = os.path.join(ROOT, "dist", "clupa_boundaries.kmz")
OUT_FULL = os.path.join(ROOT, "dist", "clupa_full_with_descriptions.kmz")


def load_json(p):
    return json.load(open(p, encoding="utf-8"))


def kml_val(v):
    """None-safe escape."""
    if v is None:
        return ""
    if isinstance(v, str):
        return escape(v)
    return escape(str(v), quote=False)


def build_policy_text(policy_row, perm_rows):
    """Human-readable KL instance-style description strings."""
    lines = []
    land = policy_row.get("LAND_AREA_DESCR_ENG") or ""
    intent = policy_row.get("LAND_USE_INTENT_DESCR_ENG") or ""
    preface = policy_row.get("PERMITTED_USES_PREFACE_ENG") or ""
    addendum = policy_row.get("PERMITTED_USES_ADDENDUM_ENG") or ""
    url = policy_row.get("URL_ENG") or ""
    if land:
        lines.append("LAND AREA DESCRIPTION:")
        lines.append(land.strip())
        lines.append("")
    if intent:
        lines.append("LAND USE INTENT:")
        lines.append(intent.strip())
        lines.append("")
    if preface:
        lines.append("PERMITTED USES PREFACE:")
        lines.append(preface.strip())
        lines.append("")
    if perm_rows:
        lines.append("PERMITTED USES:")
        for r in perm_rows:
            typ = r.get("PERMITTED_USE_TYPE_ENG") or ""
            flag = r.get("PERMITTED_FLG_ENG") or ""
            guidelines = (r.get("PERMITTED_USE_GUIDELINES_ENG") or "").strip()
            lines.append(f"- {typ} | {flag}")
            if guidelines:
                lines.append(f"  {guidelines}")
        lines.append("")
    if addendum:
        lines.append("PERMITTED USES ADDENDUM:")
        lines.append(addendum.strip())
        lines.append("")
    if url:
        lines.append("REFERENCE:")
        lines.append(url)
    return "\n".join(lines)


def geom_kml(geom):
    """Convert GeoJSON Polygon or MultiPolygon to a KML string body."""
    parts = []
    def coord_line(ring):
        # rings are [[lon,lat, ...]]; GeoJSON -> KML keeps lon,lat (drop z if present)
        s = " "
        return " ".join(f"{c[0]:.6f},{c[1]:.6f}" for c in ring)
    def poly_kml(polys):
        b = []
        for ring_i, ring in enumerate(polys):
            tag = "outerBoundaryIs" if ring_i == 0 else "innerBoundaryIs"
            b.append(f"<{tag}><LinearRing><coordinates>{coord_line(ring)}</coordinates></LinearRing></{tag}>")
        return "".join(b)
    t = geom.get("type")
    if t == "Polygon":
        parts.append(f"<Polygon><tessellate>1</tessellate>{poly_kml(geom['coordinates'])}</Polygon>")
    elif t == "MultiPolygon":
        polys = []
        for p in geom["coordinates"]:
            polys.append(f"<Polygon><tessellate>1</tessellate>{poly_kml(p)}</Polygon>")
        parts.append("<MultiGeometry>" + "".join(polys) + "</MultiGeometry>")
    else:
        raise ValueError(f"unsupported geom type {t}")
    return "".join(parts)


def build_kmz(out_path, with_descriptions):
    bound = load_json(L5) if os.path.exists(L5) else None
    if bound is None:
        raise SystemExit("asset layer5.geojson missing; run fetch first")
    policies = {}
    ogf_to_policy_ident = {}
    if with_descriptions:
        if os.path.exists(L8):
            for f in load_json(L8)["features"]:
                p = f["properties"]
                pid = p.get("POLICY_IDENT")
                if pid:
                    policies[pid] = p
                    ogf_to_policy_ident[p.get("OGF_ID")] = pid
        perm_by_policy = {}
        if os.path.exists(L13):
            for f in load_json(L13)["features"]:
                p = f["properties"]
                ident = ogf_to_policy_ident.get(p.get("CLUPA_POLICY_ID"))
                if ident:
                    perm_by_policy.setdefault(ident, []).append(p)

    placemarks = []
    for f in bound["features"]:
        p = f["properties"]
        pid = p.get("POLICY_IDENT") or p.get("policy_id")
        name = p.get("name") or pid or "CLUPA area"
        desc = ""
        if with_descriptions:
            prow = policies.get(pid)
            perm = perm_by_policy.get(pid, [])
            if prow:
                desc = build_policy_text(prow, perm)
        lines = [
            f"<Placemark>",
            f"<name>{kml_val(name)}</name>",
            f"<styleUrl>#clupa</styleUrl>",
        ]
        if pid:
            lines.append(f"<ExtendedData><Data name=\"policy_id\"><value>{kml_val(pid)}</value></Data>"
                         f"<Data name=\"designation\"><value>{kml_val(p.get('designation',''))}</value></Data></ExtendedData>")
        if desc:
            lines.append(f"<description><![CDATA[{html.escape(desc)}]]></description>")
        lines.append(geom_kml(f["geometry"]))
        lines.append("</Placemark>")
        placemarks.append("".join(lines))

    kml = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
           "<kml xmlns=\"http://www.opengis.net/kml/2.2\">"
           "<Document><name>Ontario Crown Land Use Policy Areas</name>"
           "<Style id=\"clupa\">"
           "<LineStyle><color>660000ff</color><width>2</width></LineStyle>"
           "<PolyStyle><color>400088cc</color><fill>1</fill><outline>1</outline></PolyStyle>"
           "</Style>"
           + "".join(placemarks) +
           "</Document></kml>")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)
    print("WROTE", out_path, os.path.getsize(out_path), "bytes")


if __name__ == "__main__":
    full = "--descriptions" in sys.argv
    build_kmz(OUT_FULL if full else OUT_BOUND, full)
