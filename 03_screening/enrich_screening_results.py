"""既存のlarge_scale_screen_result.csvに直近性の指標を追加する。

入力CSVと同じディレクトリで実行する想定。
"""
from pathlib import Path
import pandas as pd
import yfinance as yf

RANGE_DAYS = 60
ZONE_RATIO = 0.25
INPUT = Path(__file__).with_name("large_scale_screen_result.csv")
OUTPUT = Path(__file__).with_name("large_scale_screen_result_enriched.csv")

def wave_fields(df):
    df = df.dropna(subset=["High", "Low", "Close"]).tail(RANGE_DAYS).copy()
    hi, lo = float(df["High"].max()), float(df["Low"].min())
    width = hi - lo
    if width <= 0 or lo <= 0:
        raise ValueError("invalid range")
    upper, lower = hi - width * ZONE_RATIO, lo + width * ZONE_RATIO
    up = df["High"] >= upper
    down = df["Low"] <= lower
    touches = []
    for i, idx in enumerate(df.index):
        if bool(up.iloc[i]) and not (i and bool(up.iloc[i-1])):
            touches.append((idx, "UPPER"))
        if bool(down.iloc[i]) and not (i and bool(down.iloc[i-1])):
            touches.append((idx, "LOWER"))
    alternating = []
    for date, side in touches:
        if not alternating or alternating[-1][1] != side:
            alternating.append((date, side))
    switches = alternating[1:]
    last_switch = switches[-1][0] if switches else pd.NaT
    current = float(df["Close"].iloc[-1])
    pos = (current - lo) / width * 100
    since = len(df.loc[last_switch:]) - 1 if pd.notna(last_switch) else None
    return {
        "LastSwitchDate": last_switch.strftime("%Y-%m-%d") if pd.notna(last_switch) else "",
        "CurrentPrice": current,
        "CurrentPositionPct": pos,
        "DaysSinceLastSwitch": since,
    }

def main():
    result = pd.read_csv(INPUT, dtype={"Code": str})
    rows = []
    for _, row in result.iterrows():
        try:
            hist = yf.Ticker(str(row["Ticker"])).history(period="1y", auto_adjust=False)
            fields = wave_fields(hist)
        except Exception as exc:
            fields = {"LastSwitchDate": "", "CurrentPrice": None,
                      "CurrentPositionPct": None, "DaysSinceLastSwitch": None,
                      "EnrichmentError": str(exc)}
        rows.append(fields)
    result = pd.concat([result.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    result.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"saved: {OUTPUT}")

if __name__ == "__main__":
    main()
