# IGNIS UY — Pitch-safe Presentation Mode / 3D Explorer

## Why this change exists

The team rehearsed its NASA Space Apps pitch using the original 2D-first
application. The latest 3D redesign improved capabilities, but it also
shifted familiar controls, panels, and maps. **The goal of this PR is to
preserve the rehearsed workflow while keeping all the newer functionality.**

This change is a view preference only. Scientific calculations,
uploaded data, navigation pages, model assumptions, PDFs, and data
filter keys are shared.

## What the presenter sees

**Default: Presentation Mode (the 3D Explorer toggle is OFF).**

- A fresh session opens on **Home · Discover IGNIS**, just as it did
  before the cinematic dashboard PR.
- The original sidebar navigation order and button labels are unchanged.
- Analysis filters remain in the same sidebar position and retain the
  original keys: `sidebar_region`, `sidebar_sensores`, `ignis_selected_year`.
- The Dashboard's familiar 4 metric cards, 2D Uruguay plot on the left,
  Instruments chart, External Validation, Other Tools, and monthly
  trend are restored from the pre-3D historical version, including
  the old button keys and callback routes.
- Uruguay Atlas uses its original 2D map and Tools buttons.
- Recent Monitoring uses its original 2D observation map.
- Historical Archive keeps its metrics and charts without introducing
  the extra 3D map before them.
- Alerts & Traceability starts with the original alert narrative.
- Satellite–Ground Fusion retains the original clickable grid,
  area/year selectors, selected-cell actions, and PDF report workflow.
- 3D Earth & Satellites keeps the familiar single large globe with
  the left-side orbital controls and the timeline underneath.

**3D remains available:**

- At the bottom of the sidebar, after the familiar navigation, filters
  and resource links, use **3D Explorer** to switch the display.
- On the classic Dashboard, Uruguay Atlas, Recent Monitoring and
  Satellite–Ground Fusion, a single **Explore in 3D** entry point is
  available without moving the original buttons.
- In 3D Explorer, the existing 3D/2D paired views, cinematic mission
  dashboard, and scientific reporting tools remain available.
- The advanced views include **← Back to Presentation Mode**.
- The selected page stays the same, the imported records are not reloaded,
  and previously selected sidebar filters remain unchanged.

## Pitch sequence suggestion

1. Open IGNIS (Home appears by default).
2. Follow the exact original navigation practiced by the team.
3. Explain the 2D data and MODIS–VIIRS harmonization using the familiar buttons.
4. Open Satellite–Ground Fusion and demonstrate the existing clickable grid.
5. When ready for an optional visual highlight, select **Explore in 3D**.
6. Return to **Presentation Mode** to continue the rehearsed report workflow.

There are no separate databases, duplicated NASA FIRMS records, or
independent map calculations per mode. The global toggle changes only
the presentation of the same underlying app.

## Files and regression guarantees

- `ignis_modes.py`: display preference and explicit callbacks.
- `ignis_historico.py`: default Home, sidebar toggle (after existing
  controls), historical/alerts conditional 3D visibility.
- `ignis_visual.py`: restored pre-3D dashboard and Atlas layout, optional
  advanced view.
- `ignis_nrt.py`: restore original 2D map in presentation.
- `ignis_fusion_terrestre.py`: preserve original fusion grid and reports
  while retaining the 3D pair in Explorer.
- `ignis_espacio.py`: preserve single-globe layout for the pitch and
  use 3D + report-ready 2D side by side in Explorer.
- `tests/test_ignis_presentation_compatibility.py`: protects navigation
  order, UI keys, classic layout, and state isolation.
- `.github/workflows/ignis-presentation-compatibility.yml`:
  verifies existing regressions and switches modes via Streamlit AppTest.

## Science and deployment

- Presentation Mode does not change a thermal anomaly into a confirmed
  wildfire, or a subsatellite ground-track crossing into sensor coverage.
- Advanced 3D terrain and orbit effects retain their existing scientific
  disclaimers; report maps remain static and data-driven.
- This PR is not automatically merged into the production application.
  A team walkthrough of both experiences is recommended before merging.

## Out of scope

This PR does not implement additional data sources, new risk models,
instrument swath validation, or bidirectional 3D–2D map feature
cross-highlighting. Those improvements can be separate PRs without
disrupting the pitch workflow.
