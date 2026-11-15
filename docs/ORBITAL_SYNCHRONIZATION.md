# IGNIS UY — Synchronized orbital tracking and 3D spatial views

## Fix for the satellite / last-pass discrepancy

The previous dashboard continuously illustrated satellites orbiting Uruguay while
the Earth page used a different TLE animation clock. The scientific mode now
consumes one shared orbital service (ignis_orbits.py) in both renderers.

**Current tracking**: Skyfield propagates up-to-date CelesTrak TLEs using
SGP4 and WGS84 geodetic coordinates. Both map pages use the same UTC reference
and timestamped ephemeris. The frontend smoothly interpolates real calculated
samples instead of advancing an independent orbit phase. A satellite outside
the local Uruguay map is not artificially drawn above the country.

**Selected UTC**: Choose a timezone-aware UTC date and time in 3D Earth.
Both views read the same Streamlit session state. Historical dates without
matching archived TLE elements result in an unavailable marker, not a
fake historical orbit. The imported FIRMS observation year/date is separate.

**Last / next pass**: a roughly 40-second sampled crossing of the satellite's
SUBSATELLITE GROUND TRACK through a simplified Uruguay national polygon.
Replays show the same timestamped SGP4 track used by the calculation.
These events are *not* verified sensor swath intersections, thermal detections,
or confirmed wildfires. No pass is displayed if the TLE is unsuitable or
the 24-hour search interval contains no complete sampled crossing.

**Illustrative mode**: Opt-in cinematic animations and schematic beams are
explicitly marked NOT REAL-TIME TRACKING. Scientific pass controls are
disabled in illustrative mode. Calculated mode does not show beams because
validated instrument field-of-view geometry is not implemented.

## Data source and limitations

- CelesTrak GP/TLE query by NORAD catalog number and timestamped retrieval.
- Skyfield EarthSatellite and WGS84 geographic_position_of.
- Current implementation allows 5 days maximum from TLE epoch per sample
  and requires less than 4 days at the reference timestamp when using
  a ±24-hour pass window. This is a conservative software policy, not
  a guarantee of prediction precision.
- A result can be unavailable due to network, old elements, missing Skyfield,
  propagation error, or no crossing in the bounded interval.
- Historical TLE archives have **not** been connected. Do not extrapolate a
  2026 TLE to a 2000–2025 FIRMS acquisition date.
- Ground-track pass results rely on an approximate polygon and sampled times;
  accurate instrument coverage needs sensor swath geometry and validation.
- Planet, atmospheric effects and local 3D terrain are visual stylizations,
  not verified terrain elevation or live satellite imagery.

## Integrated spatial views

A single reusable adapter in ignis_spatial.py renders data-grounded 3D maps
across the Dashboard, Uruguay Atlas, Historical Archive, Alerts & Traceability,
Recent NASA FIRMS Monitoring and Satellite–Ground Fusion. It preserves
existing source data, coordinates, timestamps and scientific total counts.
The 3D Earth & Satellites page uses the same orbital service.
Original 2D selection charts and accessible fallbacks remain available.
PDF reports remain static because interactive WebGL cannot run inside a PDF.

## Tests and rollout

GitHub Actions checks Python compilation, Streamlit startup, SGP4 epoch
and geodetic propagation, refusal of stale TLEs, ground-track crossing
semantics, cross-page clock consistency, map adapters, JavaScript syntax and
a browser-rendered synthetic fixture. No production fire records are
fabricated by the orbital engine or map adapters.

Review the PR before merging. An actual Streamlit Cloud browser check using
imported FIRMS records is recommended before production release.

References: https://rhodesmill.org/skyfield/earth-satellites.html
and https://celestrak.org/NORAD/elements/
