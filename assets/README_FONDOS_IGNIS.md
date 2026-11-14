# IGNIS UY homepage backgrounds

These four images were provided by the project team and optimized as WebP for the Home page. They are hosted in the repository, not an external service.

| Location | File | Depiction |
|---|---|---|
| Main hero | `bg_portada.webp` | South America with Uruguay highlighted and a satellite |
| Satellite observations | `bg_observaciones.webp` | A satellite scanning the region |
| Scientific Atlas | `bg_atlas.webp` | Uruguay highlighted on Earth |
| Traceability | `bg_trazabilidad.webp` | Documents, analysis, and a verification shield |

## Integration

The images are loaded in `ignis_visual.py` through `_apply_local_home_backgrounds()`. The function uses `asset_uri(path, "image/webp")` and emits high-contrast dark-gradient CSS rules. It only affects the Home page. Missing images fall back to previous section backgrounds; the hero also retains its local SVG fallback.

These assets **are illustrative artwork**. They are not dated satellite imagery, validated coordinates, actual wildfire locations, or NASA FIRMS detection evidence. Glowing points and illustrative borders must not support geospatial inference.

Harmonization algorithms, scientific maps, ZIP imports, external validation, and filters were not modified.
