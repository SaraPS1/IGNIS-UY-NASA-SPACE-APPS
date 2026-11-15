# IGNIS UY — 3D globe, 2D report-map and reliability audit

## Scope and working baseline
Base: current `main` following merged orbital synchronization PR #13.
This change is intentionally isolated in its own review branch.

### Defects investigated and corrected

1. **Blank 3D Earth on Streamlit:** A scoping error declared
   `scientific` and selected-UTC variables inside a satellite iteration,
   then read them later from the outer animation loop. That produced a
   JavaScript runtime ReferenceError without a Python syntax error.
   The clock state is now declared once at the correct scope.
2. **Remote texture failure was treated as a global failure:** the globe
   now uses a bundled public-domain Natural Earth fallback surface
   (see `assets/README_WORLD_FALLBACK.md`). Optional external Blue Marble,
   nighttime and cloud textures can fail independently without destroying
   a functional WebGL scene.
3. **Module/CDN/WebGL failure:** an independent classic-script watchdog
   can draw a local scientific 2D Uruguay outline and FIRMS markers, with
   a retry control, even if Three.js modules never load.
4. **Uruguay camera preset overrode the intended view:** refocused the
   regional camera on the southern +X/+Z hemisphere, with a better Earth
   field of view and material fallbacks.
5. **Live orbit playback:** Current UTC runs on the real UTC clock at
   1×. Speed selectors affect replay/illustrative modes, not live
   position calculations. The UI disables pause and speed while Current
   UTC is selected.
6. **Overlapping status messages:** report clear distinctions between
   successfully rendered 3D, 3D with fallback imagery, and a true 2D
   fallback after WebGL/JavaScript-module errors.
7. **Home typography:** increased the left inset of the “What you can
   do with IGNIS” heading only, without a global content shift.
8. **Historical atlas filtering mismatch:** the All Records choice now
   supplies all years to *both* scientific map representations.

## Spatial map inventory

| Page | 3D | Adjacent scientific 2D | Report/export behavior |
| --- | --- | --- | --- |
| Home / Mission Control | Interactive 3D Uruguay | Same-filter 2D right of 3D | PNG from scientific PDF map renderer; report route unchanged |
| Uruguay Atlas | Interactive 3D | Same-filter 2D | PNG from scientific PDF map renderer |
| Historical Archive | Interactive 3D | Accumulated 2D map | PNG from scientific PDF map renderer |
| Alerts & Traceability | 3D observation context when loaded | Corresponding 2D scientific map | PNG from scientific PDF map renderer |
| Recent FIRMS monitoring | 3D from returned observations | Same-query 2D map | PNG + existing CSV |
| 3D Earth & Satellites | Immersive Three.js globe | Selected-date Uruguay 2D scientific view | PNG; independently renders if globe unavailable |
| Satellite–Ground Fusion | Data-derived FIRMS and candidate association 3D view | Same-period 2D view | Separate selected-cell PDF has *exact* 2D cell map also previewed in the app |
| Spatial Density analytics | 3D | Same-period 2D | PNG from scientific PDF map renderer |
| Main PDF Report | Interactive WebGL not embedded in PDF | Static 2D from `ignis_informe.map_figure` | Unchanged scientific PDF |
| Fusion selected-cell PDF | 3D used only in app | Static historical recurrence + imported evidence | Exact PNG rendered by `_mapa_estatico_para_pdf` |
| MODIS–VIIRS harmonization (nongeographic tables/plots) | No fake 3D geography | Existing statistics | Existing analyses retained |

Every pair normalizes its real source records and applies the same
selected year/region/date **before** either map renders. The 3D
renderer may visually sample markers for performance but does not alter
the summary totals; the 2D static map uses the selected full records.

## Scientific boundaries

- A NASA FIRMS thermal anomaly is not a confirmed wildfire.
- Satellite ground-track crossing is not verified MODIS/VIIRS sensor
  swath coverage. Historical orbital reconstruction requires
  appropriate archived TLEs, which are not yet connected.
- Generalized Natural Earth country outlines are cartographic
  references, not official boundaries or measured terrain elevation.
- The Earth globe uses stylized lighting and optional *static* NASA
  Earth textures; it must not claim to show historical live Earth
  imagery, live cloud conditions or operational fire alerts.
- Imported ground reports and proximity/association candidates are
  marked for review, not presented as verified incidents.

## Browser and regression testing

`.github/workflows/ignis-globe-runtime.yml` compiles the application,
runs existing and new tests, starts Streamlit in the smoke test, and
uses real headless Chromium/Playwright to exercise:

1. Full 3D WebGL initialization and real DOM controls.
2. Blocked external planet textures while maintaining a visible 3D globe.
3. Blocked Three.js modules, producing the local 2D fallback and Retry.
4. JavaScript runtime errors (not just syntactic validity).
5. A measurable visible planet, so a black-but-working canvas fails.
6. 2D PNG generation without WebGL, matching the report renderer.
7. Data-source normalization and paired map callsites.

Screenshots are uploaded as CI artifacts. Synthetic fixture markers
are clearly labeled, and are **never** written to the production
observation database.

## Important remaining limitations (must not be claimed as complete)

- Real production Streamlit Cloud needs post-merge visual inspection
  with the team's imported NASA FIRMS files and actual satellite TLEs.
  The standalone WebGL browser tests do not verify all Streamlit iframe
  navigation interactions across every production page.
- The common map pair synchronizes **filters, source observations and
  report output**, not click-to-click selection across Streamlit iframe
  boundaries. Implement a proper bidirectional Streamlit component
  before claiming full interactive cross-highlighting.
- Earth day/night visual lighting is not a full physical sun ephemeris,
  and the country-outline fallback is intentionally lower resolution
  than real Blue Marble imagery.
- Three.js module loading still uses a CDN in production; if unavailable
  the **2D fallback** works, but full offline 3D would require separately
  vendoring the module bundle and auditing its license.
- High-resolution atmospheric cloud imagery and instrument swaths are
  optional/not validated by the fallback renderer.
- The fusion page preserves its clickable 2D recurrence grid and
  selected-cell PDF workflow; the synchronized 3D/2D overview is
  below that input grid because association calculations depend on
  its selections.
- PNG report maps are static; interactive 3D WebGL is not embedded in PDF.

## Further roadmap
- Replace illustrative Earth lighting with an appropriately validated
  sun position if true time-correct illumination is required.
- Implement verified sensor swath coverage separately from orbital
  ground tracks.
- Implement true bidirectional 3D↔2D feature focus in a registered
  Streamlit component.
- Record per-route end-to-end browser interaction screenshots from a
  complete deployed application with approved real FIRMS data.
- Evaluate local Three.js bundling and lighter 3D scene lifecycle for
  older browsers and mobile devices.

Do not merge this branch until the team reviews the screenshots and
checks the actual deployed interface.
