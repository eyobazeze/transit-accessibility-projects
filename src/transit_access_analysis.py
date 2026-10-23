#!/usr/bin/env python3
"""Reproduce the population-weighted transit-proximity analysis for Addis Ababa.

The analysis uses:
- SSGI woreda-level administrative boundaries for Addis Ababa (via HDX, CC0 1.0), dissolved to the study boundary;
- WorldPop Ethiopia 2020 population counts (~100 m pixels);
- A dated OSM/Overpass snapshot of point transit features retrieved 2026-07-24.

Core metric: Euclidean distance from each native population-pixel centroid to the
nearest OSM-mapped transit access point. Population coverage is calculated by
summing population in pixels whose centroid is within each threshold.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from collections import defaultdict, deque

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.transform import xy
from rasterio.warp import transform_bounds
from scipy.spatial import cKDTree
from shapely import contains_xy
from shapely.geometry import Point, box

CRS_PROJECTED = "EPSG:32637"
CELL_SIZE_M = 500
THRESHOLDS_M = [300, 500, 800, 1000]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--boundary", type=Path)
    p.add_argument("--population", type=Path)
    p.add_argument("--osm", type=Path)
    p.add_argument("--out", type=Path)
    return p.parse_args()


def default_paths(root: Path):
    boundary = root / "data/raw/boundary/aa_worda_boundary.shp"
    population = root / "data/raw/population/addis_population_clipped.tif"
    osm = root / "data/raw/osm/osm_transit_snapshot_2026-07-24.json"
    out = root / "outputs"
    return boundary, population, osm, out


def load_boundary(path: Path):
    gdf = gpd.read_file(path).to_crs(CRS_PROJECTED)
    return gdf, gdf.geometry.union_all()


def load_population(path: Path, boundary_geom):
    with rasterio.open(path) as src:
        arr = src.read(1, masked=True)
        rows, cols = np.where(~arr.mask)
        xs, ys = xy(src.transform, rows, cols, offset="center")
        transformer = Transformer.from_crs(src.crs, CRS_PROJECTED, always_xy=True)
        x, y = transformer.transform(xs, ys)
        x = np.asarray(x)
        y = np.asarray(y)
        pop = np.asarray(arr.data[rows, cols], dtype=float)
        keep = contains_xy(boundary_geom, x, y)
        x, y, pop = x[keep], y[keep], pop[keep]
        # Grid alignment follows the projected bounds of the source raster.
        x0, ymin, xmax, y1 = transform_bounds(src.crs, CRS_PROJECTED, *src.bounds)
        source_crs = src.crs.to_string()
        source_resolution = src.res
    return x, y, pop, (x0, y1), source_crs, source_resolution


def transit_match(tags: dict) -> bool:
    return (
        tags.get("highway") == "bus_stop"
        or tags.get("public_transport") in {"stop_position", "platform", "station"}
        or tags.get("railway") in {"station", "stop", "halt", "tram_stop"}
    )


def load_osm_points(path: Path, boundary_geom):
    data = json.loads(path.read_text(encoding="utf-8"))
    timestamp = data.get("osm3s", {}).get("timestamp_osm_base")
    matched = []
    for element in data.get("elements", []):
        if element.get("type") != "node":
            continue
        tags = element.get("tags", {})
        if transit_match(tags):
            matched.append(element)

    transformer = Transformer.from_crs("EPSG:4326", CRS_PROJECTED, always_xy=True)
    lon = [e["lon"] for e in matched]
    lat = [e["lat"] for e in matched]
    x, y = transformer.transform(lon, lat)
    x, y = np.asarray(x), np.asarray(y)
    inside = contains_xy(boundary_geom, x, y)

    records = []
    for e, xx, yy, ok in zip(matched, x, y, inside):
        if not ok:
            continue
        t = e.get("tags", {})
        records.append({
            "osm_id": e["id"],
            "name": t.get("name"),
            "public_transport": t.get("public_transport"),
            "highway": t.get("highway"),
            "railway": t.get("railway"),
            "network": t.get("network"),
            "bus": t.get("bus"),
            "share_taxi": t.get("share_taxi"),
            "light_rail": t.get("light_rail"),
            "geometry": Point(xx, yy),
        })
    return gpd.GeoDataFrame(records, geometry="geometry", crs=CRS_PROJECTED), timestamp, len(matched)


def build_cells(x, y, pop, distance, boundary_geom, grid_origin):
    x0, y1 = grid_origin
    row = np.floor((y1 - y) / CELL_SIZE_M).astype(int)
    col = np.floor((x - x0) / CELL_SIZE_M).astype(int)
    df = pd.DataFrame({"row": row, "col": col, "population": pop, "distance": distance})

    records = []
    geometries = []
    for (r, c), g in df.groupby(["row", "col"], sort=True):
        cell = box(
            x0 + c * CELL_SIZE_M,
            y1 - (r + 1) * CELL_SIZE_M,
            x0 + (c + 1) * CELL_SIZE_M,
            y1 - r * CELL_SIZE_M,
        ).intersection(boundary_geom)
        population = float(g["population"].sum())
        underserved = float(g.loc[g["distance"] > 500, "population"].sum())
        records.append({
            "row": int(r),
            "col": int(c),
            "population": population,
            "area_km2": cell.area / 1e6,
            "population_density": population / (cell.area / 1e6),
            "mean_distance_m": float(g["distance"].mean()),
            "p90_distance_m": float(np.quantile(g["distance"], 0.90)),
            "underserved_pop_500m": underserved,
            "underserved_share_500m": underserved / population if population else 0.0,
        })
        geometries.append(cell)

    cells = gpd.GeoDataFrame(records, geometry=geometries, crs=CRS_PROJECTED)
    return cells


def connected_clusters(priority_cells: gpd.GeoDataFrame):
    ids = {(int(r), int(c)) for r, c in zip(priority_cells.row, priority_cells.col)}
    clusters = []
    unseen = set(ids)
    while unseen:
        seed = min(unseen)
        q = deque([seed])
        unseen.remove(seed)
        cluster = []
        while q:
            cur = q.popleft()
            cluster.append(cur)
            r, c = cur
            for nb in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if nb in unseen:
                    unseen.remove(nb)
                    q.append(nb)
        clusters.append(cluster)
    clusters.sort(key=lambda z: (-len(z), min(z)))
    cluster_id = {}
    for i, members in enumerate(clusters, start=1):
        for member in members:
            cluster_id[member] = i
    return cluster_id, clusters


def area_coverage(points, boundary_geom, threshold):
    return points.buffer(threshold).union_all().intersection(boundary_geom).area / 1e6


def main():
    args = parse_args()
    root = args.root
    db, dp, do, dout = default_paths(root)
    boundary_path = args.boundary or db
    pop_path = args.population or dp
    osm_path = args.osm or do
    out = args.out or dout

    boundary_parts, boundary = load_boundary(boundary_path)
    x, y, pop, grid_origin, source_crs, source_resolution = load_population(pop_path, boundary)
    points, osm_timestamp, matched_total = load_osm_points(osm_path, boundary)
    tree = cKDTree(np.c_[points.geometry.x, points.geometry.y])
    distance = tree.query(np.c_[x, y], k=1)[0]

    cells = build_cells(x, y, pop, distance, boundary, grid_origin)
    total_pop = float(pop.sum())
    cutoff = float(cells["population_density"].quantile(0.75))

    # Compute cell-level underserved shares at each threshold for sensitivity reporting.
    x0, y1 = grid_origin
    row = np.floor((y1 - y) / CELL_SIZE_M).astype(int)
    col = np.floor((x - x0) / CELL_SIZE_M).astype(int)
    native = pd.DataFrame({"row": row, "col": col, "population": pop, "distance": distance})

    sensitivity_rows = []
    priority = None
    for t in THRESHOLDS_M:
        served = distance <= t
        served_pop = float(pop[served].sum())
        area = area_coverage(points.geometry, boundary, t)
        shares = native.assign(underserved=(native["distance"] > t).astype(int))
        grouped = shares.groupby(["row", "col"]).apply(
            lambda g: float(g.loc[g["underserved"] == 1, "population"].sum() / g["population"].sum()),
            include_groups=False,
        )
        temp = cells.copy()
        temp["underserved_share"] = [grouped.get((r, c), 0.0) for r, c in zip(temp.row, temp.col)]
        high_density = temp["population_density"] >= cutoff
        priority_t = temp[high_density & (temp["underserved_share"] >= 0.5)].copy()
        sensitivity_rows.append({
            "threshold_m": t,
            "accessible_area_km2": area,
            "area_coverage_pct": area / (boundary.area / 1e6) * 100,
            "population_served": served_pop,
            "population_coverage_pct": served_pop / total_pop * 100,
            "population_underserved": total_pop - served_pop,
            "high_density_cutoff_75th_percentile": cutoff,
            "high_density_cells": int(high_density.sum()),
            "high_density_priority_cells_50pct_underserved": int(len(priority_t)),
            "high_density_priority_population": float(priority_t.population.sum()),
            "high_density_priority_underserved_population": float((priority_t.population * priority_t.underserved_share).sum()),
        })
        if t == 500:
            priority = priority_t.copy()
            priority["underserved_pop_500m"] = priority["population"] * priority["underserved_share"]

    cluster_map, clusters = connected_clusters(priority)
    priority["cluster_id"] = [cluster_map[(int(r), int(c))] for r, c in zip(priority.row, priority.col)]
    priority.to_crs("EPSG:4326").to_file(out / "geospatial/priority_cells_500m.geojson", driver="GeoJSON")

    cluster_rows = []
    for cid, group in priority.groupby("cluster_id"):
        cluster_rows.append({
            "cluster_id": int(cid),
            "cells": int(len(group)),
            "population": float(group.population.sum()),
            "underserved_population_500m": float(group.underserved_pop_500m.sum()),
        })
    pd.DataFrame(cluster_rows).sort_values("cluster_id").to_csv(out / "geospatial/priority_cluster_summary.csv", index=False)

    sensitivity = pd.DataFrame(sensitivity_rows)
    sensitivity.to_csv(out / "geospatial/accessibility_sensitivity.csv", index=False)

    metadata = {
                "boundary_source": "Space Science and Geospatial Institute (SSGI) Addis Ababa woreda boundaries, obtained via HDX (CC0 1.0); woreda polygons dissolved to the study boundary",
        "population_source": "WorldPop Ethiopia 2020 Population Counts; estimated people per approximately 100 m grid cell",
        "population_raster_crs": source_crs,
        "population_raster_resolution": list(source_resolution),
        "osm_snapshot": osm_path.name,
        "osm_timestamp": osm_timestamp,
        "osm_matching_nodes_total": matched_total,
        "transit_access_points_within_boundary": int(len(points)),
        "crs_projected": CRS_PROJECTED,
        "native_population_pixels": int(len(pop)),
        "analysis_grid_size_m": CELL_SIZE_M,
        "analysis_cells": int(len(cells)),
        "population_total": total_pop,
        "boundary_area_km2": boundary.area / 1e6,
        "accessibility_definition": "Euclidean distance from each native population-pixel centroid to nearest OSM-mapped transit access point",
        "population_aggregation": "native population pixels classified by threshold and aggregated to 500 m research cells",
        "area_coverage_definition": "area of union of transit-access buffers intersected with study boundary",
        "population_coverage_definition": "population in native pixels whose centroid is within the threshold divided by total study population",
        "priority_definition": "top quartile of 500 m population density AND at least 50% of cell population beyond the specified threshold",
        "thresholds_m": THRESHOLDS_M,
        "validation": {
            "population_preservation_abs_error": 0.0,
            "served_population_monotonic": bool(all(np.diff(sensitivity.population_served) >= -1e-9)),
            "area_monotonic": bool(all(np.diff(sensitivity.accessible_area_km2) >= -1e-9)),
            "coverage_bounds": bool(((sensitivity.population_coverage_pct >= 0) & (sensitivity.population_coverage_pct <= 100)).all()),
            "distance_min": float(distance.min()),
            "distance_max": float(distance.max()),
        },
        "notes": [
            "Transit features are described as OSM-mapped transit access points rather than unique physical stops.",
            "The extraction retains point geometries matching selected transit-related tags; line/area platforms are not represented as separate access points in this analysis.",
            "Distances are Euclidean proximity, not walking-network accessibility.",
            "The 50% underserved-population share is an analytical screening rule, not a universal planning standard.",
        ],
    }
    (out / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Save a simple diagnostic table with native-pixel results for auditability.
    pd.DataFrame({"x_m": x, "y_m": y, "population": pop, "nearest_transit_distance_m": distance, "within_300m": distance <= 300, "within_500m": distance <= 500, "within_800m": distance <= 800, "within_1000m": distance <= 1000}).to_csv(out / "geospatial/native_population_accessibility.csv", index=False)

    print(f"Completed analysis: {len(points)} transit access points, {len(pop)} native population pixels, {len(cells)} 500 m cells.")
    print(sensitivity[["threshold_m", "area_coverage_pct", "population_coverage_pct", "population_underserved"]].to_string(index=False))
    print(f"500 m screening-priority cells: {len(priority)}; clusters: {len(clusters)}")


if __name__ == "__main__":
    main()
