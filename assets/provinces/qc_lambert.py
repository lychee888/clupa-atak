"""Minimal Lambert-Conformal-Conic (Quebec Lambert / NAD83) to WGS84 converter.

Used only for Quebec's PATP shapefile, which ships in EPSG:32198.
Pure Python 3 stdlib; ~ centimetre accuracy over Quebec's extent.
"""
import math

# WGS84 / NAD83 ellipsoid
A = 6378137.0
INV_F = 298.257222101
F = 1.0 / INV_F
E = math.sqrt(F * (2 - F))  # first eccentricity

# EPSG:32198 NAD83 / Quebec Lambert
CM = -68.5
PHI0 = 44.0
PHI1 = 46.0
PHI2 = 60.0
FE = 0.0
FN = 0.0


def _m(phi):
    return math.cos(phi) / math.sqrt(1 - E * E * math.sin(phi) ** 2)


def _t(phi):
    s = math.sin(phi)
    return math.tan(math.pi / 4 - phi / 2) / ((1 - E * s) / (1 + E * s)) ** (E / 2)


def _n(phi1, phi2):
    return (math.log(_m(phi1)) - math.log(_m(phi2))) / (math.log(_t(phi1)) - math.log(_t(phi2)))


N = _n(math.radians(PHI1), math.radians(PHI2))
C = _m(math.radians(PHI1)) / (N * _t(math.radians(PHI1)) ** N)
RHO0 = A * C * _t(math.radians(PHI0)) ** N


def to_wgs84(x, y):
    """EPSG:32198 (x=easting, y=northing) -> (lon, lat) in WGS84 degrees."""
    rho = math.hypot(x - FE, RHO0 - (y - FN))
    theta = math.atan2(x - FE, RHO0 - (y - FN))
    lon = math.degrees(theta / N) + CM
    # rho = A*C * t^N   =>   t = (rho/(A*C))^(1/N)
    target = (rho / (A * C)) ** (1.0 / N)
    # bisect phi so that _t(phi) == target
    lo, hi = math.radians(-85.0), math.radians(85.0)
    for _ in range(80):
        mid = (lo + hi) / 2
        if _t(mid) > target:
            lo = mid
        else:
            hi = mid
    return lon, math.degrees((lo + hi) / 2)


def fwd(lon, lat):
    """WGS84 -> EPSG:32198 (diagnostic use)."""
    lam = math.radians(lon - CM)
    phi = math.radians(lat)
    rho = A * C * _t(phi) ** N
    return rho * math.sin(lam * N), RHO0 - rho * math.cos(lam * N)


if __name__ == "__main__":
    # Round-trip check: Quebec City lat/lon via the forward and back
    lon, lat = -71.208, 46.813
    x, y = fwd(lon, lat)
    back_lon, back_lat = to_wgs84(x, y)
    print(f"fwd  -> {x:.1f}, {y:.1f}")
    print(f"back -> {back_lon:.5f}, {back_lat:.5f}  (expect {lon:.5f}, {lat:.5f})")
