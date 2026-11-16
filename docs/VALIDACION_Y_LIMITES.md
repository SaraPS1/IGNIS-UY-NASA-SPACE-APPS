# Validation, sensitivity, and limitations — IGNIS UY

## Available evidence

The repository includes `biblioteca_ignis/validacion_seis_casos.csv` and `biblioteca_ignis/sensibilidad_seis_casos.csv`, which support review of six Uruguayan cases (Cerro del Toro, Durazno, Artigas, Canelones, Lavalleja, and Treinta y Tres) with different distance radii and temporal windows.

*Candidate pair* fields document associations between records, **not** independent proof of confirmed wildfires or instrument accuracy. Each file should be identified by version and method: do not assume it automatically matches the current matching implementation if it was produced with another algorithm or range.

## What the sensitivity laboratory validates

- Cell-day counts depend on the chosen spatial resolution.
- Coincidence requires both instrument families, the same UTC date, and the same cell under the rounding rule.
- Duplicating observations does not duplicate the coincident cell-day count.
- Records from different dates do not become coincidences.
- Coverage is not invented for periods without data.

## What it **does not** validate

- Accuracy of on-the-ground wildfire detection.
- Probability that two detections refer to the same fire.
- Equal sensitivity, coverage, and resolution between MODIS and VIIRS.
- A temporal trend in Uruguay's fires derived from raw counts.
- 95% intervals or predictive performance.
- Replacement of official detection and alert methods.

## Known risks

1. **Sampling bias:** The demonstration's historical archive is partial and concentrated in summer months; days without imported observations are ambiguous.
2. **Instrument changes:** New satellites and orbital changes create artificial shifts in counts.
3. **Grid:** Cell size and grid anchoring affect matches; `0.2°` is an exploratory convention.
4. **Matching:** A candidate pair meets thresholds but does not prove event identity.
5. **Geography:** Maps use approximate outlines and geographic bounding boxes.
6. **External data:** News and institutional records require verification; the fusion demonstration includes synthetic sources.
7. **AI:** Ask IGNIS is a rule-based statistical engine, not a forecasting LLM.

## Future validation experiments (not implemented yet)

- Complete daily coverage inventories by instrument, region, and scientific product.
- Cross-sensor calibration under comparable observation opportunities.
- Retrospective validation using held-out sensors, years, and regions.
- Reproducible error metrics, uncertainty, and confidence intervals.
- Systematic comparisons against real external evidence, auditing false positives and omissions.

**Project principle:** Thermal anomaly ≠ confirmed wildfire. IGNIS UY does not issue official alerts, validated forecasts, or operational instructions.
