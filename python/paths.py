"""Shared folder locations. Every script imports this, so the repo runs from any working directory."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
VEC = DATA / 'vectors'          # centrelines, footprint, segment-zone units
RAS = DATA / 'rasters'          # land-cover maps exported from Earth Engine (script gee/08)
TAB = DATA / 'tables'           # panel table exported from Earth Engine (gee/04-05) and other inputs
VAL = DATA / 'validation'       # accuracy points and labels
RES = ROOT / 'results'          # everything the Python scripts write
RES.mkdir(exist_ok=True)
(RES / 'vectors').mkdir(exist_ok=True)

ZONES = [('F', 'Footprint'), ('B1', '0–500 m'), ('B2', '500 m–1 km'), ('B3', '1–5 km')]
CRS = 'EPSG:32631'              # WGS 84 / UTM zone 31N, used throughout
