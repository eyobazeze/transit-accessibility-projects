# Data Sources and Provenance

## 1. WorldPop population

**Dataset:** WorldPop Global 2015–2030 constrained population counts, R2025A v1, year 2026  
**File:** `eth_pop_2026_CN_100m_R2025A_v1.tif` (repository holds a clip: `addis_population_clipped.tif`)  
**Provider:** WorldPop, University of Southampton  
**Citation:** Bondarenko et al. (2025), https://doi.org/10.5258/SOTON/WP00839  
**Note:** constrained product; unsettled pixels are NoData. WorldPop labels this release an early version that may change.  
**Licence:** CC BY 4.0 (attribution required)  
**Resolution:** approximately 100 m  
**Interpretation:** estimated number of people per grid cell.

The analysis uses the supplied population counts as pixel-level population estimates. It does not describe them as census observations or “real population data.”

## 2. Administrative boundary

**Dataset:** Ethiopia – Addis Ababa subcities and woredas (resource `aa_worda_boundary.zip`)  
**Source:** Space Science and Geospatial Institute (SSGI)  
**HDX contributor:** 3iS  
**URL:** https://data.humdata.org/dataset/ethiopia-addis-ababa-subcities-and-woredas (HDX dataset ID `8d82f1ca-5a1d-4e73-9fea-8e53c190869d`)  
**Downloaded:** 6 July 2026  
**HDX dates:** time period 24 October 2024; added 26 March 2025; modified 19 December 2025  
**Licence:** CC0 1.0 (Public Domain)

The file contains 116 woredas in 10 sub-cities (EPSG:4326). The zip's `wfsrequest.txt` records an export from the EthioNSDI GeoServer (layer `geonode:aa_worda_boundary`). The woreda-level polygons are dissolved to form the Addis Ababa study boundary.

This is not the OCHA COD-AB boundary set. The HDX record cautions that the dataset does not fit the woreda boundaries in shapefiles shared by OCHA.

## 3. OpenStreetMap

**Source:** OpenStreetMap data retrieved through an Overpass API snapshot.  
**Licence:** ODbL 1.0 (attribution and share-alike apply to the database and derived databases)  
**Snapshot timestamp:** `2026-07-24T10:57:40Z`  
**Local snapshot file:** `data/raw/osm/osm_transit_snapshot_2026-07-24.json`  
**Query:** requested through OSMnx (`ox.features_from_place("Addis Ababa, Ethiopia", tags)`); the generated Overpass text was not saved. The snapshot's contents (2,577 nodes, 75 ways; 2,417 tagged transit nodes) are consistent with the tag list below; see `docs/OSM_RETRIEVAL.md`.

The snapshot contains the Overpass attribution notice that the data are from OpenStreetMap and are made available under ODbL.

The analysis selects point nodes with the following transit-related tags:

- `highway=bus_stop`
- `public_transport=platform`
- `public_transport=stop_position`
- `public_transport=station`
- `railway=station`
- `railway=stop`
- `railway=halt`
- `railway=tram_stop`

Only matching **nodes** are used as transit access points. OSM platforms represented as ways or areas are not converted into points by this workflow.

## Attribution

OpenStreetMap attribution is required when publicly distributing the produced work. Use:

> Map data from OpenStreetMap, available under the Open Database License (ODbL): https://www.openstreetmap.org/copyright

See the OpenStreetMap Foundation attribution guidance: https://osmfoundation.org/wiki/Licence/Attribution_Guidelines
