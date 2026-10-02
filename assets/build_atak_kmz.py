"""Build a KMZ for ATAK from CLUPA boundaries + optional policy descriptions.

Usage:
  python build_atak_kmz.py              # boundaries only (no descriptions)
  python build_atak_kmz.py --descriptions  # embed policy text per polygon
                                           # requires layer8 + layer13; aborts if missing

Organization:
- Placemarks are grouped in Folders by designation so ATAK's layer manager
  lets users toggle General Use / Enhanced Management / Provincial Park /
  Conservation Reserve etc. independently.
- Each designation gets its own color style.
- Areas whose designation is not one of the four main ones (and areas with
  no designation) fall into an "Other" folder; nothing is dropped.

Style colors (KML aabbggrr): General Use green, Enhanced Management amber,
Provincial Park blue, Conservation Reserve purple, Other grey.

Field notes:
- Raw service fields are NAME_ENG / DESIGNATION_ENG; the distilled file
  uses name / designation. Both spellings are read.
- Duplicate policy rows for one policy ident (layer8 has 9 such ids) are
  resolved by the most recent DATE_POLICY_LAST_UPDATED.
- Descriptions are emitted before styleUrl/ExtendedData per the KML 2.2
  schema element order.

No third-party dependencies: Python 3 stdlib only (zipfile + xml).
"""
import json, os, sys, zipfile, html
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
L5 = os.path.join(ROOT, "assets", "layer5.geojson")
L8 = os.path.join(ROOT, "assets", "layer8.geojson")     # policy text
L13 = os.path.join(ROOT, "assets", "layer13.geojson")  # permitted use
L4 = os.path.join(ROOT, "assets", "layer4.geojson")    # overlays
OUT_BOUND = os.path.join(ROOT, "dist", "clupa_boundaries.kmz")
OUT_FULL = os.path.join(ROOT, "dist", "clupa_full_with_descriptions.kmz")

# fill colors are aabbggrr; outline keyed the same way
STYLES = {
    "General Use Area":          ("clupa-gu",  "332e8b46", "ff2e8b46"),
    "Enhanced Management Area":  ("clupa-ema", "3300a5c7", "ff00a5c7"),
    "Provincial Park":           ("clupa-pp",  "40e68b22", "ffe68b22"),
    "Conservation Reserve":      ("clupa-cr",  "40b060a0", "ffb060a0"),
    "Other":                     ("clupa-ot",  "30888888", "ff666666"),
}
FOLDER_ORDER = list(STYLES)


def load_json(p):
    return json.load(open(p, encoding="utf-8"))


def kml_val(v):
    if v is None:
        return ""
    return escape(str(v))


def clean_text(s):
    return "".join(ch for ch in s if ch >= " " or ch in "\n\r\t")


def newest_row(rows):
    def key(p):
        v = p.get("DATE_POLICY_LAST_UPDATED")
        return v if isinstance(v, (int, float)) else 0
    return sorted(rows, key=key)[-1]


def build_policy_text(policy_row, perm_rows):
    lines = []
    for label, field in (("LAND AREA DESCRIPTION", "LAND_AREA_DESCR_ENG"),
                         ("LAND USE INTENT", "LAND_USE_INTENT_DESCR_ENG"),
                         ("PERMITTED USES PREFACE", "PERMITTED_USES_PREFACE_ENG"),
                         ("PERMITTED USES ADDENDUM", "PERMITTED_USES_ADDENDUM_ENG")):
        v = (policy_row.get(field) or "").strip()
        if v:
            lines.append(f"{label}:")
            lines.append(v)
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
    url = policy_row.get("URL_ENG") or ""
    if url:
        lines.append("REFERENCE:")
        lines.append(url)
    return "\n".join(lines)


def geom_kml(geom):
    parts = []
    def coord_line(ring):
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


def style_block(style_id, fill, outline):
    return (f'<Style id="{style_id}">'
            f'<LineStyle><color>{outline}</color><width>2</width></LineStyle>'
            f'<PolyStyle><color>{fill}</color><fill>1</fill><outline>1</outline></PolyStyle>'
            f'</Style>')


def folder_for(desig):
    return desig if desig in STYLES else "Other"


def build_kmz(out_path, with_descriptions):
    if not os.path.exists(L5):
        raise SystemExit("assets/layer5.geojson missing; run assets/fetch_layer.py 5 first")
    bound = load_json(L5)

    policies = {}
    ogf_to_policy_ident = {}
    perm_by_policy = {}
    n_perm_rows = 0
    if with_descriptions:
        missing = [n for n, p in (("layer8", L8), ("layer13", L13)) if not os.path.exists(p)]
        if missing:
            raise SystemExit(
                f"--descriptions requires {', '.join(missing)}.geojson; "
                f"run assets/fetch_layer.py 8 13 first (refusing to build a "
                f"description-less file under the descriptions filename)")
        for f in load_json(L8)["features"]:
            p = f["properties"]
            pid = p.get("POLICY_IDENT")
            if pid:
                policies.setdefault(pid, []).append(p)
        for pid, rows in policies.items():
            row = newest_row(rows)
            policies[pid] = row
            ogf_to_policy_ident[row.get("OGF_ID")] = pid
        for f in load_json(L13)["features"]:
            p = f["properties"]
            ident = ogf_to_policy_ident.get(p.get("CLUPA_POLICY_ID"))
            if ident:
                perm_by_policy.setdefault(ident, []).append(p)
                n_perm_rows += 1

    folders = {name: [] for name in FOLDER_ORDER}
    counts = {name: 0 for name in FOLDER_ORDER}
    named = descs = 0
    for f in bound["features"]:
        p = f["properties"]
        pid = p.get("POLICY_IDENT") or p.get("policy_id")
        name = p.get("NAME_ENG") or p.get("name") or pid or "CLUPA area"
        if name and name != pid:
            named += 1
        desig = p.get("DESIGNATION_ENG") or p.get("designation") or ""
        folder = folder_for(desig)
        counts[folder] += 1
        desc = ""
        if with_descriptions:
            prow = policies.get(pid)
            perm = perm_by_policy.get(pid, [])
            if prow:
                desc = build_policy_text(prow, perm)
        lines = ["<Placemark>"]
        # KML 2.2 element order: name, description, styleUrl, extended data, geometry
        lines.append(f"<name>{kml_val(name)}</name>")
        if desc:
            lines.append(f"<description><![CDATA[{html.escape(clean_text(desc))}]]></description>")
            descs += 1
        lines.append(f"<styleUrl>#{STYLES[folder][0]}</styleUrl>")
        if pid:
            lines.append(
                f"<ExtendedData>"
                f"<Data name=\"policy_id\"><value>{kml_val(pid)}</value></Data>"
                f"<Data name=\"designation\"><value>{kml_val(desig)}</value></Data>"
                f"</ExtendedData>")
        lines.append(geom_kml(f["geometry"]))
        lines.append("</Placemark>")
        folders[folder].append("".join(lines))

    body = []
    for folder in FOLDER_ORDER:
        if not folders[folder]:
            continue
        body.append(f"<Folder><name>{kml_val(folder)}</name><open>0</open>"
                    + "".join(folders[folder]) + "</Folder>")

    styles = "".join(style_block(sid, fill, outline) for sid, fill, outline in STYLES.values())
    kml_str = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<kml xmlns="http://www.opengis.net/kml/2.2">'
               '<Document><name>Ontario Crown Land Use Policy Areas</name>'
               + styles + "".join(body) +
               '</Document></kml>')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml_str)
    print(f"WROTE {out_path} {os.path.getsize(out_path)} bytes "
          f"features={sum(counts.values())} named={named} descriptions={descs} "
          f"permitted_use_rows={n_perm_rows}")
    print("folder counts:", counts)


if __name__ == "__main__":
    full = "--descriptions" in sys.argv
    build_kmz(OUT_FULL if full else OUT_BOUND, full)
