# Scientific methodology — IGNIS UY

## Unit of analysis

Each row represents a **satellite thermal observation**, not a confirmed wildfire or burned area. The Master dataset retains the UTC date, latitude, longitude, instrument, satellite, acquisition time, FRP when available, confidence, provenance, and ID.

## 1. Grid-cell/day coincidence

The current analysis assigns each observation to a grid:

```text
cell_lat = round(latitude / resolution_in_degrees)
cell_lon = round(longitude / resolution_in_degrees)
```

For each `(UTC day, cell_lat, cell_lon)` combination, the system checks whether there is at least one MODIS and one VIIRS observation. It counts **one** coincident cell-day even if multiple detections exist within it.

```text
C(r) = sum_{day, cell} 1[MODIS > 0 and VIIRS > 0]
```

The **0.20° resolution is an exploratory parameter, not a sensor's native resolution**. Near 33° S, it represents approximately 22 km north–south and 19 km east–west, with variations according to latitude. Two nearby observations may fall into different cells; two distant observations may belong to the same cell.

The new `ignis_sensibilidad.py` laboratory runs exactly this rule for 0.05°, 0.10°, 0.20°, and 0.40° on the same imported subset. It identifies scale-dependent changes; **it does not establish an optimal grid size by itself**.

## 2. Spatial and temporal matching

`ignis_coincidencias.py` searches for candidate MODIS–VIIRS pairs on the same UTC day using spherical coordinates and a `cKDTree`. Distance is calculated using a mean Earth radius of 6,371.0088 km. The reference thresholds are **5 km** and **30 minutes**, configurable in the interface.

Candidates are ordered by smaller time difference and distance, with non-reuse within each MODIS-to-VIIRS-platform comparison. A MODIS point may appear in separate comparisons against different platforms. These pairs **are not unique wildfires**.

## 3. Temporal statistics

Records are counted by `(year, month, instrument)` and displayed **without normalization for observation opportunities**. The pilot unusual-activity signal requires at least three reference years for the same month and sensor, five records, and twice the median of other years.

The absence of imported records is not interpreted as a month with complete coverage and zero fires.

## 4. Concentration versus recurrence

- **Concentration:** Number of observations in a spatial cell.
- **Recurrence:** Number of distinct years containing observations in a cell.
- **Visual density:** A spatial histogram smoothed with a Gaussian filter, not burned area.

## 5. Satellite–ground fusion

`ignis_fusion_terrestre.py` creates candidate associations by distance and time, with default parameters of 10 km and 24 hours. When an external record contains only a date, the system matches by local calendar day rather than inventing an exact time. Synthetic CSV files are identified as such and are not independent validation.

## 6. Requirements for future quantitative harmonization

A harmonized series requires, at minimum:

1. Verified instrument availability and observation opportunities, distinguishing products and overpass times.
2. Representative MODIS–VIIRS overlap periods to estimate corrections.
3. Correction or stratification for coverage and detection differences, distinguishing day and night.
4. Validation on years or areas excluded from fitting, with error metrics and uncertainty intervals.
5. Explicit criteria for declining to estimate when sufficient information is unavailable.

Raw-count ratios **must not be labeled as calibration**. IGNIS currently publishes neither quantitatively harmonized series nor calibrated probabilities.

## Reproducibility

The sensitivity laboratory is deterministic, does not require external services, and does not modify the Master dataset. Its exported CSV includes the four spatial scales and the currently selected year/region/sensor subset.

Run the tests:

```bash
python -m unittest discover -s tests -p "test_ignis_sensibilidad.py" -v
```

See also [data sources](FUENTES_DATOS.md), [validation and limitations](VALIDACION_Y_LIMITES.md), and the scripts named above.
