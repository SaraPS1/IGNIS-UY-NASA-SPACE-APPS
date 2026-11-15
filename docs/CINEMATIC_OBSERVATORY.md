# IGNIS UY — Cinematic Geospatial Observatory

This feature adds a real interactive WebGL Uruguay scene to the existing Streamlit dashboard, while keeping the Python analysis modules and file formats unchanged.

## Where it appears

New visits open **Dashboard / Mission Control** by default. The original **Home · Discover IGNIS** landing page remains accessible in the sidebar, alongside all existing sections.

The **Uruguay · Geospatial Observatory** includes:

- An extruded national outline built from `uruguay_contorno.geojson`, illustrative relief, a large Earth horizon, clouds, orbit trails and a controllable 3D camera.
- Distinct MODIS and VIIRS observations, labelled with the actual imported timestamp, instrument, satellite, location, FRP and confidence where provided.
- An animated chronological selector (2000–2026), source toggles and a compact mission deck showing full record counts by year.
- **Guided flyover:** visits up to five spatially separated *displayed observations* ordered by their available FRP, with a Stop action. It does not construct or predict incidents.
- A radial camera menu, cinematic mode, reduced-motion preference, adaptive graphical quality and a labelled 2D fallback.
- The existing Ask IGNIS assistant and scientific analytics integrated around the 3D scene.

## Implementation

- `ignis_scene3d.py` — a data adapter for the existing uploaded NASA FIRMS records. Totals always use complete filtered data; only the rendered markers are capped for performance.
- `assets/ignis_scene3d.html` — self-contained Three.js WebGL visualization with client-side interactions, cinematic controls and graceful 2D fallback.
- `ignis_dashboard.py` — responsive Streamlit layout, mission-control design system, historical analytics and Ask IGNIS integration.
- `ignis_visual.py` and `ignis_historico.py` — narrow integration points that preserve all existing analysis pages.
- `ignis_fusion_terrestre.py` — exposes calculated (not invented) associations to the scene.

Three.js is loaded from a CDN. A browser must support WebGL and be allowed to access the CDN for the full 3D renderer; otherwise the map falls back to the 2D canvas.

## Verification

Run `python -m unittest discover -s tests -p 'test_ignis_cinematic_observatory.py' -v` and `python -m unittest discover -s tests -p 'test_ignis_scene3d_dashboard.py' -v`. The `IGNIS cinematic observatory validation` GitHub Actions workflow compiles Python modules, checks JavaScript syntax with Node, tests the data adapter and captures a browser preview when Chrome is available.

The workflow preview uses **synthetic test observations**, visibly marked as such. It must never be interpreted as real FIRMS or real wildfire activity.

## Scientific boundaries

IGNIS is a research system, not an emergency alerting product. A FIRMS thermal anomaly is not automatically a wildfire; missing imported detections do not prove absence of fire. The globe, relief, satellite orbits and beams in this dashboard are illustrative. Do not use them to infer physical orbit positions, fire spread, risk probability, validated coverage or operational status. Official record sources remain traceable through the existing modules.

The production dashboard never injects demonstration observations or fabricated metrics. Without uploaded data it displays the Uruguay outline and clearly states that observations must be imported. Verified department boundaries appear only when an appropriate documented polygon dataset is available.
