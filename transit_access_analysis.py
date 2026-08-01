"""
Transit Access & Underserved Areas in Addis Ababa
==================================================
Author: Eyob Azeze Negussie
Description:
    Spatial analysis of public transit accessibility in Addis Ababa.
    Fetches bus stops and transit infrastructure from OpenStreetMap,
    creates 500m walkability buffers, and identifies underserved areas
    using population density data.

Tools: GeoPandas, OSMnx, Folium, Contextily
Data Sources:
    - OpenStreetMap (transit stops, routes)
    - WorldPop / HDX (population density)
"""

import geopandas as gpd
import osmnx as ox
import folium
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import contextily as ctx
from shapely.geometry import Point
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ── 1. Define Study Area ───────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1: Defining study area — Addis Ababa, Ethiopia")
print("=" * 60)

CITY = "Addis Ababa, Ethiopia"
CRS_PROJECTED = "EPSG:32637"   # UTM Zone 37N — accurate for Ethiopia
CRS_WGS84     = "EPSG:4326"    # WGS84 — for web maps

# ── 2. Fetch City Boundary ─────────────────────────────────────────────────────
print("\nSTEP 2: Fetching city boundary from OpenStreetMap...")
try:
    city_boundary = ox.geocode_to_gdf(CITY)
    city_boundary = city_boundary.to_crs(CRS_PROJECTED)
    print(f"  ✓ City boundary loaded: {city_boundary.geometry.area.sum() / 1e6:.1f} km²")
except Exception as e:
    print(f"  ✗ Could not fetch boundary: {e}")
    city_boundary = None

# ── 3. Fetch Transit Stops from OSM ───────────────────────────────────────────
print("\nSTEP 3: Fetching transit stops from OpenStreetMap...")

tags = {
    "highway": "bus_stop",
    "public_transport": ["stop_position", "platform"],
    "railway": ["station", "stop", "halt", "tram_stop"]
}

try:
    stops_gdf = ox.features_from_place(CITY, tags=tags)
    # Keep only point geometries (stops, not route polygons)
    stops_gdf = stops_gdf[stops_gdf.geometry.geom_type.isin(["Point"])].copy()
    stops_gdf = stops_gdf.to_crs(CRS_PROJECTED)
    stops_gdf = stops_gdf.reset_index(drop=True)
    print(f"  ✓ Transit stops loaded: {len(stops_gdf)} stops found")
except Exception as e:
    print(f"  ✗ OSM fetch failed: {e}")
    # Fallback: key known LRT & bus hubs as sample points (WGS84)
    print("  → Using representative transit hub coordinates as fallback")
    known_stops = [
        {"name": "Legehar LRT Station",    "lat": 9.0192, "lon": 38.7525, "type": "LRT"},
        {"name": "Meskel Square Station",  "lat": 9.0105, "lon": 38.7614, "type": "LRT"},
        {"name": "Stadium LRT Station",    "lat": 9.0235, "lon": 38.7470, "type": "LRT"},
        {"name": "Torhailoch Station",     "lat": 8.9731, "lon": 38.7448, "type": "LRT"},
        {"name": "Lideta Station",         "lat": 9.0097, "lon": 38.7374, "type": "LRT"},
        {"name": "Kolfe Station",          "lat": 9.0261, "lon": 38.7130, "type": "LRT"},
        {"name": "Ayat Station",           "lat": 9.0381, "lon": 38.8320, "type": "LRT"},
        {"name": "Meri Station",           "lat": 9.0650, "lon": 38.8050, "type": "LRT"},
        {"name": "Piassa Bus Terminal",    "lat": 9.0360, "lon": 38.7490, "type": "Bus"},
        {"name": "Merkato Bus Terminal",   "lat": 9.0350, "lon": 38.7290, "type": "Bus"},
        {"name": "Megenagna Bus Stop",     "lat": 9.0210, "lon": 38.8010, "type": "Bus"},
        {"name": "Bole Bus Terminal",      "lat": 8.9963, "lon": 38.7893, "type": "Bus"},
        {"name": "CMC Bus Stop",           "lat": 9.0560, "lon": 38.8030, "type": "Bus"},
        {"name": "Saris Bus Stop",         "lat": 9.0060, "lon": 38.7180, "type": "Bus"},
        {"name": "Kality Bus Terminal",    "lat": 8.9390, "lon": 38.7460, "type": "Bus"},
        {"name": "Gotera Bus Stop",        "lat": 8.9890, "lon": 38.7610, "type": "Bus"},
        {"name": "Summit Bus Stop",        "lat": 8.9960, "lon": 38.8120, "type": "Bus"},
        {"name": "Mekanisa Bus Stop",      "lat": 8.9810, "lon": 38.7230, "type": "Bus"},
        {"name": "Lamberet Bus Stop",      "lat": 9.0480, "lon": 38.7700, "type": "Bus"},
        {"name": "Ayer Tena Bus Stop",     "lat": 8.9580, "lon": 38.7220, "type": "Bus"},
        {"name": "Shiro Meda Bus Stop",    "lat": 9.0610, "lon": 38.7490, "type": "Bus"},
        {"name": "Akaki Bus Terminal",     "lat": 8.9030, "lon": 38.7950, "type": "Bus"},
        {"name": "Bole Bulbula Stop",      "lat": 8.9700, "lon": 38.8080, "type": "Bus"},
        {"name": "Mexico Bus Stop",        "lat": 9.0150, "lon": 38.7470, "type": "Bus"},
        {"name": "Hayahulet Bus Stop",     "lat": 9.0070, "lon": 38.7680, "type": "Bus"},
    ]
    stops_df = pd.DataFrame(known_stops)
    geometry = [Point(xy) for xy in zip(stops_df.lon, stops_df.lat)]
    stops_gdf = gpd.GeoDataFrame(stops_df, geometry=geometry, crs=CRS_WGS84)
    stops_gdf = stops_gdf.to_crs(CRS_PROJECTED)
    print(f"  ✓ Fallback stops loaded: {len(stops_gdf)} major hubs")

# ── 4. Create 500m Walkability Buffers ────────────────────────────────────────
print("\nSTEP 4: Creating 500m walkability buffers around transit stops...")
BUFFER_DISTANCE = 500  # metres — standard pedestrian shed

stops_gdf["buffer"] = stops_gdf.geometry.buffer(BUFFER_DISTANCE)
buffers_gdf = stops_gdf.set_geometry("buffer")

# Dissolve overlapping buffers into a single served area polygon
served_area = buffers_gdf.dissolve().reset_index(drop=True)
served_area_km2 = served_area.geometry.area.sum() / 1e6
print(f"  ✓ Total area within 500m of transit: {served_area_km2:.1f} km²")

# ── 5. Load Real Population Data from WorldPop ────────────────────────────────
print("\nSTEP 5: Loading real population density from WorldPop raster...")

PROJECT_ROOT = BASE_DIR

CLIPPED_RASTER_4326 = PROJECT_ROOT / "data" / "processed" / "addis_population_clipped.tif"
REPROJECTED_RASTER  = PROJECT_ROOT / "data" / "processed" / "addis_population_utm.tif"


# Reproject the clipped raster from EPSG:4326 to EPSG:32637 (meters) —
# only needs to run once; skip if the file already exists
if not REPROJECTED_RASTER.exists():
    with rasterio.open(CLIPPED_RASTER_4326) as src:
        transform, width, height = calculate_default_transform(
            src.crs, CRS_PROJECTED, src.width, src.height, *src.bounds
        )
        kwargs = src.meta.copy()
        kwargs.update({"crs": CRS_PROJECTED, "transform": transform, "width": width, "height": height})

        with rasterio.open(REPROJECTED_RASTER, "w", **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=transform, dst_crs=CRS_PROJECTED,
                resampling=Resampling.nearest
            )
    print("  ✓ Raster reprojected to EPSG:32637")

# Build the same 500m grid as before (same bounds logic you already had)
if city_boundary is not None:
    bounds = city_boundary.total_bounds
else:
    bounds = [460000, 985000, 510000, 1030000]

grid_size = 500
x_coords = np.arange(bounds[0], bounds[2], grid_size)
y_coords = np.arange(bounds[1], bounds[3], grid_size)
xx, yy = np.meshgrid(x_coords, y_coords)

# Sample the REAL raster at each grid point, instead of the fake formula
with rasterio.open(REPROJECTED_RASTER) as src:
    res_x, res_y = src.res
    pixel_area_km2 = (res_x * res_y) / 1_000_000

    sample_points = list(zip(xx.flatten(), yy.flatten()))
    raw_values = np.array([v[0] for v in src.sample(sample_points)])

    # Nodata / negative values (e.g. outside the raster's real extent) -> 0
    population_count = np.where(raw_values > 0, raw_values, 0)
    density = population_count / pixel_area_km2   # people per km^2, same units your script already expects

# Convert to GeoDataFrame — identical structure to what Section 6-8 already expect
points = [Point(x, y) for x, y in zip(xx.flatten(), yy.flatten())]
pop_grid = gpd.GeoDataFrame({
    "geometry": points,
    "population_density": density
}, crs=CRS_PROJECTED)

if city_boundary is not None:
    pop_grid = gpd.clip(pop_grid, city_boundary)
    pop_grid.to_file(DATA_DIR / "processed" / "population_grid_full.geojson", driver="GeoJSON")
    print(f"  ✓ Full population grid exported: {len(pop_grid)} cells")

print(f"  ✓ Population grid created from real WorldPop data: {len(pop_grid):,} cells")
print(f"  ✓ Mean density: {pop_grid['population_density'].mean():.0f} people/km²")

# ── 6. Identify Underserved Areas ─────────────────────────────────────────────
print("\nSTEP 6: Identifying underserved high-density areas...")

# Tag each grid cell: served vs underserved
pop_grid["served"] = pop_grid.geometry.within(served_area.geometry.union_all())
served_pop   = pop_grid[pop_grid["served"]]
unserved_pop = pop_grid[~pop_grid["served"]]

HIGH_DENSITY_THRESHOLD = 8000  # people per km²
underserved_high_density = unserved_pop[unserved_pop["population_density"] > HIGH_DENSITY_THRESHOLD]

print(f"  ✓ Grid cells served by transit:          {len(served_pop):,}")
print(f"  ✓ Grid cells NOT served by transit:      {len(unserved_pop):,}")
print(f"  ✓ High-density underserved cells:        {len(underserved_high_density):,}")
if len(pop_grid) > 0:
    pct = len(served_pop) / len(pop_grid) * 100
    print(f"  ✓ Coverage rate:                         {pct:.1f}% of city area")

# ── 7. Static Map ─────────────────────────────────────────────────────────────
print("\nSTEP 7: Generating static choropleth map...")

fig, axes = plt.subplots(1, 2, figsize=(18, 9))
fig.patch.set_facecolor("#1a1a2e")

for ax in axes:
    ax.set_facecolor("#1a1a2e")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("#444")

# --- Left panel: Transit coverage map ---
ax1 = axes[0]

if city_boundary is not None:
    city_boundary.to_crs("EPSG:3857").boundary.plot(ax=ax1, color="#555", linewidth=1)

# Population grid
pop_grid.to_crs("EPSG:3857").plot(
    ax=ax1, column="population_density",
    cmap="YlOrRd", alpha=0.6, markersize=2, legend=False
)

# Served area — dissolved territory, solid fill (reads as coverage, not a route network)
served_area.to_crs("EPSG:3857").plot(
    ax=ax1, color="#00b4d8", alpha=0.35, linewidth=0
)
served_area.to_crs("EPSG:3857").boundary.plot(
    ax=ax1, color="#00b4d8", linewidth=0.8
)

# Transit stops
stops_gdf.to_crs("EPSG:3857").plot(
    ax=ax1, color="#ffffff", markersize=18, marker="o", zorder=5,
    edgecolor="#00b4d8", linewidth=0.8
)

try:
    ctx.add_basemap(ax1, crs="EPSG:3857", source=ctx.providers.CartoDB.DarkMatter, alpha=0.5)
except:
    pass

ax1.set_title("Transit Coverage — 500m Walkability Buffers",
              color="white", fontsize=13, fontweight="bold", pad=20)
ax1.set_axis_off()

# Legend
legend_elements = [
    mpatches.Patch(facecolor="#00b4d8", alpha=0.4, label="500m transit buffer"),
    plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="white",
               markeredgecolor="#00b4d8", markersize=7, label="Transit stop / hub"),
]
ax1.legend(handles=legend_elements, loc="lower left",
           facecolor="#111", edgecolor="#444", labelcolor="white", fontsize=9)

# --- Right panel: Underserved areas ---
ax2 = axes[1]

if city_boundary is not None:
    city_boundary.to_crs("EPSG:3857").boundary.plot(ax=ax2, color="#555", linewidth=1)

served_pop.to_crs("EPSG:3857").plot(
    ax=ax2, color="#2d6a4f", alpha=0.3, markersize=3
)
unserved_pop.to_crs("EPSG:3857").plot(
    ax=ax2, color="#e76f51", alpha=0.25, markersize=3
)
# Underserved high-density cells buffered into visible circles instead of tiny points —
# these are the headline finding, so they need to read clearly at feed/thumbnail size
underserved_high_density_buffered = underserved_high_density.copy()
underserved_high_density_buffered["geometry"] = underserved_high_density.geometry.buffer(180)
underserved_high_density_buffered.to_crs("EPSG:3857").plot(
    ax=ax2, color="#e63946", alpha=0.9, edgecolor="#ffffff", linewidth=0.3
)

try:
    ctx.add_basemap(ax2, crs="EPSG:3857", source=ctx.providers.CartoDB.DarkMatter, alpha=0.5)
except:
    pass

ax2.set_title("Underserved High-Density Areas",
              color="white", fontsize=13, fontweight="bold", pad=20)
ax2.set_axis_off()

legend2 = [
    mpatches.Patch(facecolor="#2d6a4f", alpha=0.7, label="Served area"),
    mpatches.Patch(facecolor="#e76f51", alpha=0.5, label="Underserved area"),
    mpatches.Patch(facecolor="#e63946", alpha=0.9, label="High-density underserved (>8k/km²)"),
]
ax2.legend(handles=legend2, loc="lower left",
           facecolor="#111", edgecolor="#444", labelcolor="white", fontsize=9)

# Reserve headroom above the panels so the suptitle, stat callout, and panel
# titles each get their own vertical band. Using subplots_adjust (not
# tight_layout) here because tight_layout doesn't reliably account for
# suptitle/figtext elements placed above the top of the axes.
fig.subplots_adjust(top=0.80, bottom=0.05)

# Title stack, evenly spaced top-down: main title -> stat callout -> panel titles.
# All three use figure-fraction y-coordinates (0-1), spaced 0.05 apart, which is
# safe regardless of final saved size since savefig below uses a fixed pad_inches
# instead of bbox_inches="tight" auto-cropping around text extents.
fig.text(0.5, 0.97, "Public Transit Accessibility Analysis — Addis Ababa, Ethiopia",
          ha="center", va="top", color="white", fontsize=16, fontweight="bold")

coverage_pct = len(served_pop) / len(pop_grid) * 100 if len(pop_grid) > 0 else 0
underserved_n = len(underserved_high_density)
fig.text(0.5, 0.905,
    f"{coverage_pct:.1f}% of grid area within 500m of transit  ·  "
    f"{underserved_n:,} high-density cells underserved",
    ha="center", va="top", color="#e63946", fontsize=13, fontweight="bold")

fig.text(0.5, 0.02,
    "Data: OpenStreetMap, WorldPop | Analysis: GeoPandas, OSMnx | Author: Eyob Azeze Negussie",
    ha="center", va="bottom", color="#888", fontsize=9
)

map_path = OUTPUT_DIR / "transit_access_map.png"
plt.savefig(map_path, dpi=150, pad_inches=0.15,
            facecolor="#1a1a2e", edgecolor="none")
plt.close()
print(f"  ✓ Static map saved → {map_path}")

# ── 8. Interactive Folium Map ──────────────────────────────────────────────────
print("\nSTEP 8: Generating interactive Folium web map...")

center_lat, center_lon = 9.0200, 38.7500
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles="CartoDB dark_matter"
)

# Transit stop markers
for _, row in stops_gdf.to_crs(CRS_WGS84).iterrows():
    name = row.get("name", row.get("name_en", "Transit Stop"))
    stop_type = row.get("type", row.get("railway", row.get("highway", "Stop")))
    color = "#00b4d8" if str(stop_type).lower() in ["lrt", "station", "tram_stop"] else "#90e0ef"
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.9,
        popup=folium.Popup(f"<b>{name}</b><br>Type: {stop_type}", max_width=200),
        tooltip=str(name)
    ).add_to(m)

# 500m buffer zones
buffers_wgs = buffers_gdf.to_crs(CRS_WGS84)
buffers_wgs = buffers_wgs.set_geometry("buffer")
buffers_poly = gpd.GeoDataFrame(geometry=buffers_wgs.geometry, crs=CRS_WGS84)
folium.GeoJson(
    buffers_poly.__geo_interface__,
    style_function=lambda x: {
        "fillColor": "#00b4d8", "color": "#00b4d8",
        "weight": 1, "fillOpacity": 0.15
    },
    name="500m Transit Buffers",
    tooltip="500m walkability zone"
).add_to(m)

# Underserved high-density areas — convert points to small circles via buffer
if len(underserved_high_density) > 0:
    uhd_wgs = underserved_high_density.to_crs(CRS_WGS84)
    uhd_poly = gpd.GeoDataFrame(
        geometry=underserved_high_density.geometry.buffer(250).to_crs(CRS_WGS84),
        crs=CRS_WGS84
    )
    folium.GeoJson(
        uhd_poly.__geo_interface__,
        style_function=lambda x: {
            "fillColor": "#e63946", "color": "#e63946",
            "weight": 0.5, "fillOpacity": 0.6
        },
        name="High-Density Underserved Areas",
        tooltip="Underserved high-density area"
    ).add_to(m)

folium.LayerControl().add_to(m)

# Legend
legend_html = """
<div style="position:fixed; bottom:30px; left:30px; z-index:1000;
     background:#1a1a2e; padding:14px 18px; border-radius:10px;
     border:1px solid #333; color:white; font-size:12px; font-family:sans-serif;">
  <b style="font-size:13px;">Transit Accessibility</b><br>
  <b style="color:#888; font-size:10px;">Addis Ababa, Ethiopia</b><br><br>
  <span style="color:#00b4d8;">●</span> Transit stop / hub<br>
  <span style="color:#00b4d8; opacity:0.5;">■</span> 500m walkability buffer<br>
  <span style="color:#e63946;">■</span> High-density underserved area<br><br>
  <span style="color:#888; font-size:10px;">Data: OpenStreetMap | Author: Eyob Azeze</span>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

folium_path = OUTPUT_DIR / "transit_access_interactive.html"
m.save(str(folium_path))
print(f"  ✓ Interactive map saved → {folium_path}")

# ── 9. Summary Statistics ──────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("ANALYSIS SUMMARY")
print("=" * 60)
print(f"  City:                     Addis Ababa, Ethiopia")
print(f"  Total transit stops:      {len(stops_gdf)}")
print(f"  Buffer radius:            {BUFFER_DISTANCE}m (standard walkability shed)")
print(f"  Area served by transit:   {served_area_km2:.1f} km²")
if len(pop_grid) > 0:
    print(f"  Population grid cells:    {len(pop_grid):,}")
    print(f"  Cells served:             {len(served_pop):,} ({len(served_pop)/len(pop_grid)*100:.1f}%)")
    print(f"  Cells underserved:        {len(unserved_pop):,} ({len(unserved_pop)/len(pop_grid)*100:.1f}%)")
    print(f"  High-density underserved: {len(underserved_high_density):,} cells")
print("=" * 60)
print("\n✓ Analysis complete. Outputs saved to /outputs/")
print("  → transit_access_map.png         (static publication map)")
print("  → transit_access_interactive.html (interactive web map)")