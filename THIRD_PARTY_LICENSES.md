# Third-party materials, licenses, and attribution — IGNIS UY

This inventory is supplied to make provenance visible to reviewers. **Listing a resource here does not prove that all rights have been cleared.** Verify the licenses associated with the **actual installed versions, bundled copies and exported media** before the final release.

## Licensing scope

The repository proposes **Apache License 2.0 for original code authored by the IGNIS UY contributors**, subject to approval from all rights holders. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

**Not automatically licensed under Apache 2.0:** NASA or third-party observations; satellite imagery and external basemaps; official NASA, Air Force School, Fire Service or SINAE branding; third-party software and fonts; and SI-generated or externally sourced images, audio, or video when the team lacks transferable distribution rights. Such materials remain governed by their original rights and conditions. Do not interpret this document as a grant of permissions for assets the team does not own.

## Python runtime packages

These are the direct dependencies from `requirements.txt`. Their license identifiers are *informational starting points*, not a completed review of installed wheels, transitive dependencies, bundled data, or version-specific notices.

| Dependency | Upstream project / license lookup | License family to verify for actual version | Project use |
| --- | --- | --- | --- |
| Streamlit | https://github.com/streamlit/streamlit | Apache-2.0 | Web UI |
| pandas | https://github.com/pandas-dev/pandas | BSD-3-Clause | Tables and time-series analysis |
| NumPy | https://github.com/numpy/numpy | BSD-3-Clause | Numerical operations |
| Plotly | https://github.com/plotly/plotly.py | MIT | Interactive charts |
| Folium | https://github.com/python-visualization/folium | MIT | Leaflet-based maps |
| ReportLab | https://pypi.org/project/reportlab/ | BSD-style; confirm package's included license | PDF reports |
| Matplotlib | https://matplotlib.org/stable/project/license.html | Matplotlib License (PSF-based) | Static scientific charts |
| SciPy | https://github.com/scipy/scipy | BSD-3-Clause | Matching and spatial analysis |
| Requests | https://github.com/psf/requests | Apache-2.0 | Web/API requests |
| sgp4 | https://pypi.org/project/sgp4/ | MIT; verify installed version | Orbital propagation |
| Skyfield | https://github.com/skyfielders/python-skyfield | MIT; verify installed version | Orbital calculations |

Additional packages, transitive dependencies and deployed environment versions are not captured by this direct-dependency list. Preserve applicable notices if redistributing software packages.

## Front-end / visualization and mapping resources

| Resource | Upstream | Review status |
| --- | --- | --- |
| Three.js | https://threejs.org/ | Check MIT license and bundled/imported JavaScript version |
| Leaflet | https://leafletjs.com/ | Check upstream license and attribution in maps |
| OpenStreetMap data / tile servers (if displayed) | https://www.openstreetmap.org/copyright | Verify visible map attribution and provider usage/redistribution conditions |
| External orbital elements and textures (if downloaded) | Identify the **specific** origin URL and license | **Not yet cleared** |
| Blue Marble / Black Marble-inspired visuals | https://visibleearth.nasa.gov/ | Distinguish original NASA source imagery from SI-generated art; check rights and logos |

## Data and documentary evidence

| Data/resource | Source | Use / caution |
| --- | --- | --- |
| NASA FIRMS MODIS / VIIRS | https://www.earthdata.nasa.gov/data/tools/firms | Imported thermal-anomaly observations; document product/version and cite NASA FIRMS |
| NASA Worldview | https://worldview.earthdata.nasa.gov/ | Outbound inspection links, not proof of an embedded imagery license |
| SINAE / MIRA documentary evidence | https://www.gub.uy/sistema-nacional-emergencias/ | Institutional references require source-specific permission and provenance |
| Fire Service / PAIF reports | Cite the individual governmental source | Do not imply agency endorsement or official system integration |
| Simulated Fire Service / SINAE CSVs | Team-created test fixtures | Clearly labeled **synthetic, not official evidence** |

See [Data sources and provenance](docs/FUENTES_DATOS.md) for implemented versus proposed integrations.

## Artwork, logos, reports, and media

| Asset category | Required check before distributing |
| --- | --- |
| IGNIS UY team emblem / logo | Confirm the generating tool, authorship and usage rights; visibly label SI-generated versions |
| Website hero and feature-card artwork | Verify original files, generation method and permitted redistribution; visible SI watermark where needed |
| 3D textures, background images and report illustrations | Record each file's source and permission; remove unclear assets |
| NASA, institutional and mission emblems | **Do not assume permission** to reproduce official logos, particularly within SI-generated visual media |
| Canva presentation | Review every embedded image, template, illustration and font for redistribution rights and required SI marking |
| Generated scientific PDFs | Attribute NASA FIRMS data and SI-assisted Python generation; evaluate each graphic's origin; re-export after compliance changes |
| HeyGen English narration / other synthetic audio | Check the plan-specific HeyGen terms; disclose SI generation in descriptive text and metadata |
| Google Drive video walkthrough | Check media and audio provenance, video sharing rights, and any external tracks |

**Open items:** A complete file-by-file asset audit, contributor approval, and verified permissions for institutional emblems and third-party illustrations have **not** been completed by this PR. Avoid stating that all media are cleared until those reviews are finished.

## What to submit to Space Apps

The official [NASA Space Apps 2026 Terms and Conditions](https://www.spaceappschallenge.org/legal/) require appropriate license documentation and citations of **every used resource**, including free/open-source materials. Use the submission form's **NASA Data** and **Space Agency Partner & Other Data** fields for actual resources used in the project; do not list merely proposed integrations as implemented.

Before submission, the team should archive original asset URLs, terms, copyright holder approvals, and any permission records where applicable. This document is an inventory, **not legal certification**.
