import math
from typing import Dict

METERS_PER_DEGREE_LAT = 111_320.0


def local_to_geo(local_coord: Dict[str, float], origin_geo: Dict[str, float]) -> Dict[str, float]:
    """Convert local metric coordinates to geographic coordinates."""
    x = float(local_coord.get("x", 0.0))
    y = float(local_coord.get("y", 0.0))
    z = float(local_coord.get("z", 0.0))

    lat0 = float(origin_geo["lat"])
    lon0 = float(origin_geo["lon"])

    dlat = y / METERS_PER_DEGREE_LAT
    cos_lat = max(math.cos(math.radians(lat0)), 1e-6)
    dlon = x / (METERS_PER_DEGREE_LAT * cos_lat)

    return {
        "lon": lon0 + dlon,
        "lat": lat0 + dlat,
        "alt": float(origin_geo.get("alt", 0.0)) + z,
    }


def geo_to_local(geo_coord: Dict[str, float], origin_geo: Dict[str, float]) -> Dict[str, float]:
    """Convert geographic coordinates to local metric coordinates."""
    lat0 = float(origin_geo["lat"])
    lon0 = float(origin_geo["lon"])

    dlat = float(geo_coord["lat"]) - lat0
    dlon = float(geo_coord["lon"]) - lon0

    y = dlat * METERS_PER_DEGREE_LAT
    cos_lat = max(math.cos(math.radians(lat0)), 1e-6)
    x = dlon * METERS_PER_DEGREE_LAT * cos_lat

    return {
        "x": x,
        "y": y,
        "z": float(geo_coord.get("alt", 0.0)) - float(origin_geo.get("alt", 0.0)),
    }


def local_roundtrip_error_m(local_coord: Dict[str, float], origin_geo: Dict[str, float]) -> float:
    """Roundtrip error in meters after local->geo->local transform."""
    geo = local_to_geo(local_coord, origin_geo)
    local2 = geo_to_local(geo, origin_geo)
    dx = float(local_coord.get("x", 0.0)) - local2["x"]
    dy = float(local_coord.get("y", 0.0)) - local2["y"]
    dz = float(local_coord.get("z", 0.0)) - local2["z"]
    return math.sqrt(dx * dx + dy * dy + dz * dz)
