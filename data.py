# -*- coding: utf-8 -*-
"""
data.py — שליפת נתונים מ-yfinance עם cache, ליומי ותוך-יומי.
מופרד מה-UI כדי שגם alerts_bot.py יוכל להשתמש בו.
"""

import pandas as pd
import yfinance as yf

# הגדרות לכל מצב: תקופה + אינטרוול
MODE_SETTINGS = {
    "swing":    dict(period="2y", interval="1d"),
    "intraday": dict(period="5d", interval="15m"),
}


def _clean(df):
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    return df if not df.empty else None


def fetch_one(symbol, mode="swing"):
    """טעינת נכס בודד. אם אין דאטה תוך-יומי — נופל אוטומטית ליומי."""
    cfg = MODE_SETTINGS.get(mode, MODE_SETTINGS["swing"])
    try:
        df = yf.download(symbol, period=cfg["period"], interval=cfg["interval"],
                         progress=False, auto_adjust=True)
        df = _clean(df)
        if df is None or len(df) < 60:
            # fallback ליומי (למשל מניות ת"א ללא תוך-יומי)
            df = _clean(yf.download(symbol, period="2y", interval="1d",
                                    progress=False, auto_adjust=True))
        return df
    except Exception:
        return None


def fetch_batch(symbols, mode="swing"):
    """טעינה מרוכזת של רשימת נכסים בבת אחת — מהיר בהרבה מלולאה."""
    cfg = MODE_SETTINGS.get(mode, MODE_SETTINGS["swing"])
    out = {}
    data = None
    try:
        data = yf.download(symbols, period=cfg["period"], interval=cfg["interval"],
                           progress=False, auto_adjust=True, group_by="ticker", threads=True)
    except Exception:
        data = None

    for s in symbols:
        sub = None
        try:
            if data is not None and isinstance(data.columns, pd.MultiIndex) \
                    and s in data.columns.get_level_values(0):
                sub = _clean(data[s])
        except Exception:
            sub = None
        if sub is None or len(sub) < 60:
            sub = fetch_one(s, mode)   # fallback פרטני
        if sub is not None and len(sub) >= 60:
            out[s] = sub
    return out
