# IGNIS V5.2 — data-quality audit, unique matching, and NASA context

## Scope of this release

This module improves research quality and exploratory tools. It **does not** correct for sensitivity, cloud coverage, or observation opportunities, nor does it estimate the number of unique wildfires.

### 1. Row-level FIRMS import (`ignis_firms_sensor.py`)

Previously, each imported CSV was classified as a whole: if it mixed VIIRS S-NPP, NOAA-20, and NOAA-21, a single name could replace their individual identities.

The `instrumento` field is now determined **row by row**, first from `instrument` and `satellite` metadata and, when unavailable, from an unambiguous filename identifier. An unidentified platform remains explicitly marked as `VIIRS (plataforma no identificada)` (literally, “VIIRS, platform unidentified”); an unknown instrument is not arbitrarily converted to MODIS or VIIRS and triggers a warning.

Source-file provenance, stable identifiers, and the Master ZIP are preserved.

### 2. V5 matching (`ignis_pareo_v5.py`)

This complements — and does not silently replace — the earlier `ignis_coincidencias.emparejar` method.

1. Converts `fecha + acq_time` into a **complete UTC instant**, rejecting invalid HHMM values.
2. Filters out-of-range coordinates, invalid dates, and unrecognized instruments.
3. Searches for spherical-coordinate candidates with `cKDTree`, using `radio_km` and the `ventana_min` time difference.
4. Includes records on adjacent dates, including **both sides of UTC midnight**, and across the year boundary where applicable.
5. Orders candidates by time difference, then by distance.
6. Selects pairs without reusing any observation from either family in the complete result, including across different VIIRS platforms.
7. Retains both acquisition times, distances, coordinates, and **uncalibrated** FRP in the downloadable CSV.

Limitation: Selection is **greedy**, not a mathematically global minimum-cost assignment solution. A candidate meets compatibility thresholds; it does not establish that two observations describe the same fire.

V5 results may differ from historical results because of midnight crossing or global uniqueness; older tables must not be replaced without identifying the algorithm version.

### 3. Data-quality audit (`ignis_calidad.py`)

Counts total records, valid coordinates, valid dates, valid UTC times, recognized instruments, available FRP, and possible duplicate identifiers. Produces a monthly inventory of imported records and days **with detections**, by platform.

The column labeled `Días con detecciones` (“Days with detections”) **is NOT the number of satellite overpass days or observation opportunities**. Months without records are labeled `SIN REGISTROS IMPORTADOS` (“NO IMPORTED RECORDS”) rather than asserting zero activity. The audit does not justify temporal extrapolation or count calibration.

### 4. NASA Worldview (`ignis_worldview.py`)

Atlas and NRT monitoring provide direct links to [NASA Worldview](https://worldview.earthdata.nasa.gov/) with an observation's date and geographic extent.

The `t` and `v` URL parameters are documented in the [official Worldview repository](https://github.com/nasa-gibs/worldview/blob/main/doc/url_parameters.md).

The user must select appropriate satellite layers inside Worldview. The date and area do not guarantee useful imagery or cloud-free conditions; the visualization does not confirm a wildfire.

### 5. Reproducibility

From the repository root:

```bash
python -m pip install "numpy>=1.24" "pandas>=2" "scipy>=1.11"
python -m unittest discover -s tests -p 'test_ignis_sensibilidad.py' -v
python -m unittest discover -s tests -p 'test_ignis_pareo_calidad_v5.py' -v
```

The tests run in CI with Python 3.11 and 3.12. Synthetic cases cover midnight, the year boundary, mixed satellites, invalid HHMM values, missing coverage, duplicate IDs, and Worldview links.

## Outstanding work

- Automated historical ingestion with scientific product versions and hashes, plus a verifiable record of actual coverage.
- Quantitative MODIS–VIIRS calibration with equivalent observation opportunities, day/night distinctions, overlap periods, and instrument-change controls.
- Out-of-sample retrospective validation, uncertainty bounds, and abstention criteria.
- Embedded NASA GIBS thermal layers: the application currently provides only the **Worldview verification link**.
- Comparison with Fire Service/SINAE confirmed events using real evidence rather than test CSV files.

NASA notes that NRT observations may be replaced by science-quality data in the historical archive: [NASA FIRMS Archive](https://firms2.modaps.eosdis.nasa.gov/download/). NRT and definitive products must not be silently combined for calibration.

**Scientific principle:** Imported data ≠ complete coverage; anomalies ≠ confirmed wildfires; coincidences ≠ instrument calibration.
