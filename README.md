# IGNIS UY — Del espacio a la evidencia territorial

**Prototipo de investigación científica independiente** que organiza observaciones de anomalías térmicas de NASA FIRMS en Uruguay, explora coincidencias entre MODIS y VIIRS y permite contrastar registros con evidencias documentales y terrestres.

> **Importante:** una detección FIRMS no equivale a un incendio único ni confirma superficie quemada. La armonización **cuantitativa** entre sensores y la validación operativa siguen pendientes.

## Qué está implementado

- Importación de NASA FIRMS MODIS/VIIRS (CSV/ZIP), deduplicación de observaciones y exportación/reimportación manual del Maestro IGNIS.
- Consultas recientes de NASA FIRMS mediante MAP_KEY, iniciadas bajo demanda.
- Mapas, series temporales, calendarios por instrumento y PDF científico.
- Coincidencia exploratoria por **día UTC y celda de 0,20°**; pareo alternativo por **5 km y 30 min** (umbrales configurables).
- **Laboratorio de sensibilidad de cuadrículas**: comparar 0,05°, 0,10°, 0,20° y 0,40° con el mismo recorte y exportar resultados a CSV.
- Monitoreo reciente que incluye NOAA-21; importación histórica de archivos **mixtos** con identificación del instrumento por registro.
- **Pareo científico V5 alternativo:** coincidencias únicas a través de medianoche UTC y exportación de pares con dos fechas, distancias y FRP original.
- **Auditoría de calidad FIRMS:** coordenadas, fechas, horarios, FRP, posibles duplicados e inventario mensual con advertencia de cobertura no verificada.
- **NASA Worldview:** enlace por fecha y localización desde el Atlas y desde el monitoreo NRT.
- Trazabilidad documental, asociación experimental NASA–Bomberos/PAIF–SINAE/MIRA, sección de aportes e interfaz Ask IGNIS **basada en reglas** (no es un LLM).

Los archivos disponibles en una sesión no garantizan cobertura temporal o instrumental completa. Las salidas **no son alertas oficiales**.

## Cómo ejecutar

Python 3.11 recomendado.

```bash
python -m pip install -r requirements.txt
streamlit run principal.py
```

Configurar `FIRMS_MAP_KEY` en los secrets de Streamlit para consultas recientes (ver `.streamlit/secrets.toml.example`). **Nunca publicar claves en el repositorio.** Los ZIP/CSV históricos se cargan desde la interfaz y el Maestro se descarga como respaldo para la siguiente sesión.

### Pruebas de ciencia

```bash
python -m unittest discover -s tests -p "test_ignis_sensibilidad.py" -v
python -m unittest discover -s tests -p "test_ignis_pareo_calidad_v5.py" -v
```

Las pruebas sintéticas de sensibilidad no sustituyen validación con incendios confirmados.

## Premium 3D control center (English UI)

The **Control center** page is an interactive geospatial dashboard built on the
existing Python/Streamlit backend:

- `ignis_scene3d.py` + `assets/ignis_scene3d.html` — an isolated Three.js
  component (loaded from a CDN inside `st.components.v1.html`, no build step)
  that renders an extruded Uruguay with an illuminated outline, an Earth
  backdrop with atmosphere and clouds, schematic satellites with orbit trails
  and observation beams, instanced NASA FIRMS thermal observations (height ∝
  FRP, tooltip with the real metadata), the 0.2° historical recurrence grid,
  documented reference towns, satellite–ground associations from the fusion
  page, a 2000–2026 timeline with play/pause/speed, a radial camera menu,
  cinematic mode, a *Reduce motion* setting, adaptive quality and a 2D canvas
  fallback when WebGL or the CDN is unavailable.
- `ignis_dashboard.py` — design system (deep navy / electric cyan / wildfire
  orange palette), top bar, animated metric strip, the integrated Ask IGNIS
  panel and the analytics tabs (historical activity, spatial density, monthly
  calendar, sensor comparison, satellite–ground fusion).

Scientific integrity rules kept by the redesign:

- Every marker and every number comes from the records imported in the
  session; empty states say so instead of showing demonstration figures.
- "Live" is shown only when a real NRT query has been executed; otherwise the
  interface says *Historical data* with the latest imported timestamp.
- Relief and orbits are explicitly labelled as illustrative. Verified
  TLE-based trajectories remain in **3D Earth & Satellites**.
- Department boundaries are drawn only if a verified GeoJSON is placed at
  `assets/uruguay_departamentos.geojson` (Polygon/MultiPolygon features with
  a `name` property); otherwise the toggle reports that no verified dataset is
  available.

## Documentación y atribución

| Documento | Contenido |
|---|---|
| [Fuentes de datos](docs/FUENTES_DATOS.md) | NASA FIRMS y otros servicios: usado, piloto o propuesto |
| [Método científico](docs/METODO_CIENTIFICO.md) | Fórmulas, criterios, discretización, pares y requisitos de calibración |
| [Validación y límites](docs/VALIDACION_Y_LIMITES.md) | Casos, alcance de pruebas, sesgos e incertidumbre pendiente |
| [Calidad y pareo V5](docs/V5_CALIDAD_Y_PAREO.md) | Importación por fila, cruces de medianoche, inventario de datos y Worldview |
| [Uso de IA](docs/USO_DE_IA.md) | Capacidades reales de Ask IGNIS y registro de herramientas por completar |
| [Hoja de ruta](docs/HOJA_DE_RUTA.md) | Fases hacia cobertura, armonización cuantitativa y visualización NASA GIBS |
| [Contribuciones](TEAM_IGNIS_CONTRIBUCIONES.md) | Consultas públicas mediante GitHub Issues |

**Datos:** NASA [Fire Information for Resource Management System (FIRMS)](https://www.earthdata.nasa.gov/data/tools/firms), parte de EOSDIS. Se reconoce la procedencia de las observaciones MODIS y VIIRS. IGNIS UY no es una aplicación de NASA ni cuenta con aprobación institucional implícita.

**Estado del desafío:** esta versión **no** demuestra corrección completa de los saltos en la serie histórica debidos a cambios de sensores. Los recuentos de detecciones se muestran sin normalización por cobertura y las pruebas de coincidencia son exploratorias.

El README y los datos exportados documentan lo que el prototipo realiza realmente; cualquier modelo calibrado deberá publicar metodología, pruebas fuera de muestra e intervalos antes de presentarse como resultado científico.
