# IGNIS UY — From Space to Ground Evidence

**NASA Space Apps Challenge 2026 · Independent geospatial research prototype · Uruguay**

IGNIS UY organizes NASA FIRMS MODIS and VIIRS thermal anomaly observations, explores spatial and temporal correspondences between instruments, and supports experimental comparison against documentary and ground evidence. The project combines historical maps, calendars, 3D visualizations, quality checks and scientific reporting.

> **Scientific limitation:** A satellite thermal anomaly is **not** a confirmed wildfire, a unique fire event, or measured burned area. The 2000–2026 imported archive is **partial and not normalized for satellite coverage**. IGNIS UY does **not** currently publish a validated quantitative MODIS–VIIRS harmonized series, operational fire alerts or confirmed ground matches.

## Project links — start here

| Resource | Link | Status and purpose |
| --- | --- | --- |
| **GitHub project and source** | [IGNIS UY repository](https://github.com/SaraPS1/IGNIS-UY-NASA-SPACE-APPS) | Public source, methods, tests and documentation |
| **Project demonstration** | [Seven-slide presentation on Canva](https://canva.link/ta32fjqimlmpur6) | Official short project overview |
| **Additional files and reports** | [IGNIS UY project Drive folder](https://drive.google.com/drive/folders/1GAA0pQ4IglPLJJnTzFsizzOmaVGKQjy2) | Supporting documents; anonymous access has **not been independently verified** |
| **Long-form website walkthrough** | Link to be added after the screen recording is published | Approximately ten-minute **supplemental guide** with SI-generated female narration (HeyGen); separate from the required short demo |
| **Live Streamlit app** | [Open IGNIS UY on Streamlit](https://ignis-uy-nasa-space-apps-jhw9zqnrnsardpgxulfzq9.streamlit.app/) | Interactive project application |

**Explore the project:** Open the [interactive Streamlit application](https://ignis-uy-nasa-space-apps-jhw9zqnrnsardpgxulfzq9.streamlit.app/), then consult the scientific methods, validation limits, source provenance and reproducible code in this repository. The short project demonstration and optional longer walkthrough are separate resources.

## The challenge and our approach

MODIS and VIIRS observe thermal activity with different detection sensitivity, spatial resolution, observation times and platform availability. Comparing raw counts without accounting for these differences can misrepresent historical patterns.

IGNIS UY contributes a **transparent, reproducible exploratory workflow**, not a finished sensor calibration. It imports and audits records, organizes them by UTC timestamp and instrument, tests candidate MODIS–VIIRS associations, displays an observation calendar and supports provisional satellite–ground evidence associations.

The application aims to make these uncertainties understandable rather than conceal them.

## Explore the website

| Section | Working capability | How to interpret it |
| --- | --- | --- |
| **Home · Discover IGNIS** | Project introduction and navigation | SI-generated artwork is illustrative, not measured imagery |
| **Data upload** | Import NASA FIRMS CSV/ZIP and IGNIS Master ZIP; overview and data checks | No guaranteed complete archive or persistent global database |
| **Dashboard** | Observation metrics and full-width interactive 3D Uruguay scene | Terrain effects and some orbital elements are illustrative |
| **Historical Archive 2000–2026** | Filter imported observations and view time-series/maps | Scope refers to available imports, not verified continuous coverage |
| **MODIS–VIIRS Harmonization** | Grid-cell/day and spatial–temporal candidate matching; sensitivity analysis | Candidates do not prove the same fire or calibrated equivalence |
| **Uruguay Map** | 3D view by default; optional 2D zoomable and density maps | Coordinates display observations, not confirmed events |
| **Alerts & Traceability** | Statistical screening and documentary research | Not operational wildfire warnings |
| **Final Calendar** | Organize imported observations by date/sensor | No record is not proof of no fire |
| **PDF Report** | Export scientific summaries | Reports identify SI-assisted report-generation code in visible text and PDF metadata; NASA FIRMS source measurements are not SI-generated |
| **Recent Monitoring** | Optional recent FIRMS API queries | Requires configured key; NRT differs from definitive archived products |
| **3D Earth & Satellites** | Interactive globe and satellite context | Scientific SGP4 positions require valid TLEs; otherwise explicitly illustrative |

The project also includes experimental satellite–ground fusion and **Ask IGNIS**, a deterministic Python/Pandas rule-based assistant for loaded data. **Ask IGNIS is not a generative LLM at runtime** and does not browse live news on its own.

## What the numbers actually mean

The team presentation describes an **imported sample of 17,946 records from 27 years**. These are sample-dependent counts from a particular IGNIS Master dataset, **not universal NASA totals or a continuously maintained historical census**. Other uploads and filters will produce different totals.

Two complementary exploratory methods are implemented:

1. **Cell/day co-occurrence:** Group MODIS and VIIRS observations by UTC date and a configurable geographic grid. The illustrative base grid is **0.20°**, not a native MODIS/VIIRS footprint. One matching cell/day is counted once even if multiple observations occur within it.
2. **Distance/time candidates:** Compare observation coordinates and acquisition times; reference parameters include **5 km** and **30 minutes**, adjustable in the interface. Candidate associations are not independent fire confirmations.

The team sample reported **14 candidate coincident grid cell-days** and **2 candidate distance/time pairs** for its selected example. Those are **different definitions and should not be added together** or called 16 fires.

The pilot space-to-ground demonstration uses **real imported FIRMS observations and two explicitly synthetic ground/institutional CSV test sources**. The demonstration shows that the matching software operates, **not** that institutional ground evidence has been independently verified.

See [scientific methodology](docs/METODO_CIENTIFICO.md), [validation and limitations](docs/VALIDACION_Y_LIMITES.md) and [V5 quality and matching](docs/V5_CALIDAD_Y_PAREO.md).

## Run IGNIS UY

**Prerequisites:** Python 3.11 recommended, internet access for CDN-based 3D dependencies and optional API functionality.

```bash
git clone https://github.com/SaraPS1/IGNIS-UY-NASA-SPACE-APPS.git
cd IGNIS-UY-NASA-SPACE-APPS
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run principal.py
```

The Streamlit application normally opens at **http://localhost:8501**. To explore real data, upload a NASA FIRMS CSV/ZIP or the team's exported Master ZIP under **Data upload**. The default empty state should **not** be misrepresented as a fully populated archive.

For optional recent NASA FIRMS API queries, configure `FIRMS_MAP_KEY` in Streamlit secrets as described in `.streamlit/secrets.toml.example`. Never commit a MAP_KEY or access token. The Master dataset is manually downloaded and reimported to preserve work across sessions.

### Tests

```bash
python -m unittest discover -s tests -p "test_ignis_sensibilidad.py" -v
python -m unittest discover -s tests -p "test_ignis_pareo_calidad_v5.py" -v
python -m unittest discover -s tests -p "test_3d_panel_no_overlap.py" -v
```

GitHub Actions additionally tests scientific methods, UI compatibility, source fidelity, 3D rendering paths and SI documentation. **Passing automated tests does not replace real-browser testing or field validation.**

## Supplementary narrated website walkthrough (approximately 10 minutes)

A ten-minute English-language guided tour has **SI-generated female voice narration**, created using **HeyGen AI Voice (Janet — Warm & Approachable, en-US)** from a team-reviewed script prepared with SI assistance. The narration audio is **generated**, not recorded by a human narrator; the website screen recording and final edited video are separate media. The completed public video link will be added here after publication; the audio link is not presented as a completed or uploaded video.

**Required attribution for the published walkthrough:** place the following notice in the video's public description **and in its metadata**: *“SI-generated voice narration: HeyGen AI Voice (Janet, US English). Script prepared with SI assistance and reviewed by the IGNIS UY team. Screen recording demonstrates the IGNIS UY application.”* Do not claim the voice is a human teammate. If any video imagery itself is SI-generated, mark that imagery visibly as SI-generated as required by the challenge; screen recordings of the existing site are not automatically wholly SI-generated video.

The tutorial follows all 14 navigation tabs, including Data Upload, Dashboard, Historical Archive, Harmonization, Uruguay Map, Alerts & Traceability, Final Calendar, PDF Report, Recent Monitoring, 3D Earth & Satellites, Ask IGNIS, Satellite–Ground Fusion and Team & Contributions. It is **supplementary** and does not replace the required competition short demo.

## Super Intelligence (SI) — transparent disclosure

**SI tools were used** to help design, write, debug and document Python/HTML/CSS/JavaScript, and to assist with visual illustrations and explanatory text. The team remains responsible for checking the work and scientific claims.

- **Generated artwork:** The website labels illustrative backgrounds **SI-generated illustration** and the team emblem **SI-generated logo**. Web overlays **do not embed watermarks into the raw image files**. Standalone images, exported graphics, slides and any generated videos must carry visible SI watermarks.
- **Code and data:** SI-assisted data-processing code is disclosed in project documents and metadata exported with Master ZIP files. **NASA FIRMS satellite observations are externally sourced, not AI-generated measurements.**
- **Scientific PDF exports:** Both the general report and selected-cell fusion report visibly acknowledge SI-assisted report-generation code and include provenance in PDF metadata. The reports retain NASA FIRMS attribution in text without embedding NASA insignia. Any accompanying illustrative graphic or team emblem is identified as SI-generated or SI-assisted where displayed.
- **Audio/video:** The **supplemental ten-minute website walkthrough uses SI-generated narration** produced with HeyGen AI Voice (Janet, en-US). Its final public video must acknowledge the synthetic voice in **description and metadata**. This does not imply that the app includes synthetic voice or that the screen recording is generated footage. Any separately SI-generated video footage requires its own visible watermark.
- **Branding:** Do not include, recreate or modify NASA insignia, flags, mission logos or identifier designs in SI-generated art. Factual NASA FIRMS source attribution is not a claim of endorsement. The team must separately review all existing media and permissions before submission.

Full details: [SI use and provenance](docs/SI_USAGE.md) · [Machine-readable SI disclosure](docs/si_usage.json) · [Ask IGNIS and tool-use notes](docs/USO_DE_IA.md).

## NASA data, third-party libraries and attribution

**Primary data source:** [NASA Fire Information for Resource Management System (FIRMS)](https://www.earthdata.nasa.gov/data/tools/firms), including externally supplied MODIS and VIIRS active-fire/thermal anomaly products. [FIRMS API](https://firms.modaps.eosdis.nasa.gov/api/) enables optional recent queries.

**Tools and software:** [Python](https://www.python.org/), [Streamlit](https://streamlit.io/), [Pandas](https://pandas.pydata.org/), [NumPy](https://numpy.org/), [Plotly](https://plotly.com/python/), [Three.js](https://threejs.org/), [Folium](https://python-visualization.github.io/folium/), [Matplotlib](https://matplotlib.org/), [SciPy](https://scipy.org/), [ReportLab](https://www.reportlab.com/), [SGP4](https://pypi.org/project/sgp4/) and [Skyfield](https://rhodesmill.org/skyfield/). Versions and package requirements are in [requirements.txt](requirements.txt).

**Other evidence sources:** Fire service/PAIF, SINAE/MIRA records and press references are **pilot/proposed external sources**, not a claim of an official data integration or agency endorsement. NASA POWER, EONET and GIBS are documented as proposed resources where not actually integrated; do not list proposed resources as successfully used in the final submission. Inspect [source inventory](docs/FUENTES_DATOS.md) for precise current statuses.

## License and third-party rights

**Original IGNIS UY software:** [Apache License 2.0](LICENSE) is proposed for original contributor-owned code. This is an OSI-approved open-source license; release under these terms requires confirmation from the copyright holders of the contributed work. See the [project NOTICE](NOTICE).

**Third-party content and attribution:** The Apache license **does not automatically grant rights** to NASA datasets, official agency logos, third-party code/assets, externally sourced imagery, satellite textures, or AI-generated media subject to third-party terms. Those resources remain subject to their respective owners' licenses and permissions. Consult the [third-party licensing and source inventory](THIRD_PARTY_LICENSES.md), [data provenance](docs/FUENTES_DATOS.md), and [SI disclosure](docs/SI_USAGE.md).

The project is independent and is not endorsed or certified by NASA or Uruguayan authorities. The remaining asset ownership and contributor approvals are release checks, not established clearances.

## What remains uncertain or unfinished

- **Quantitative harmonization:** No demonstrated coverage-corrected, calibrated MODIS–VIIRS historical trend, sensor equivalence or validated uncertainty interval.
- **Ground truth:** No completed external institutional validation or confirmed-fire detection rate; synthetic matching tests are identified.
- **Completeness:** Some historical periods and instruments have partial uploads; missing observations are not zero events.
- **Scientific map limits:** Approximate boundary/geometry may be used; density heatmaps show observation concentration, not burned area.
- **Operational status:** Not for emergency dispatch, official alerting or predictive fire-risk claims.
- **Deployment & public access:** A team-provided [live Streamlit deployment](https://ignis-uy-nasa-space-apps-jhw9zqnrnsardpgxulfzq9.streamlit.app/) is linked above; its logged-out accessibility and actual deployed version, as well as the Canva/Drive links, must still be checked by the team.
- **SI compliance and attribution:** Final independent review of every binary image, presentation asset, video, logo and license is still required.
- **Hackathon development provenance:** The team must accurately represent any work created before the challenge and confirm relevant eligibility requirements with organizers where applicable.

## Documentation and team contributions

| Document | Purpose |
| --- | --- |
| [Data sources](docs/FUENTES_DATOS.md) | Implemented versus pilot/proposed services and provenance |
| [Scientific methodology](docs/METODO_CIENTIFICO.md) | Grid/day matching, proximity rules, temporal statistics and fusion |
| [Validation and limitations](docs/VALIDACION_Y_LIMITES.md) | Evidence, biases, missing validation and known risks |
| [V5 quality and matching](docs/V5_CALIDAD_Y_PAREO.md) | Record identification, UTC matching and inventory checks |
| [SI provenance](docs/SI_USAGE.md) | Code, data, media and branding requirements |
| [Ask IGNIS/AI notes](docs/USO_DE_IA.md) | Rule-based assistant and SI tool-use log |
| [Roadmap](docs/HOJA_DE_RUTA.md) | Future calibrated methods and validation |
| [Team contributions](TEAM_IGNIS_CONTRIBUCIONES.md) | Questions and community contribution workflow |

Team contribution document: [TEAM_IGNIS_CONTRIBUCIONES.md](TEAM_IGNIS_CONTRIBUCIONES.md).

**Team members credited in the project presentation:** Nahuel Sanabria, Sara Pastor, Danna Rodríguez, Jordan Danielli and Fabricio Saravia.

---

**Independent research prototype — no NASA endorsement.** Satellite thermal detections are not confirmed fires; exploratory harmonization and associations are not validated operational products. Publication of this repository does not by itself establish competition eligibility or complete SI-media compliance.
