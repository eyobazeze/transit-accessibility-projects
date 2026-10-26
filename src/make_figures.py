"""Regenerate publication Figures 1-4 from the saved analysis outputs.

Usage (from the repository root):
    python src/make_figures.py [output_dir]

Inputs : outputs/geospatial/*.geojson|csv and data/raw/boundary/aa_worda_boundary.shp
Outputs: Fig1_study_area_transit.png, Fig2_nearest_transit_distance.png,
         Fig3_priority_clusters.png, Fig4_threshold_sensitivity.png (default: outputs/figures)
No analysis is recomputed here; the figures only display the saved results.
"""
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parent.parent
GEO = ROOT / "outputs" / "geospatial"
BOUNDARY = ROOT / "data" / "raw" / "boundary" / "aa_worda_boundary.shp"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs" / "figures"
CRS = "EPSG:32637"
DPI = 300
plt.rcParams["font.family"] = "DejaVu Sans"
BLUE, GREY, RED, ACCENT = "#1f77b4", "#d9d9d9", "#d62728", "#ff7f00"


def load():
    boundary = gpd.read_file(BOUNDARY).to_crs(CRS)
    # Dissolve the woredas and keep only the outer ring(s): tiny interior gaps/slivers between
    # woreda polygons would otherwise be drawn as stray lines. Analysis uses the saved outputs only.
    from shapely.geometry import MultiPolygon, Polygon
    u = boundary.union_all()
    polys = list(u.geoms) if isinstance(u, MultiPolygon) else [u]
    outline = gpd.GeoSeries([MultiPolygon([Polygon(p.exterior) for p in polys])], crs=CRS)
    cells = gpd.read_file(GEO / "population_access_cells_500m.geojson").to_crs(CRS)
    priority = gpd.read_file(GEO / "priority_cells_500m.geojson").to_crs(CRS)
    stops = gpd.read_file(GEO / "transit_access_points.geojson").to_crs(CRS)
    return outline, cells, priority, stops


MAP_SIZE = (10.4, 10.4)  # identical canvas for Figs 1-3


def base(outline, title, figsize=MAP_SIZE, fill=GREY):
    fig, ax = plt.subplots(figsize=figsize, dpi=DPI)
    outline.plot(ax=ax, facecolor=fill, edgecolor="none", zorder=0)  # grey = no population data (maps 2-3)
    ax.set_aspect("equal")
    ax.set_axis_off()
    fig.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.02)
    ax.set_title(title, fontsize=18, pad=8)
    return fig, ax


def finish_map(ax, outline):
    outline.boundary.plot(ax=ax, color="black", linewidth=0.8, zorder=6)
    minx, miny, maxx, maxy = outline.total_bounds
    # scale bar: 5 km, lower right, thin line with end ticks and "0" / "5 km" labels
    x0, y0 = maxx - 5000, miny - 1800
    ax.plot([x0, x0 + 5000], [y0, y0], color="black", linewidth=1.4, zorder=7)
    for xt in (x0, x0 + 5000):
        ax.plot([xt, xt], [y0 - 280, y0 + 280], color="black", linewidth=1.4, zorder=7)
    ax.text(x0, y0 - 500, "0", ha="center", va="top", fontsize=13, zorder=7)
    ax.text(x0 + 5000, y0 - 500, "5 km", ha="center", va="top", fontsize=13, zorder=7)
    ax.set_ylim(y0 - 1800, maxy + 500)
    # north arrow: upper right
    nx, ny = minx + 2500, maxy - 800
    ax.annotate("", xy=(nx, ny), xytext=(nx, ny - 3200),
                arrowprops=dict(arrowstyle="-|>", color="black", lw=1.8), zorder=7)
    ax.text(nx, ny + 400, "N", ha="center", va="bottom", fontsize=16, fontweight="bold", zorder=7)


def fig1(outline, stops):
    fig, ax = base(outline, "Study Area and OSM-Mapped Transit Access Points", fill="white")
    stops.plot(ax=ax, color=BLUE, markersize=5, alpha=0.6, linewidth=0, zorder=3)
    finish_map(ax, outline)
    ax.legend(handles=[
        Line2D([0], [0], marker="o", color="none", markerfacecolor=BLUE, alpha=0.8, markersize=6,
               label=f"OSM transit access point\n(n = {len(stops):,})"),
        Line2D([0], [0], color="black", lw=1, label="Study boundary\n(dissolved woredas)")],
        loc="lower left", bbox_to_anchor=(0.0, 0.05), frameon=False, fontsize=14)
    return fig


def grouped_legend(ax, groups, **kw):
    """Legend with bold group headings. groups = [(heading, [handles...]), ...]"""
    handles, headers = [], []
    for heading, hs in groups:
        headers.append(len(handles))
        handles.append(Patch(facecolor="none", edgecolor="none", label=heading))
        handles.extend(hs)
    leg = ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(-0.01, 0.03), frameon=False,
                    fontsize=13, handlelength=1.6, **kw)
    for i in headers:
        leg.get_texts()[i].set_fontweight("bold")
        leg.get_texts()[i].set_fontsize(12.5)
    return leg


def fig2(outline, cells):
    # Band edges are the paper's own proximity thresholds (300, 500, 800, 1,000 m); no other breaks.
    bins = [0, 300, 500, 800, 1000, np.inf]
    cols = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"]  # ColorBrewer YlOrRd, 5 classes
    labels = ["< 300", "300-500", "500-800", "800-1,000", "> 1,000"]
    cmap, norm = ListedColormap(cols), BoundaryNorm(bins, len(cols))
    fig, ax = base(outline, "Cell-Level Mean Distance to the Nearest OSM-Mapped Transit Access Point")
    cells.plot(ax=ax, column="mean_distance_m", cmap=cmap, norm=norm, linewidth=0, zorder=2)
    finish_map(ax, outline)
    grouped_legend(ax, [("Cell mean distance (m)", [Patch(facecolor=c, label=l) for c, l in zip(cols, labels)]),
                        ("Other", [Patch(facecolor=GREY, label="No population data")])])
    return fig


def fig3(outline, cells, priority):
    """Emphasis design: quiet single-hue density base (quartile classes), priority cells in an accent colour."""
    fig, ax = base(outline, "Population Density and Screening-Priority Clusters")
    d = cells.population_density
    q1, q2, q3 = np.percentile(d, [25, 50, 75])  # quartiles of the research-cell densities; q3 = priority cut-off
    bins = [0, q1, q2, q3, np.inf]
    cols = ["#eff3ff", "#bdd7e7", "#6baed6", "#2171b5"]  # ColorBrewer Blues, 4 classes
    f = lambda v: f"{v:,.0f}"
    labels = [f"< {f(q1)}", f"{f(q1)}-{f(q2)}", f"{f(q2)}-{f(q3)}", f">= {f(q3)} (top quartile)"]
    cmap, norm = ListedColormap(cols), BoundaryNorm(bins, len(cols))
    cells.plot(ax=ax, column="population_density", cmap=cmap, norm=norm, linewidth=0, zorder=2)
    priority.plot(ax=ax, facecolor=ACCENT, edgecolor="black", linewidth=0.6, zorder=4)
    for cid, g in priority.groupby("cluster_id"):
        c = g.union_all().centroid
        ax.text(c.x + 450, c.y + 450, str(int(cid)), fontsize=12, fontweight="bold", color="black",
                ha="center", va="center", zorder=8,
                path_effects=[pe.withStroke(linewidth=2.4, foreground="white")])
    finish_map(ax, outline)
    ncl = priority.cluster_id.nunique()
    grouped_legend(ax, [
        ("Density (people/km²)", [Patch(facecolor=c, label=l) for c, l in zip(cols, labels)]),
        ("Screening-priority cell", [Patch(facecolor=ACCENT, edgecolor="black", linewidth=0.6,
            label=f"n = {len(priority)}; top-quartile density\nand >= 50% of residents\nbeyond 500 m")]),
        ("Other", [Patch(facecolor=GREY, label="No population data")])])
    return fig


def fig4():
    d = pd.read_csv(GEO / "accessibility_sensitivity.csv")
    x, y = d.threshold_m.tolist(), d.population_coverage_pct.tolist()
    fig, ax = plt.subplots(figsize=(9.86, 6.52), dpi=DPI)
    ax.plot(x, y, marker="o", linewidth=2.5, markersize=8, color=BLUE)
    for xi, yi in zip(x, y):
        ax.annotate(f"{yi:.1f}%", (xi, yi), textcoords="offset points", xytext=(0, 12), ha="center", fontsize=13)
    ax.set_ylim(0, 108)
    ax.set_yticks(range(0, 101, 20))
    ax.set_xlim(250, 1050)
    ax.set_xticks(range(300, 1001, 100))
    ax.set_xlabel("Euclidean proximity threshold (m)", fontsize=13.25)
    ax.set_ylabel("Population coverage (%)", fontsize=13.25)
    ax.set_title("Sensitivity of Population Coverage to Distance Threshold", fontsize=18.6)
    ax.grid(alpha=0.3)
    ax.tick_params(labelsize=12.8)
    fig.tight_layout()
    return fig


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    outline, cells, priority, stops = load()
    for name, fig in [("Fig1_study_area_transit.png", fig1(outline, stops)),
                      ("Fig2_nearest_transit_distance.png", fig2(outline, cells)),
                      ("Fig3_priority_clusters.png", fig3(outline, cells, priority)),
                      ("Fig4_threshold_sensitivity.png", fig4())]:
        fig.savefig(OUT / name, dpi=DPI, facecolor="white")
        plt.close(fig)
        print("saved", OUT / name)


if __name__ == "__main__":
    main()
