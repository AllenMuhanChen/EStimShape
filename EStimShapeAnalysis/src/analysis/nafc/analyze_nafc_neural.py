"""
Combined NAFC neural analysis: runs both raster and PSTH from a single config.
Edit the CONFIG block here; changes apply to both analyses automatically.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from clat.util import time_util

from src.analysis.nafc.analyze_nafc_neural_raster import load_data, run as run_raster
from src.analysis.nafc.analyze_nafc_neural_psth   import run as run_psth


# ═══════════════════════════ CONFIG ═════════════════════════════════════════
# ── shared ──────────────────────────────────────────────────────────────────
EXP_DB_NAME     = "allen_estimshape_exp_260426_0"
INTAN_BASE_PATH = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape/allen_estimshape_exp_260426_0/2026-04-26/"
CHANNEL_NAME    = "A-007"
SINCE_DATE      = time_util.from_date_to_now(2026, 4, 26)

# ── raster ───────────────────────────────────────────────────────────────────
RASTER_TIME_BEFORE_S = 0.2   # seconds before sample_on
RASTER_TIME_AFTER_S  = 1.5   # seconds after sample_on

# ── PSTH ─────────────────────────────────────────────────────────────────────
PSTH_TIME_BEFORE_S   = 0.6   # seconds before sample_off
PSTH_TIME_AFTER_S    = 3.0   # seconds after sample_off
BIN_SIZE_S           = 0.05  # 50 ms bins
SHOW_STD             = True  # shaded ± 1 SEM band
# ════════════════════════════════════════════════════════════════════════════


def main():
    data, err = load_data(EXP_DB_NAME, INTAN_BASE_PATH, SINCE_DATE)
    if err or data.empty:
        print(err or "No matching trials — check EXP_DB_NAME / SINCE_DATE.")
        return

    run_raster(data, CHANNEL_NAME, RASTER_TIME_BEFORE_S, RASTER_TIME_AFTER_S)
    run_psth(data, CHANNEL_NAME, PSTH_TIME_BEFORE_S, PSTH_TIME_AFTER_S, BIN_SIZE_S, SHOW_STD)


if __name__ == "__main__":
    main()
