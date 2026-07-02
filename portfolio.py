# -*- coding: utf-8 -*-
"""
portfolio.py — לוגיקת תיק (רווח/הפסד + דגל מכירה), שמירה/טעינה, ומחשבון פוזיציה.
"""

import os

import pandas as pd

import config

# הקובץ שבו נשמר התיק בין הפעלות (על דיסק השרת) — גיבוי מקומי
PORTFOLIO_FILE = os.path.join(os.path.dirname(__file__), "portfolio_data.csv")
_COLS = ["ticker", "entry_price", "qty"]


# ------------------------------------------------------------------
# Google Sheets (שמירה קבועה שלא מתאפסת גם אחרי עדכון קוד) — אופציונלי
# מופעל רק אם הוגדרו הסודות ב-Streamlit; אחרת נופל אוטומטית ל-CSV מקומי.
# ------------------------------------------------------------------
def _gsheet():
    try:
        import streamlit as st
        if "gcp_service_account" not in st.secrets or "gsheet_key" not in st.secrets:
            return None
        import gspread
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gc = gspread.authorize(creds)
        return gc.open_by_key(st.secrets["gsheet_key"]).sheet1
    except Exception:
        return None


def storage_status():
    """טקסט לתצוגה: איזה מנגנון שמירה פעיל."""
    return ("☁️ Google Sheets — שמירה קבועה (לא מתאפסת)" if _gsheet() is not None
            else "💾 שמירה מקומית — נשמרת בין כניסות, אך עלולה להתאפס בעדכון קוד")


def _load_local():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            return pd.read_csv(PORTFOLIO_FILE)[_COLS].to_dict("records")
        except Exception:
            return []
    return []


def load_holdings():
    """טוען את התיק — קודם מ-Google Sheets אם מוגדר, אחרת מהדיסק המקומי."""
    sh = _gsheet()
    if sh is not None:
        try:
            recs = sh.get_all_records()
            return [{"ticker": str(r["ticker"]),
                     "entry_price": float(r["entry_price"]),
                     "qty": float(r["qty"])} for r in recs if r.get("ticker")]
        except Exception:
            pass
    return _load_local()


def save_holdings(holdings):
    """שומר את התיק — ל-Google Sheets אם מוגדר, ותמיד גם לגיבוי מקומי."""
    sh = _gsheet()
    if sh is not None:
        try:
            sh.clear()
            sh.update([_COLS] + [[h["ticker"], h["entry_price"], h["qty"]] for h in holdings])
        except Exception:
            pass
    try:
        pd.DataFrame(holdings, columns=_COLS).to_csv(PORTFOLIO_FILE, index=False)
    except Exception:
        pass


def position_size(account, risk_pct, entry, stop):
    """כמה מניות לקנות כדי לא לסכן יותר מ-risk_pct מהתיק."""
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return dict(shares=0, dollar_risk=0, position_value=0, risk_per_share=0)
    dollar_risk = account * (risk_pct / 100)
    shares = int(dollar_risk / risk_per_share)
    return dict(
        shares=shares,
        dollar_risk=round(dollar_risk, 2),
        position_value=round(shares * entry, 2),
        risk_per_share=round(risk_per_share, 4),
    )


def evaluate_holding(row, analysis):
    """מקבל פוזיציה (מילון עם entry_price, qty) + תוצאת analyze, ומחזיר שורת מעקב."""
    price = analysis['price']
    entry = float(row['entry_price'])
    qty = float(row['qty'])
    pnl_abs = (price - entry) * qty
    pnl_pct = (price / entry - 1) * 100

    # דגל "למכור?"
    sell = False
    reason = ""
    if price <= analysis['stop']:
        sell, reason = True, "נשבר הסטופ"
    elif not analysis['st_up']:
        sell, reason = True, "היפוך מגמה (Supertrend דובי)"
    elif analysis['score'] <= config.SCORE_SELL:
        sell, reason = True, "הניקוד נחלש"
    elif analysis['rsi'] > 78:
        reason = "קניית יתר — שקול מימוש חלקי"

    return dict(
        price=round(price, 2),
        pnl_abs=round(pnl_abs, 2),
        pnl_pct=round(pnl_pct, 2),
        score=round(analysis['score'], 1),
        signal=analysis['signal'],
        stop=round(analysis['stop'], 2),
        sell=sell,
        reason=reason,
    )
