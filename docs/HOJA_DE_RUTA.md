# Phased roadmap — IGNIS UY V5

This document separates **actually implemented deliverables** from pending objectives. Learning from other projects is legitimate, but copying their interfaces or claiming unreproduced results is not.

## Phase 1: scientific foundations and traceability — included in this PR

- Verifiable inventory of used and proposed sources.
- Explicit methods and limitations; AI usage without invented attributions.
- Grid sensitivity laboratory from 0.05° to 0.40°, exportable as CSV.
- Unit tests and scientific CI.
- Historical VIIRS NOAA-21 import identified from satellite metadata and filename.

## Phase 2: historical coverage and acquisition — pending

- Verified historical ingestion by collection and satellite, with temporal and spatial coverage metadata.
- Controlled updates using checksums, stable IDs, and versioning of each product.
- DuckDB/Parquet to accelerate queries without replacing source data.
- Separate NRT from scientific collections and record versions.

## Phase 3: quantitative harmonization — pending

- Define a reference scale and actual overlap periods.
- Estimate adjustments **only** with verified instrument exposure and comparable records.
- Separate day/night and months/areas; control for instrument changes.
- Retrospective validation using years/sensors excluded from training.
- Error metrics, uncertainty intervals, and abstention rules.

## Phase 4: interface and external resources — pending

- Date-based NASA GIBS layers and contextual links to Worldview.
- EONET context and/or independent documentary sources; an event is not absolute ground truth for every pixel.
- A public API with reproducible responses if the pipeline becomes stable.
- Optional generative analyst, **never** a substitute for verified calculations.

### Scientific acceptance criterion

Do not display labels such as “calibrated,” “validated,” “wildfire probability,” or “operational alert” unless the methodology, supporting data, independent validation, and uncertainty documentation are available.
