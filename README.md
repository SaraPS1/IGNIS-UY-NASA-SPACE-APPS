# IGNIS UY — From Space to Ground Evidence

**Independent scientific research prototype** that organizes NASA FIRMS thermal anomaly observations in Uruguay, explores matches between MODIS and VIIRS, and compares satellite records with documentary and ground evidence.

> **Important:** A FIRMS detection does not represent a unique wildfire or confirm burned area. **Quantitative** cross-sensor harmonization and operational validation remain pending.

## Implemented features

- Import NASA FIRMS MODIS/VIIRS CSV/ZIP files, deduplicate observations, and manually export/reimport the IGNIS Master dataset.
- Query recent NASA FIRMS observations on demand with a MAP_KEY.
- Generate maps, time series, instrument-specific calendars, and scientific PDF reports.
- Exploratory matching by **UTC day and 0.20° grid cell**; alternative matching within **5 km and 30 minutes** (configurable).
- **Grid sensitivity laboratory:** compare 0.05°, 0.10°, 0.20°, and 0.40° using the same subset and export results to CSV.
- Recent monitoring including NOAA-21; historical import of **mixed** files with per-record instrument identification.
- **Alternative V5 scientific matching:** unique matches across UTC midnight and export of paired dates, distances, and original FRP.
- **FIRMS quality audit:** coordinates, dates, times, FRP, possible duplicates, and a monthly inventory warning about unverified coverage.
- **NASA Worldview:** links for specific dates and locations from the Atlas and NRT monitoring.
- Documentary traceability, experimental NASA–Fire Service/PAIF–SINAE/MIRA associations, contributions, and the **rule-based** Ask IGNIS assistant (not an LLM).

Files available during a session do not guarantee complete temporal or instrument coverage. Outputs **are not official alerts**.

## Getting started

Python 3.11 is recommended.

```bash
python -m pip install -r requirements.txt
streamlit run principal.py
```

Configure `FIRMS_MAP_KEY` in Streamlit secrets for recent queries (see `.streamlit/secrets.toml.example`). **Never commit API keys to the repository.** Historical ZIP/CSV files are uploaded through the interface. Download the IGNIS Master dataset as a backup for the next session.

### Scientific tests

```bash
python -m unittest discover -s tests -p "test_ignis_sensibilidad.py" -v
python -m unittest discover -s tests -p "test_ignis_pareo_calidad_v5.py" -v
```

Synthetic sensitivity tests do not replace validation against confirmed wildfires.

## Documentation and attribution

| Document | Contents |
|---|---|
| [Data sources](docs/FUENTES_DATOS.md) | NASA FIRMS and other services: implemented, pilot, or proposed |
| [Scientific methodology](docs/METODO_CIENTIFICO.md) | Formulas, criteria, discretization, matching, and calibration requirements |
| [Validation and limitations](docs/VALIDACION_Y_LIMITES.md) | Cases, testing scope, biases, and outstanding uncertainty |
| [V5 quality and matching](docs/V5_CALIDAD_Y_PAREO.md) | Per-record import, midnight matching, data inventory, and Worldview |
| [AI use](docs/USO_DE_IA.md) | Actual Ask IGNIS capabilities and a tool-use log for the team to complete |
| [Roadmap](docs/HOJA_DE_RUTA.md) | Steps toward verified coverage, quantitative harmonization, and NASA GIBS visualization |
| [Contributions](TEAM_IGNIS_CONTRIBUCIONES.md) | Public discussions through GitHub Issues |

**Data:** NASA [Fire Information for Resource Management System (FIRMS)](https://www.earthdata.nasa.gov/data/tools/firms), part of EOSDIS. MODIS and VIIRS observations are attributed to their respective sources. IGNIS UY is independent and is not an official NASA application or an indication of NASA endorsement.

**Challenge status:** This version **does not** demonstrate a complete correction of discontinuities in the historical series caused by sensor changes. Detection counts are not normalized by observation coverage, and matching tests remain exploratory.

The README and exported data document what the prototype actually does. Any future calibrated model must publish its methodology, out-of-sample tests, and uncertainty intervals before being presented as a scientific result.
