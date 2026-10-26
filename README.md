# Sprint 2 — Las Pintas (PIN), 2023 y 2024
Análisis comparativo de calidad del aire (Índice AIRE Y SALUD, NOM-172-SEMARNAT-2023) con perspectiva de transporte de pollos.

## Reproducir
1. Instalar dependencias: `pip install -r requirements.txt`
2. Descargar `BD_2023.xlsx` y `BD_2024.xlsx` de https://aire.jalisco.gob.mx/Dhistoricos y colocarlos en `data/`
3. `python analysis.py data/BD_2023.xlsx data/BD_2024.xlsx` → genera en `out/`: `horario.csv`, `diario.csv`, `mensual.csv`, figuras PNG y `R.json`
4. `python dash.py` → maqueta del dashboard (`out/fig_dashboard.png`)

## Archivos
- `pipeline.py`: carga/filtra PIN, NowCast, categorías horarias y resumen diario
- `analysis.py`: cobertura, comparación 2024 vs 2023, episodios, meteorología y figuras
- `dash.py`: propuesta de dashboard con las mismas tablas
