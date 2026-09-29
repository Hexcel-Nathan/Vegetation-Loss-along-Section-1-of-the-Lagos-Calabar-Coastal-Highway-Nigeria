"""Run the whole Python part of the pipeline in order (about 2 minutes).

    python python/run_all.py

Everything is written to results/. The Earth Engine part (gee/) must be run first in the
Earth Engine Code Editor, but its outputs are already included in data/, so this runs as is.
"""
import subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ['01_build_control_units.py', '02_segment_covariates.py', '03_accuracy_olofsson.py',
         '04_matching_did.py', '05_fragmentation.py', '06_hotspots.py', '07_results_workbook.py',
         '08_add_results_sheets.py', '09_figure2_workflow.py', '10_results_charts.py']
for s in STEPS:
    t = time.time()
    print(f'\n=== {s} ===', flush=True)
    r = subprocess.run([sys.executable, str(HERE / s)], stdout=subprocess.DEVNULL)
    if r.returncode:
        sys.exit(f'{s} failed (exit code {r.returncode})')
    print(f'done in {time.time() - t:.0f} s')
print('\nAll steps finished. Outputs are in results/.')
