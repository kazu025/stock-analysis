"""ma25_flat_below_ma75.csvを順番にチャート表示する起動用スクリプト。

チャート描画と操作は 02_chart_ma25_cross_approaching.py と共通です。
"""
from pathlib import Path
import runpy
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
CHART_SCRIPT = SCRIPT_DIR / "02_chart_ma25_cross_approaching.py"
DEFAULT_CSV = SCRIPT_DIR / "ma25_flat_below_ma75.csv"


if "--csv" not in sys.argv:
    sys.argv[1:1] = ["--csv", str(DEFAULT_CSV)]

runpy.run_path(str(CHART_SCRIPT), run_name="__main__")
