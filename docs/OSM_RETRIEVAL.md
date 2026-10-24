# OSM snapshot retrieval

The snapshot `data/raw/osm/osm_transit_snapshot_2026-07-24.json` is raw Overpass API output
(generator: Overpass API 0.7.62.11; `timestamp_osm_base` 2026-07-24T10:57:40Z).

## How it was obtained

The author's original early script requested the data through OSMnx, which sends the query to the Overpass API:

```python
CITY = "Addis Ababa, Ethiopia"
tags = {
    "highway": "bus_stop",
    "public_transport": ["stop_position", "platform"],
    "railway": ["station", "stop", "halt", "tram_stop"],
}
stops_gdf = ox.features_from_place(CITY, tags=tags)
# point geometries were kept; polygons/ways were discarded
```

The area was the place polygon OSMnx resolves for "Addis Ababa, Ethiopia" (a Nominatim lookup), not the SSGI study boundary.
The exact Overpass text that OSMnx generated was not saved, and the retrieval step is not part of the current analysis
script: the saved JSON is the analysis input. Re-running the call today will not reproduce the snapshot, because OSM changes continuously.

## Consistency check on the saved file

- 2,577 nodes and 75 ways. 2,417 nodes carry tags; the other 160 are untagged vertices of the 75 platform ways.
- All 2,417 tagged nodes and all 75 ways satisfy the tag set above (`highway=bus_stop`, `public_transport=stop_position|platform`,
  `railway=station|stop|halt|tram_stop`). Adding `public_transport=station` (listed in the paper) selects no additional objects,
  because every such object also carries `railway=station` or `highway=bus_stop`. No `railway=tram_stop` object occurs in the data.
- Node extent: about 8.84-9.09 N, 38.67-38.89 E.
- The analysis keeps point nodes only and filters them to the study boundary (2,414 of 2,417 inside).

This establishes that the tag set matches; it does not prove the byte-for-byte origin of the file.
