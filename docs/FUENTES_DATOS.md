# Data sources and provenance — IGNIS UY

> **Implementation status documented in this repository.** A source identified as planned must not be presented as integrated.

| Source / service | Status | Current or proposed use | URL |
|---|---|---|---|
| NASA FIRMS: MODIS Collection 6.1 | Implemented | Manual historical CSV/ZIP import, instrument metadata | https://www.earthdata.nasa.gov/data/tools/firms |
| NASA FIRMS: VIIRS S-NPP Collection 2 | Implemented | Historical records imported by the team | https://www.earthdata.nasa.gov/data/tools/firms |
| NASA FIRMS: VIIRS NOAA-20 | Implemented | Historical imported data and NRT queries | https://www.earthdata.nasa.gov/data/tools/firms |
| NASA FIRMS: VIIRS NOAA-21 | NRT implemented; historical import under review | Recent monitoring via API; historical expansion and validation needed | https://firms.modaps.eosdis.nasa.gov/api/ |
| NASA FIRMS Area API | Implemented, opt-in | User-initiated recent queries with `FIRMS_MAP_KEY` | https://firms.modaps.eosdis.nasa.gov/api/ |
| National and press sources (Fire Service/PAIF, SINAE/MIRA) | Pilot module; institutional validation pending | Exploratory association with uploaded data, catalogue, and documentary evidence | https://www.gub.uy/sistema-nacional-emergencias/ |
| NASA GIBS | Proposed | Date-based imagery and layers for independent context | https://gibs.earthdata.nasa.gov/ |
| NASA Worldview | Proposed in this source inventory | Link for inspecting a location and date | https://worldview.earthdata.nasa.gov/ |
| NASA EONET | Proposed | Natural events as contextual information, **not** absolute wildfire ground truth | https://eonet.gsfc.nasa.gov/ |
| NASA POWER | Proposed (auxiliary variable) | Meteorological context; not a fire detector | https://power.larc.nasa.gov/ |
| Blue Marble / Black Marble | Visual reference, not thermal evidence | Backgrounds and inspiration for visualizations; distinguish art from data | https://visibleearth.nasa.gov/ |

## What each status means

- **Implemented:** Code is present in the application. This does not imply continuous provider availability.
- **Pilot:** Data can be associated, but the accuracy of those associations has not been validated by authorities.
- **Proposed:** A resource not yet integrated into processing or visualization; it must not be cited as implemented.

**Cross-document note:** This original inventory classifies NASA Worldview as proposed, while [the V5 implementation documentation](V5_CALIDAD_Y_PAREO.md) describes live Worldview **links** in Atlas and NRT monitoring. These statements should be reconciled with the deployed version; embedded GIBS imagery is not claimed.

## Provenance

`ignis_historico.py` records the source file, date, latitude, longitude, instrument, time, FRP when available, and a stable identifier per record. The summary of each imported file includes a SHA-256 content hash. Deduplicating observations **does not** identify unique wildfires.

The IGNIS Master dataset is stored manually by downloading and reimporting between sessions. There is no automatically synchronized global historical store or proven coverage for every month.

The NRT API does not guarantee equivalence with the definitive historical science archive. Where later science collections are available, they should be preferred for historical analysis and their versions documented.

**Caution:** Missing observations in uploaded files ≠ a satellite observed the area without fire. Changes in satellites, orbits, sensitivity, clouds, products, and quality must be documented before comparing trends.

## Licensing and attribution

Thermal anomaly observations are sourced from NASA FIRMS / EOSDIS. IGNIS UY is independent and does not represent an official NASA product or validation.

Reference: [NASA FIRMS attribution and products](https://www.earthdata.nasa.gov/data/tools/firms).
