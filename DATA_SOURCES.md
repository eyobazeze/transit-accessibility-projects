# Data Sources and Provenance

## 1. WorldPop population

**Dataset:** Ethiopia 2020 Population Counts  
**Provider:** WorldPop, University of Southampton  
**DOI:** https://doi.org/10.5258/SOTON/WP00682  
**Resolution:** approximately 100 m  
**Interpretation:** estimated number of people per grid cell.

The analysis uses the supplied population counts as pixel-level population estimates. It does not describe them as census observations or “real population data.”

## 2. Administrative boundary

**Dataset:** Ethiopia – Subnational Administrative Boundaries (COD-AB)  
**Provider:** United Nations Office for the Coordination of Humanitarian Affairs / Humanitarian Data Exchange  
**Source:** https://data.humdata.org/dataset/cod-ab-eth

The woreda-level polygons supplied with the project are dissolved to form the Addis Ababa study boundary.

## 3. OpenStreetMap

**Source:** OpenStreetMap data retrieved through an Overpass API snapshot.  
**Snapshot timestamp:** `2026-07-24T10:57:40Z`  
**Local snapshot file:** `data/raw/osm/osm_transit_snapshot_2026-07-24.json`

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
