# Reproducibility Notes

The reported paper results are generated from the files committed in `data/raw/` and the analysis script in `src/`.

## Source snapshot identity

- WorldPop: Ethiopia 2020 Population Counts, DOI 10.5258/SOTON/WP00682.
- OSM: Overpass snapshot timestamp `2026-07-24T10:57:40Z`.
- Study boundary: SSGI Addis Ababa woreda boundaries (HDX dataset "Ethiopia – Addis Ababa subcities and woredas", CC0 1.0, downloaded 6 July 2026) dissolved to the study boundary.
- Projected CRS: EPSG:32637.
- Native population pixels inside boundary: 56,666.
- OSM matching nodes: 2,417 total; 2,414 inside boundary.
- Research cells: 2,155 valid 500 m cells.
- Total estimated population represented within the study boundary: 4,627,715.063.

## Core validation values

| Threshold | Area coverage | Population coverage | Population beyond threshold |
|---:|---:|---:|---:|
| 300 m | 27.9174% | 46.7204% | 2,465,628.035 |
| 500 m | 48.3910% | 75.4392% | 1,136,603.178 |
| 800 m | 67.3587% | 91.8489% | 377,210.199 |
| 1,000 m | 75.0937% | 95.4214% | 211,886.576 |

## Important implementation details

The 500 m grid is aligned to the projected bounds of the source WorldPop raster, while each grid cell is clipped to the dissolved Addis Ababa study boundary. Native population-pixel centroids are used for the Euclidean nearest-transit calculation; population is not first resampled to the 500 m grid for the accessibility classification.

The estimated population associated with each native raster cell is represented at that cell's centroid for the proximity calculation. The resulting threshold coverage is therefore population-weighted by the native pixel population values, but the study does not calculate a population-weighted mean distance.

The workflow evaluates Euclidean proximity rather than walking-network distance. The 500 m threshold is an analytical scenario and is not the UN SDG 11.2.1 indicator.
