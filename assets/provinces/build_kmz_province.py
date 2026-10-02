"""Provincial KMZ builder: full-accuracy raw geometry + 100 m simplified.

Usage:
  python build_kmz_province.py bc nb          # build both KMZs for codes
  python build_kmz_province.py                # all available provinces

For each province code with a raw GeoJSON in assets/provinces/raw/:
  dist/<code>_crown_full.kmz     raw geometry, all features
  dist/<code>_crown_light.kmz    Douglas-Peucker 0.001 deg (~100 m) simplified

Folder colours mirror Ontario's designation scheme exactly:
  General Use / general public lands  green
  Polygons-classified "special"       amber (tenures, leases)
  Provincial/National Park category   blue
  Conservation / reserves             purple
  Other                               grey

Description text (per polygon) puts the most useful attributes first.
"""
import json, os, sys, math, zipfile, html
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # repo root
RAW = os.path.join(HERE, "raw")
DIST = os.path.join(ROOT, "dist")
os.makedirs(DIST, exist_ok=True)

from province_config import PROVINCES

# KML aabbggrr fill colors; purple/amber/green/blue/grey palette same as Ontario
# and whichever special cases provinces show
STYLE_COLORS = {
    # exact as Ontario
    "General Use Area":          ("clupa-gu",  "332e8b46", "ff2e8b46"),
    "Enhanced Management Area":  ("clupa-ema", "3300a5c7", "ff00a5c7"),
    "Provincial Park":           ("clupa-pp",  "40e68b22", "ffe68b22"),
    "Conservation Reserve":      ("clupa-cr",  "40b060a0", "ffb060a0"),
    "Other":                     ("clupa-ot",  "30888888", "ff666666"),
}
FOLDER_ORDER = list(STYLE_COLORS)


def style_block(style_id, fill, outline):
    return (f'<Style id="{style_id}">'
            f'<LineStyle><color>{outline}</color><width>2</width></LineStyle>'
            f'<PolyStyle><color>{fill}</color><fill>1</fill><outline>1</outline></PolyStyle>'
            f'</Style>')


def kml_val(v):
    if v is None:
        return ""
    return escape(str(v))


def clean_text(s):
    return "".join(ch for ch in s if ch >= " " or ch in "\n\r\t")


# ------------- classify ------------- 
KEYWORDS = [
    # first match wins
    ("Provincial Park",       ("provincial park", "parc national", "parc provincial",
                               "manitoba park", "national park", "parc")),
    ("Conservation Reserve",  ("conservation", "protection", "écolog", "ecolog",
                               "refuge", "wildlife", "faunique", "nature",
                               "biological", "patrimonial", "heritage", "reserve",
                               "réserv", "cross-country", "private", "privé")),
    ("General Use Area",      ("general use", "green area", "unpatented",
                               "utilisation multiple", "utilisation", "timber",
                               "forest", "general", "multiple use", "multiple-use",
                               "production")),
    ("Enhanced Management Area", ("lease", "tenure", "licence", "permit",
                                  "disposition", "right-of-way", "row ",
                                  "crown grant", "payment in lieu", "rec area",
                                  "recreation", "camping", "reservation",
                                  "notation", "inventory", "crown title")),
]


def classify(category, source_layer=None):
    c = str(category or "").strip()
    lc = c.lower()
    if not c:
        return "Other"
    for label, kws in KEYWORDS:
        for kw in kws:
            if kw in lc:
                if label == "Provincial Park" and "cottage lot" in lc:
                    # cottage lots are inventory, not parks
                    continue
                return label
    return "Other"


# ------------- geometry helpers -------------
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
    out = []
    for ring in coords:
        r = dp(ring, tol)
        if r and (r[0] != r[-1] or len(r) < 4):
            if len(r) + 1 < 4:
                continue
            r = r + [r[0]]
        if len(r) >= 4:
            out.append(r)
    return out


def simplify(geom, tol):
    if not geom:
        return None
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
    if t == "LineString":
        return None  # not useful for a land-use KMZ
    if t == "MultiLineString":
        return None
    if t == "Point":
        return geom
    raise ValueError(f"unsupported geom type {t}")


def count_verts(g):
    if not g:
        return 0
    t = g["type"]
    if t == "Polygon":
        return sum(len(r) for r in g["coordinates"])
    if t == "MultiPolygon":
        return sum(len(r) for p in g["coordinates"] for r in p)
    return 0


def geom_kml(geom):
    if geom is None or count_verts(geom) == 0:
        return ""
    def coord_line(ring):
        return " ".join(f"{c[0]:.6f},{c[1]:.6f}" for c in ring)
    def poly_kml(polys):
        b = []
        for i, ring in enumerate(polys):
            tag = "outerBoundaryIs" if i == 0 else "innerBoundaryIs"
            b.append(f"<{tag}><LinearRing><coordinates>{coord_line(ring)}</coordinates></LinearRing></{tag}>")
        return "".join(b)
    t = geom["type"]
    if t == "Polygon":
        return f"<Polygon><tessellate>1</tessellate>{poly_kml(geom['coordinates'])}</Polygon>"
    if t == "MultiPolygon":
        polys = [f"<Polygon><tessellate>1</tessellate>{poly_kml(p)}</Polygon>" for p in geom["coordinates"]]
        return "<MultiGeometry>" + "".join(polys) + "</MultiGeometry>"
    return ""


# ------------- description text -------------
def build_desc(cfg, props, category, title):
    lines = []
    seen = set()
    for field in cfg.get("desc_fields", ()):
        v = props.get(field)
        if v and str(v).strip():
            lines.append(f"{field}: {clean_text(str(v))}")
            seen.add(field)
    # fall back: include any non-blank string fields so planners get *something*
    if not lines:
        for k, v in props.items():
            if v and isinstance(v, str) and len(v.strip()) > 0 and k not in seen:
                s = clean_text(v.strip())
                if len(s) < 250:
                    lines.append(f"{k}: {s}")
                if len(lines) >= 8:
                    break
    return "\n".join(lines)


# ------------- build -------------
def build(code, with_transform, tol=0.0):
    cfg = PROVINCES[code]
    src = os.path.join(RAW, f"{code}.geojson")
    fc = json.load(open(src, encoding="utf-8"))
    folder_fields = cfg.get("folder_field") or cfg.get("cat_field")

    folders = {name: [] for name in FOLDER_ORDER}
    counts = {name: 0 for name in FOLDER_ORDER}
    vin = vout = 0
    dropped_simplify = 0
    descs = 0
    nonzero_geom = 0
    for f in fc["features"]:
        p = f.get("properties") or {}
        cat = (p.get(cfg.get("cat_field")) if cfg.get("cat_field") else None) \
              or p.get("CATEGORY") \
              or ""
        title_f = cfg.get("title_field")
        title = (p.get(title_f) if title_f else None) or ""
        if cfg.get("title_field_extra"):
            if not title or title == "":
                title = p.get(cfg["title_field_extra"]) or ""
        folder = classify(cat)
        g = f.get("geometry")
        if g and count_verts(g) > 0:
            nonzero_geom += 1
        vin += count_verts(g)
        if tol > 0:
            g2 = simplify(g, tol)
            if not g2:
                dropped_simplify += 1
                continue
            g = g2
        vout += count_verts(g)
        glk = geom_kml(g)
        if not glk:
            continue
        desc = build_desc(cfg, p, cat, title)
        if desc:
            descs += 1
        counts[folder] += 1
        lines = ["<Placemark>", f"<name>{kml_val(str(title) or 'Crown land area')}</name>"]
        if desc:
            lines.append(f"<description><![CDATA[{html.escape(clean_text(desc))}]]></description>")
        lines.append(f"<styleUrl>#{STYLE_COLORS[folder][0]}</styleUrl>")
        if desc is not None:
            # ExtendedData for a couple of key attributes, always
            ev = [f"<Data name=\"category\"><value>{kml_val(cat)}</value></Data>"]
            if cfg.get("cat_field") and p.get(cfg["cat_field"]):
                ev.append(f"<Data name=\"source_value\"><value>{kml_val(title)}</value></Data>")
            lines.append("<ExtendedData>" + "".join(ev) + "</ExtendedData>")
        lines.append(glk)
        lines.append("</Placemark>")
        folders[folder].append("".join(lines))

    body = []
    for folder in FOLDER_ORDER:
        if not folders[folder]:
            continue
        body.append(f"<Folder><name>{kml_val(folder)}</name><open>0</open>"
                    + "".join(folders[folder]) + "</Folder>")

    styles = "".join(style_block(sid, fill, outline) for sid, fill, outline in STYLE_COLORS.values())
    kml_str = (f'<?xml version="1.0" encoding="UTF-8"?>'
               f'<kml xmlns="http://www.opengis.net/kml/2.2">'
               f'<Document><name>{cfg["name"]} Crown / Public Land</name>'
               + styles + "".join(body) +
               '</Document></kml>')
    tag = "full" if tol == 0 else "light"
    out_path = os.path.join(DIST, f"{code}_crown_{tag}.kmz")
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", kml_str)
    print(f"WROTE {out_path} {os.path.getsize(out_path)/1e6:.2f} MB "
          f"features={sum(counts.values())} verts_in={vin} verts_out={vout} "
          f"descs={descs} dropped_by_simplify={dropped_simplify}", flush=True)
    print("folder counts:", counts, flush=True)


if __name__ == "__main__":
    codes = [c.lower() for c in sys.argv[1:]] or list(PROVINCES)
    for c in codes:
        if c not in PROVINCES:
            print("unknown code:", c, flush=True)
            continue
        if PROVINCES[c]["kind"] == "skip":
            print(f"{c}: SKIP (config says unavailable: {PROVINCES[c].get('reason', '')[:80]})", flush=True)
            continue
        if not os.path.exists(os.path.join(RAW, f"{c}.geojson")):
            print(f"{c}: no raw geojson; run fetch_province.py {c} first", flush=True)
            continue
        build(c, with_transform=False, tol=0.0)
        build(c, with_transform=True, tol=0.001)
