# IGNIS — Offline Earth fallback data

`world_coastlines_naturalearth.geojson` is a generalized low-resolution
world country-boundary dataset sourced from:

https://github.com/johan/world.geo.json/blob/master/countries.geo.json

The underlying cartographic data come from **Natural Earth**, a public-domain
map dataset: https://www.naturalearthdata.com/about/terms-of-use/

This file is used **only for a stylized local land/ocean fallback on the 3D
Earth visualization** when optional remote satellite imagery is missing or
network-dependent textures fail. It is not a high-resolution Earth product,
not historical satellite imagery, not ground truth for political boundaries
or fire extents, and not used by SGP4 orbital calculations.

IGNIS's existing Uruguay outline in `uruguay_contorno.geojson` remains the
national spatial reference for local observation maps. Country borders are
cartographically generalized and must not be used for legal boundaries.
