# -*- coding: utf-8 -*-
"""
midday.py — מנוע מסחר "רגיעת הצהריים" בבורסת ת"א (Mean Reversion).
מבוסס על המחקר: בשעות אמצע היום הנזילות יורדת והשוק "חוזר לממוצע" (לא פורץ).
מתאים לתפיסת תנועה קטנה (0.5%-1%) של לונג/שורט על ת"א 35.

השיטה (אסטרטגיה #2 מהמחקר — לא דורשת נפח, מתאימה למדד שאין לו נפח):
  • רצועות בולינג'ר (20,2) על גרף 5 דקות.
  • RSI מהיר (9) עם רמות קיצון 72/28 (במקום 70/30).
  • פילטר ADX(14) < 25 — לוודא שוק "רגוע" ללא מגמה (התנאי הכי חשוב).
  • חלון צהריים בלבד (ברירת מחדל 13:00–16:00 שעון ישראל).

כניסה LONG:  המחיר מתחת לרצועה התחתונה + RSI(9) < 28  → יעד: רצועת האמצע (SMA20).
כניסה SHORT: המחיר מעל הרצועה העליונה + RSI(9) > 72  → יעד: רצועת האמצע.
סטופ: 0.5*ATR מעבר לנר. Time-Stop: סגירה אחרי 15 נרות (75 דק') אם לא הגיע ליעד.

⚠️ מגבלות שחובה להכיר:
  • הנתונים מושהים ~15 דק' — לביצוע חי צריך פיד בזמן אמת מהברוקר.
  • ת"א 35 הוא מדד — סוחרים אותו דרך תעודת סל/חוזה עתידי/CFD שמאפשר לונג ושורט.
  • יש לקזז עמלות ומרווח (Spread) — בצהריים הם מתרחבים; 0.5%-1% זה *אחרי* עלויות.
  • היסטוריית 5-דק' מוגבלת (~חודש), אז הבק-טסט מכוון-כיוון, לא הוכחה.
"""

import numpy as np
import pandas as pd

import engine

TZ = "Asia/Jerusalem"


def _local_index(df):
    idx = df.index
    try:
        if idx.tz is None:
            idx = idx.tz_localize("UTC")
        return idx.tz_convert(TZ)
    except Exception:
        return idx


def compute(df):
    """מחשב בולינג'ר, RSI(9), ADX, ATR, TWAP-יומי ושעת-יום (שעון ישראל)."""
    df = df.dropna().copy()
    close = df["Close"]
    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    df["bb_mid"] = mid
    df["bb_up"] = mid + 2 * std
    df["bb_lo"] = mid - 2 * std
    df["rsi9"] = engine.rsi(close, 9)
    df["adx"] = engine.adx(df, 14)
    df["atr"] = engine.atr(df, 14)

    local = _local_index(df)
    df["hour"] = local.hour + local.minute / 60.0
    df["day"] = pd.Index(local.date, name="day")
    # TWAP יומי (ממוצע מצטבר של מחיר טיפוסי — "שווי הוגן" ללא צורך בנפח)
    tp = (df["High"] + df["Low"] + df["Close"]) / 3
    df["twap"] = tp.groupby(df["day"].values).transform(lambda s: s.expanding().mean())
    return df


def _bar_signal(row, win):
    """מחזיר ('LONG'/'SHORT'/'WAIT', reason) עבור נר בודד."""
    if not (win[0] <= row["hour"] < win[1]):
        return "WAIT", "מחוץ לחלון הצהריים"
    if np.isnan(row["adx"]) or np.isnan(row["bb_lo"]):
        return "WAIT", "אין מספיק נתונים"
    if row["adx"] >= 25:
        return "WAIT", f"מגמה חזקה (ADX {row['adx']:.0f}≥25) — לא לסחור חזרה-לממוצע"
    if row["Close"] <= row["bb_lo"] and row["rsi9"] < 28:
        return "LONG", f"מתחת לרצועה התחתונה + RSI {row['rsi9']:.0f} (מכירת יתר) → צפי לתיקון מעלה"
    if row["Close"] >= row["bb_up"] and row["rsi9"] > 72:
        return "SHORT", f"מעל הרצועה העליונה + RSI {row['rsi9']:.0f} (קניית יתר) → צפי לתיקון מטה"
    return "WAIT", "המחיר בתוך הרצועות — אין קיצוניות"


def current_signal(df, win=(13.0, 16.0), tp_pct=0.6, sl_pct=0.4):
    """מצב עכשווי לפי הנר האחרון + רמות מסחר (יעד/סטופ באחוזים שאתה בוחר)."""
    d = compute(df)
    if len(d) < 25:
        return None
    row = d.iloc[-1]
    sig, reason = _bar_signal(row, win)
    price = float(row["Close"])
    if sig == "LONG":
        tgt = price * (1 + tp_pct / 100)
        stop = price * (1 - sl_pct / 100)
    elif sig == "SHORT":
        tgt = price * (1 - tp_pct / 100)
        stop = price * (1 + sl_pct / 100)
    else:
        tgt, stop = np.nan, np.nan
    return dict(signal=sig, reason=reason, price=price, target=tgt, stop=stop,
                bb_up=float(row["bb_up"]), bb_lo=float(row["bb_lo"]), bb_mid=float(row["bb_mid"]),
                rsi9=float(row["rsi9"]), adx=float(row["adx"]),
                hour=float(row["hour"]), exp_move_pct=tp_pct, data=d)


def backtest(df, win=(13.0, 16.0), tp_pct=0.6, sl_pct=0.4, time_stop=15, cost_pct=0.05):
    """בק-טסט של אסטרטגיית הצהריים. יעד/סטופ באחוזים; cost_pct = עמלה+מרווח לסבב."""
    d = compute(df).dropna(subset=["bb_lo", "adx", "rsi9", "atr"]).reset_index(drop=True)
    if len(d) < 50:
        return None
    trades = []
    i = 0
    n = len(d)
    while i < n:
        row = d.iloc[i]
        sig, _ = _bar_signal(row, win)
        if sig not in ("LONG", "SHORT"):
            i += 1
            continue
        entry = row["Close"]
        if sig == "LONG":
            target = entry * (1 + tp_pct / 100)
            stop = entry * (1 - sl_pct / 100)
        else:
            target = entry * (1 - tp_pct / 100)
            stop = entry * (1 + sl_pct / 100)

        pnl, exit_idx = None, i
        for j in range(i + 1, min(i + 1 + time_stop, n)):
            b = d.iloc[j]
            exit_idx = j
            if b["day"] != row["day"]:                 # לא מחזיקים ליום הבא
                pnl = (b["Open"] / entry - 1) * (1 if sig == "LONG" else -1)
                break
            if sig == "LONG":
                if b["Low"] <= stop: pnl = stop / entry - 1; break
                if b["High"] >= target: pnl = target / entry - 1; break
            else:
                if b["High"] >= stop: pnl = -(stop / entry - 1); break
                if b["Low"] <= target: pnl = -(target / entry - 1); break
        if pnl is None:                                # Time-Stop
            exit_idx = min(i + time_stop, n - 1)
            pnl = (d.iloc[exit_idx]["Close"] / entry - 1) * (1 if sig == "LONG" else -1)

        trades.append({"dir": sig, "pnl_pct": pnl * 100 - cost_pct})  # אחרי עלויות
        i = exit_idx + 1
    tr = pd.DataFrame(trades)
    if tr.empty:
        return dict(trades=0, win_rate=0, avg=0, total=0, best=0, worst=0, table=tr)
    wins = tr[tr["pnl_pct"] > 0]
    return dict(
        trades=len(tr),
        win_rate=len(wins) / len(tr) * 100,
        avg=tr["pnl_pct"].mean(),
        total=tr["pnl_pct"].sum(),
        best=tr["pnl_pct"].max(),
        worst=tr["pnl_pct"].min(),
        table=tr,
    )
