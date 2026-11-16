# Super Intelligence (SI) use and provenance — IGNIS UY

This disclosure is part of the public project, visible to reviewers and visitors. IGNIS UY is an **independent** research prototype, not a NASA product or an endorsed NASA application.

## SI-use categories (select all that apply)

- **Code:** YES. Generative language-model assistance was used to design, draft, revise, debug and document Python, HTML/CSS and JavaScript components. The project team remains responsible for inspection, testing, provenance and scientific claims. SI-assisted code is acknowledged in this document, the repository README and the Master-data export manifest.
- **Images:** YES. The illustrative home hero and three feature-card background artworks are treated as SI-generated/assisted. A prominent **“SI-generated illustration”** watermark is rendered directly over each image wherever the web app displays it. These illustrations are not NASA imagery or evidence of wildfire activity.
- **Data:** SI-assisted code organizes and derives summaries from externally sourced NASA FIRMS MODIS/VIIRS observations. **The source observations are not SI-generated.** No fabricated hotspot measurements, dates, satellite passes or fire confirmations should be supplied by SI. Exported Master ZIPs include code-processing and data-source provenance in `manifest.json`.
- **Text:** YES. SI tools assisted explanatory, interface and documentation prose. Statements require human review and external evidence for scientific accuracy.
- **Audio:** YES, in the planned supplemental website walkthrough: HeyGen AI Voice (Janet — Warm & Approachable, en-US) synthesized the approximately 10-minute English narration from a script prepared with SI assistance. The synthesized narration is not part of the Streamlit app itself. **Before the video is published, label the narration as SI-generated in its public description and video/audio metadata.**
- **Videos:** A website screen-recording walkthrough is planned with the SI-generated voice above; the completed video has not yet been published or audited. A human-captured screen recording is not automatically a wholly SI-generated visual. If generated footage or images are incorporated, their displayed versions must bear visible `SI-generated` watermarks.

## Illustrated UI inventory

| Displayed illustration | Location | SI indicator |
| --- | --- | --- |
| `assets/bg_portada.webp` (fallbacks `assets/ignis_hero_premium.svg` or `hero_espacio.jpg`) | Home hero | Visible “SI-generated illustration” overlay |
| `assets/bg_observaciones.webp` | Home / Observations card | Visible overlay |
| `assets/bg_atlas.webp` | Home / Atlas card | Visible overlay |
| `assets/bg_trazabilidad.webp` | Home / Traceability card | Visible overlay |
| Procedural 3D terrain and simulated orbit graphics | Dashboard / 3D views | Marked illustrative; SI-assisted software disclosed here and in README |

This inventory reflects identified UI usages. **A rendered overlay is not baked into the original WebP/JPEG/SVG file.** Anyone distributing raw source image files, screenshots that crop out the watermark, or exported imagery must apply a visible watermark to that exported media itself before submission. Do not infer that all image assets in the repository have been checked simply from this list.

## NASA identifiers, branding and source attribution

SI-generated artwork must **not** contain, recreate, or alter NASA insignia, logos, flags, mission patches or other protected NASA branding/design elements. The use of the words NASA FIRMS, MODIS and VIIRS in factual citations and source attribution is distinct from depicting branded insignia in generated artwork. No NASA logo, patch, flag or mission identifier should be introduced into any SI-created visual. NASA FIRMS observations must retain clear data-source credit. IGNIS UY is not affiliated with or endorsed by NASA.

**Human-review gate:** Before final competition submission, inspect all original graphics (including `logo_ignis.png`, home fallback assets, graphics in PDF/video exports and any new project media) for NASA insignia or mission design elements. Remove or replace prohibited imagery and ensure watermarks are visible on *every* SI-generated image/video. This repository change adds disclosures but cannot prove the provenance or contents of every existing binary asset.

## Publication checklist

1. Verify each image and video origin with the artist/author; keep generation records where available.
2. Apply a visible **SI-generated** watermark to every SI-generated image/video, including exported media; do not rely solely on web overlays for standalone files.
3. Add “SI-generated” to audio description and metadata before publishing any synthetic audio.
4. Keep source-data and SI-assisted processing provenance in every code/data release, ZIP manifest and report.
5. Check every image/video for NASA insignia, flag, mission identifier or other NASA branding/design elements. Do not use or modify those elements with SI tools.
6. Human-review scientific interpretations, outputs and challenge disclosures; select the SI-use options accurately.

## How this disclosure is maintained

This is a project-level declaration, **not** an assertion that every output was wholly written by SI or that NASA observations were generated by SI. Update this document and the machine-readable `docs/si_usage.json` whenever an SI-enabled asset, model, medium or workflow is added. The application-level UI watermark is implemented by `ignis_visual.py`, and the Master export manifest by `ignis_historico.py`.
