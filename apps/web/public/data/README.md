# Warsaw district boundaries

`warsaw-districts.geojson` contains the 18 administrative districts of Warsaw.
It was generated on 2026-08-13 from OpenStreetMap data returned by the public
Overpass API, converted to GeoJSON, reduced to district names and polygon
geometry, and simplified to 15% with topology preservation.

Source data is © OpenStreetMap contributors and is available under the Open
Database License: <https://www.openstreetmap.org/copyright>.

The source query was:

```overpass
[out:json][timeout:60];
area["name"="Warszawa"]["boundary"="administrative"]["admin_level"="6"]->.warsaw;
relation(area.warsaw)["boundary"="administrative"]["admin_level"="9"];
out body geom;
```

The checked-in file keeps map rendering independent from Overpass availability
at runtime. Regeneration must preserve all 18 named polygon features and the OSM
attribution displayed by the map.
