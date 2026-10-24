# Population-Weighted Transit Proximity in Addis Ababa

A reproducible spatial analysis of population proximity to **OSM-mapped public transit access points** in Addis Ababa, Ethiopia.

> **Paper:** *Population-Weighted Proximity to Mapped Public Transit in Addis Ababa: A Spatial Analysis Using Gridded Population and OpenStreetMap Data*

## Research question

**Where in Addis Ababa do high-density areas have relatively poor proximity to mapped public transit?**

The study deliberately measures **Euclidean proximity to mapped transit access points**, not full transport accessibility. It does not estimate walking time, service quality, destination accessibility, or whether a location is adequately served.

## Main results

| Threshold | Area coverage | Population coverage | Estimated population beyond threshold |
|---:|---:|---:|---:|
| 300 m | 27.9% | 46.7% | 2.466 million |
| **500 m** | **48.4%** | **75.4%** | **1.137 million** |
| 800 m | 67.4% | 91.8% | 0.377 million |
| 1,000 m | 75.1% | 95.4% | 0.212 million |

At 500 m, 60 high-density screening-priority cells were identified. Together they contain approximately 272,072 estimated people, of whom approximately 205,654 are beyond 500 m from an OSM-mapped transit access point. The 60 cells form 32 four-neighbor contiguous groups.

## Data

### Population

- **Source:** WorldPop Global 2015–2030 constrained population counts, release R2025A v1, year 2026 (file `eth_pop_2026_CN_100m_R2025A_v1.tif`; the repository holds a clip of it, `addis_population_clipped.tif`)
- Approximate resolution: 100 m (3 arc-seconds)
- Constrained product: unsettled pixels are NoData (about 8% of pixels inside the study boundary)
- Population values represent **estimated people per grid cell**.
- Citation: Bondarenko et al. (2026), DOI: https://doi.org/10.5258/SOTON/WP00839 (WorldPop describes R2025A v1 as an early release that may change)

The analysis uses the native population pixels and preserves their total population count. Population pixels are classified by their Euclidean distance to the nearest transit access point and then aggregated to 500 m research cells.

### Administrative boundary

- **Dataset:** Ethiopia – Addis Ababa subcities and woredas (resource `aa_worda_boundary.zip`)
- **Source:** Space Science and Geospatial Institute (SSGI); contributed to the Humanitarian Data Exchange (HDX) by 3iS
- **URL:** https://data.humdata.org/dataset/ethiopia-addis-ababa-subcities-and-woredas (HDX dataset ID `8d82f1ca-5a1d-4e73-9fea-8e53c190869d`), downloaded 6 July 2026
- **Licence:** CC0 1.0 (Public Domain)
- 116 woredas in 10 sub-cities; the woreda-level polygons are dissolved to produce the Addis Ababa study boundary.
- This is not the OCHA COD-AB boundary set. The HDX record cautions that the dataset does not fit the woreda boundaries in shapefiles shared by OCHA.

The resulting study boundary is approximately **519.5 km²**.

### Public transit

- **Source:** OpenStreetMap via an Overpass snapshot
- **Snapshot timestamp:** 2026-07-24T10:57:40Z
- 2,417 matching OSM nodes were found in the snapshot; 2,414 fell inside the study boundary.
- Matching tags include `highway=bus_stop`, `public_transport=platform`, `public_transport=stop_position`, `public_transport=station`, `railway=station`, `railway=stop`, `railway=halt`, and `railway=tram_stop`.

The analysis retains **point geometries** matching the selected transit-related tags. It therefore does not represent every possible OSM transit feature: platforms mapped only as ways/areas are not separately represented as point access locations.

OSM data is available under the Open Database License (ODbL). See https://www.openstreetmap.org/copyright.

## Method

1. Dissolve woreda-level boundary data to a fixed Addis Ababa study boundary.
2. Extract the selected point transit features from the dated OSM/Overpass snapshot.
3. Transform the WorldPop population-pixel centroids to EPSG:32637 while preserving the original population values.
4. Calculate Euclidean distance from every native population-pixel centroid to its nearest OSM-mapped transit access point.
5. Evaluate 300 m, 500 m, 800 m, and 1,000 m thresholds.
6. Aggregate population and accessibility measures to 500 m research cells.
7. Calculate population coverage and area coverage separately.
8. Define screening-priority cells as cells in the top quartile of population density with at least 50% of their population beyond the specified threshold.
9. Group 500 m screening-priority cells using four-neighbor contiguity. This is descriptive clustering, not a statistical spatial-autocorrelation test.

### Population-weighted proximity

In this project, **population-weighted proximity** means that threshold coverage is weighted by the estimated population associated with each native raster pixel. It does **not** mean that the study calculates a population-weighted mean distance.

For threshold \(T\):

\[
C_T = \frac{\sum_i P_i I(d_i \leq T)}{\sum_i P_i} \times 100
\]

where \(P_i\) is estimated population and \(d_i\) is Euclidean distance to the nearest mapped transit access point.

## Important interpretation limits

This project should **not** be described as a complete measure of public transport accessibility.

- Euclidean distance is not walking-network distance.
- The 500 m scenario is not the UN SDG 11.2.1 indicator.
- The analysis does not measure service frequency, capacity, reliability, fares, crowding, operating hours, route destinations, or pedestrian safety.
- OSM completeness and tagging can affect the mapped transit supply.
- The WorldPop population surface is a 2026 modeled estimate from an early (v1) release that may be revised; the OSM snapshot reflects one date (24 July 2026).
- The screening-priority thresholds are analytical choices, not universal planning standards.
- Each native population raster cell is represented by its centroid for the proximity calculation; the estimated population in that cell is therefore treated as associated with that representative location.
- The identified priority areas are **screening locations for further investigation**, not direct recommendations for new routes or stops.

## Repository structure

```text
.
├── data/
│   └── raw/
│       ├── boundary/          # SSGI boundary (via HDX, CC0) used in the analysis
│       ├── osm/               # dated OSM/Overpass snapshot
│       └── population/        # WorldPop population raster used in the analysis
├── outputs/
│   ├── figures/               # publication figures
│   ├── geospatial/            # derived GeoJSON/CSV outputs
│   └── analysis_metadata.json
├── src/
│   └── transit_access_analysis.py
├── CITATION.cff
├── DATA_SOURCES.md
├── requirements.txt
├── docs/
│   └── REPRODUCIBILITY_NOTES.md
└── README.md
```

## Reproduce the analysis

Create an environment with Python 3.10+ and install the dependencies:

```bash
pip install -r requirements.txt
```

Then run:

```bash
python src/transit_access_analysis.py
```

The script writes the reproducibility outputs to `outputs/geospatial/` and `outputs/analysis_metadata.json`. The publication figures in `outputs/figures/` are the figures used in the working paper. They are regenerated from the saved outputs (no analysis is recomputed) with:

```bash
python src/make_figures.py
```

Density classes in Figure 3 are quartiles of the 2,155 research-cell densities, and the colour bands in Figure 2 follow the paper's proximity thresholds (300, 500, 800 and 1,000 m).

## Validation checks

The workflow checks that:

- population is preserved to floating-point precision;
- served population is monotonic as the threshold increases;
- served area is monotonic as the threshold increases;
- coverage percentages remain between 0 and 100%;
- the native population-pixel and transit-point counts match the dated source snapshot used for the paper.

## Related literature

The analysis is positioned as a proximity-screening baseline rather than a full accessibility model. Relevant Addis Ababa and African accessibility studies include:

- Aklilu, A., & Necha, T. (2018). *Analysis of the spatial accessibility of Addis Ababa's light rail transit: The case of East–West corridor.* Urban Rail Transit, 4(1), 35–48. https://doi.org/10.1007/s40864-018-0076-6
- Atumo, E. A. (2025). *Spatial Approach for the Assessment of Public Transit Node Accessibility in Urban Areas of Developing Countries: Evidence from Addis Ababa, Ethiopia.* Abstracts of the International Cartographic Association, 10, 12. https://doi.org/10.5194/ica-abs-10-12-2025
- Asuah, A., & Acheampong, R. A. (2025). *Transport accessibility research in African cities: Systematic evidence review, knowledge gaps and directions for future research.* Urban Transitions, 3, 100013. https://doi.org/10.1016/j.ubtr.2025.100013
- Geurs, K. T., & van Wee, B. (2004). *Accessibility evaluation of land-use and transport strategies: Review and research directions.* Journal of Transport Geography, 12(2), 127–140. https://doi.org/10.1016/j.jtrangeo.2003.10.005
- Geurs, K. T., & van Wee, B. (2026). *A five-component conceptual model of calculated and perceived accessibility: Literature review and research directions.* Journal of Transport Geography, 134, 104678. https://doi.org/10.1016/j.jtrangeo.2026.104678
- Samuel, M., & Emagnu, Y. M. (2026). *Spatial optimization of bus stop locations using GIS and an integrated accessibility index in Addis Ababa, Ethiopia.* Discover Cities, 3, 101. https://doi.org/10.1007/s44327-026-00287-z

## Citation

See `CITATION.cff`.

## OSM attribution

Map data from OpenStreetMap, available under the Open Database License (ODbL): https://www.openstreetmap.org/copyright

## Author

**Eyob Azeze Negussie**  
Independent Researcher, Addis Ababa, Ethiopia
