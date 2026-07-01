# -*- coding: utf-8 -*-
"""
data.py — שליפת נתונים מ-yfinance, בנוי להתמודד עם חסימות קצב (Rate Limit)
בשרתים המשותפים של Streamlit: משיכה סדרתית (לא במקביל) + ניסיונות חוזרים עם השהיה.
מופרד מה-UI כדי שגם alerts_bot.py יוכל להשתמש בו.
"""

import time

import pandas as pd
import yfinance as yf

# הגדרות לכל מצב: תקופה + אינטרוול
MODE_SETTINGS = {
    "swing":    dict(period="2y", interval="1d"),
    "intraday": dict(period="5d", interval="15m"),
}


def _clean(df):
    if df is None or getattr(df, "empty", True):
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    return df if not df.empty else None


def _download(symbols, period, interval, group=False):
    kwargs = dict(period=period, interval=interval, progress=False,
                  auto_adjust=True, timeout=20, threads=False)  # threads=False = עדין יותר
    if group:
        kwargs["group_by"] = "ticker"
    return yf.download(symbols, **kwargs)


def fetch_one(symbol, mode="swing", retries=3):
    """טעינת נכס בודד עם ניסיונות חוזרים והשהיה מדורגת בעת חסימת קצב."""
    cfg = MODE_SETTINGS.get(mode, MODE_SETTINGS["swing"])
    for attempt in range(retries):
        try:
            df = _clean(_download(symbol, cfg["period"], cfg["interval"]))
            # למניות ת"א אין תמיד דאטה תוך-יומי — ניפול ליומי
            if (df is None or len(df) < 60) and mode == "intraday":
                df = _clean(_download(symbol, "2y", "1d"))
            if df is not None and len(df) >= 60:
                return df
        except Exception:
            pass
        time.sleep(1.5 * (attempt + 1))   # backoff: 1.5s, 3s, 4.5s
    return None


def fetch_batch(symbols, mode="swing"):
    """טעינה של רשימת נכסים. קודם ניסיון מרוכז אחד; מה שחסר — נמשך בעדינות אחד-אחד."""
    cfg = MODE_SETTINGS.get(mode, MODE_SETTINGS["swing"])
    symbols = list(symbols)
    out = {}
    data = None
    try:
        data = _download(symbols, cfg["period"], cfg["interval"], group=True)
    except Exception:
        data = None

    missing = []
    for s in symbols:
        sub = None
        try:
            if data is not None and isinstance(data.columns, pd.MultiIndex) \
                    and s in data.columns.get_level_values(0):
                sub = _clean(data[s])
        except Exception:
            sub = None
        if sub is not None and len(sub) >= 60:
            out[s] = sub
        else:
            missing.append(s)

    # השלמת החסרים בעדינות (סדרתית + השהיה קצרה) כדי לא לעורר חסימת קצב
    for s in missing:
        sub = fetch_one(s, mode, retries=2)
        if sub is not None:
            out[s] = sub
        time.sleep(0.5)
    return out
