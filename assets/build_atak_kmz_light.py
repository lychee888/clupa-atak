"""Build a reduced-size KMZ: preferred designations only + optional
Douglas-Peucker geometry simplification.

Usage:
  python build_atak_kmz_light.py                     # 4 designations, full detail
  python build_atak_kmz_light.py --tolerance 0.001   # simplify (~100 m)
  python build_atak_kmz_light.py --descriptions       # include policy text too

Default designations: General Use Area, Enhanced Management Area,
Provincial Park, Conservation Reserve.

Douglas-Peucker is written here in ~30 lines (cross-track distance in
degrees is fine at these latitudes for a 0.001 deg = ~80-110 m tolerance).

Output: dist/clupa_light.kmz
"""
import json, os, sys, math, zipfile, html
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
L5 = os.path.join(ROOT, "assets", "layer5.geojson")
L8 = os.path.join(ROOT, "assets", "layer8.geojson")
L13 = os.path.join(ROOT, "assets", "layer13.geojson")
OUT = os.path.join(ROOT, "dist", "clupa_light.kmz")

DEFAULT_DESIGNATIONS = {
    "General Use Area",
    "Enhanced Management Area",
    "Provincial Park",
    "Conservation Reserve",
}


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


# ---- Douglas-Peucker (perpendicular distance in degrees; fine at 0.001 tol) ----

def _perp_dist(pt, a, b):
    (x, y), (x1, y1), (x2, y2) = pt, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return math.hypot(x - x1, y - y1)
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))


def dp(points, tol):
    if len(points) < 3:
        return points
    stack = [(0, len(points) - 1)]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        dmax, idx = 0.0, -1
        for k in range(i + 1, j):
            d = _perp_dist(points[k], points[i], points[j])
            if d > dmax:
                dmax, idx = d, k
        if dmax > tol:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    return [p for p, k in zip(points, keep) if k]


def simplify_polygon(coords, tol):
    """coords = list of rings."""
    out = []
    for ring in coords:
        r = dp(ring, tol)
        # a valid ring needs >= 4 points (closure)
        if r and (r[0] != r[-1] or len(r) < 4):
            if len(r) + 1 < 4:
                continue
            r = r + [r[0]]
        if len(r) >= 4:
            out.append(r)
    return out


def simplify(geom, tol):
    t = geom["type"]
    if t == "Polygon":
        sc = simplify_polygon(geom["coordinates"], tol)
        if not sc:
            return None
        return {"type": "Polygon", "coordinates": sc}
    if t == "MultiPolygon":
        polys = [sc for p in geom["coordinates"] if (sc := simplify_polygon(p, tol))]
        if not polys:
            return None
        return {"type": "MultiPolygon", "coordinates": polys}
    raise ValueError(t)


def count_verts(g):
    if not g:
        return 0
    if g["type"] == "Polygon":
        return sum(len(r) for r in g["coordinates"])
    return sum(len(r) for p in g["coordinates"] for r in p)


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
    t = geom["type"]
    if t == "Polygon":
        parts.append(f"<Polygon><tessellate>1</tessellate>{poly_kml(geom['coordinates'])}</Polygon>")
    else:
        polys = [f"<Polygon><tessellate>1</tessellate>{poly_kml(p)}</Polygon>" for p in geom["coordinates"]]
        parts.append("<MultiGeometry>" + "".join(polys) + "</MultiGeometry>")
    return "".join(parts)


def main():
    tol = 0.0
    if "--tolerance" in sys.argv:
        tol = float(sys.argv[sys.argv.index("--tolerance") + 1])
    with_desc = "--descriptions" in sys.argv

    bound = load_json(L5)
    policies, ogf2id, perm = {}, {}, {}
    if with_desc:
        for p in (L8, L13):
            if not os.path.exists(p):
                raise SystemExit(f"missing {p} for --descriptions")
        for f in load_json(L8)["features"]:
            p = f["properties"]
            if p.get("POLICY_IDENT"):
                policies.setdefault(p["POLICY_IDENT"], []).append(p)
        for pid, rows in list(policies.items()):
            row = newest_row(rows)
            policies[pid] = row
            ogf2id[row.get("OGF_ID")] = pid
        for f in load_json(L13)["features"]:
            p = f["properties"]
            ident = ogf2id.get(p.get("CLUPA_POLICY_ID"))
            if ident:
                perm.setdefault(ident, []).append(p)

    placemarks = []
    kept = dropped_desig = dropped_simplify = 0
    vin = vout = 0
    descs = 0
    for f in bound["features"]:
        p = f["properties"]
        desig = p.get("DESIGNATION_ENG") or ""
        if desig not in DEFAULT_DESIGNATIONS:
            dropped_desig += 1
            continue
        g = f["geometry"]
        vin += count_verts(g)
        if tol > 0:
            g2 = simplify(g, tol)
            if not g2:
                dropped_simplify += 1
                continue
            g = g2
        vout += count_verts(g)
        kept += 1
        pid = p.get("POLICY_IDENT")
        name = p.get("NAME_ENG") or pid or "CLUPA area"
        desc = ""
        if with_desc:
            prow = policies.get(pid)
            if prow:
                desc = build_policy_text(prow, perm.get(pid, []))
                if desc:
                    descs += 1
        lines = ["<Placemark>", f"<name>{kml_val(name)}</name>"]
        if desc:
            lines.append(f"<description><![CDATA[{html.escape(clean_text(desc))}]]></description>")
        lines.append("<styleUrl>#clupa</styleUrl>")
        if pid:
            lines.append(
                f"<ExtendedData><Data name=\"policy_id\"><value>{kml_val(pid)}</value></Data>"
                f"<Data name=\"designation\"><value>{kml_val(desig)}</value></Data></ExtendedData>")
        lines.append(geom_kml(g))
        lines.append("</Placemark>")
        placemarks.append("".join(lines))

    kml = ('<?xml version="1.0" encoding="UTF-8"?>'
           '<kml xmlns="http://www.opengis.net/kml/2.2">'
           '<Document><name>Ontario CLUPA (reduced: 4 designations)</name>'
           '<Style id="clupa">'
           '<LineStyle><color>660000ff</color><width>2</width></LineStyle>'
           '<PolyStyle><color>400088cc</color><fill>1</fill><outline>1</outline></PolyStyle>'
           '</Style>'
           + "".join(placemarks) + '</Document></kml>')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml)
    suffix = f", simplified tol={tol}deg" if tol else ""
    print(f"WROTE {OUT} {os.path.getsize(OUT)} bytes | kept={kept} "
          f"dropped_by_designation={dropped_desig} dropped_by_simplify={dropped_simplify} "
          f"descriptions={descs} vertices {vin:,}->{vout:,}{suffix}")


if __name__ == "__main__":
    main()
