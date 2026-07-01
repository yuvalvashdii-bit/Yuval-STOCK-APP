# -*- coding: utf-8 -*-
"""
portfolio.py — לוגיקת תיק (רווח/הפסד + דגל מכירה) ומחשבון גודל פוזיציה.
"""

import config


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
