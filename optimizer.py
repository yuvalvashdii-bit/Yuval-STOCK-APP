# -*- coding: utf-8 -*-
"""
optimizer.py — מנוע כיול היסטורי.
מוצא את המשקלים של האינדיקטורים שנותנים את הדיוק הכי טוב בניבוי Buy/Sell/Neutral,
ובודק את הדיוק על תקופה נפרדת שהמנוע לא ראה באימון (Out-of-Sample) — מספר אמיתי.

שלוש רמות סיכון (רמת בררנות = כמה קיצוני הציון צריך להיות כדי לפעול):
  שמרני   (q=0.15) — מעט איתותים, הכי בטוח.
  מאוזן   (q=0.30) — איזון.
  אגרסיבי (q=0.45) — הרבה איתותים.
נבדק לשני אופקים: 5 ימים ו-21 יום.

הערה על יושרה: דיוק ריאלי הוא ~55%-65%. 90% אינו בר-השגה בשוק אמיתי, וכל מספר
גבוה מזה שמתקבל "על העבר" הוא Overfitting. לכן כל המספרים כאן הם Out-of-Sample.
"""

import numpy as np
import pandas as pd

import engine

PROFILES = {
    "שמרני (כמעט ללא סיכון)": 0.15,
    "מאוזן (בטוח למחצה)": 0.30,
    "אגרסיבי (הרבה הזדמנויות)": 0.45,
}
HORIZONS = {"שבוע (5 ימים)": 5, "חודש (21 יום)": 21}
SUBSIGNAL_NAMES = ["מגמה", "Supertrend", "MACD", "RSI", "VWAP", "נפח", "Squeeze"]


def subsignal_matrix(df):
    """מחזיר מטריצה TxK של אותות כיווניים לכל אינדיקטור (כל ערך בטווח ~[-1,1])."""
    df = df.dropna().copy()
    close = df['Close']
    ema_f, ema_s = engine.ema(close, 50), engine.ema(close, 200)
    r = engine.rsi(close)
    mh = engine.macd_hist(close)
    st_trend, _ = engine.supertrend(df)
    sq_on, sq_mom = engine.ttm_squeeze(df)
    vwap = engine.anchored_vwap(df)
    vol_ratio = df['Volume'] / df['Volume'].rolling(20).mean()

    s_trend = 0.5 * np.sign(close - ema_f) + 0.5 * np.sign(ema_f - ema_s)
    s_st = np.where(st_trend, 1.0, -1.0)
    s_macd = np.clip(mh / mh.rolling(50).std().replace(0, np.nan), -1, 1).fillna(0)
    s_rsi = ((r - 50) / 50).clip(-1, 1)
    s_vwap = np.sign(close - vwap)
    s_vol = (vol_ratio - 1).clip(-1, 1).fillna(0)
    s_sq = np.where(sq_on, 0.0, np.sign(sq_mom))

    X = np.column_stack([s_trend, s_st, s_macd, s_rsi, s_vwap, s_vol, s_sq]).astype(float)
    return X, df.index, close.values


def forward_returns(close_values, horizon):
    """תשואה עתידית: close[t+h]/close[t]-1. NaN בסוף (אין עתיד)."""
    c = np.asarray(close_values, float)
    fwd = np.full(len(c), np.nan)
    fwd[:-horizon] = c[horizon:] / c[:-horizon] - 1
    return fwd


def _evaluate(score, fwd, q):
    """מחשב דיוק כיווני, כיסוי, ותשואה ממוצעת לאיתות, ברמת בררנות q."""
    valid = ~np.isnan(score) & ~np.isnan(fwd)
    if valid.sum() < 30:
        return None
    sc, fw = score[valid], fwd[valid]
    hi = np.quantile(sc, 1 - q)
    lo = np.quantile(sc, q)
    buy = sc >= hi
    sell = sc <= lo
    n_sig = int(buy.sum() + sell.sum())
    if n_sig == 0:
        return None
    correct = (buy & (fw > 0)).sum() + (sell & (fw < 0)).sum()
    acc = correct / n_sig * 100
    avg_buy = float(np.mean(fw[buy])) * 100 if buy.sum() else 0.0
    return dict(accuracy=acc, n_signals=n_sig, coverage=n_sig / len(sc) * 100,
                avg_buy_ret=avg_buy)


def optimize(datasets, horizon, n_iter=1500, fit_q=0.30, seed=42):
    """
    datasets: רשימת (X, close) לנכס אחד או כמה (איגום מפחית Overfitting).
    מכייל משקלים על 70% ראשונים (אימון), ומדווח על 30% אחרונים (מבחן, Out-of-Sample).
    מחזיר: best_weights + מדדים לכל 3 רמות הסיכון על תקופת המבחן.
    """
    rng = np.random.default_rng(seed)
    K = len(SUBSIGNAL_NAMES)

    # בניית מאגרי אימון/מבחן מאוגמים (חלוקה לפי זמן בכל נכס)
    Xtr, ftr, Xte, fte = [], [], [], []
    for X, close in datasets:
        fwd = forward_returns(close, horizon)
        n = len(X)
        cut = int(n * 0.7)
        Xtr.append(X[:cut]); ftr.append(fwd[:cut])
        Xte.append(X[cut:]); fte.append(fwd[cut:])
    Xtr = np.vstack(Xtr); ftr = np.concatenate(ftr)
    Xte = np.vstack(Xte); fte = np.concatenate(fte)

    # חיפוש אקראי של משקלים — ממקסם דיוק על האימון
    best_w, best_acc = None, -1
    for _ in range(n_iter):
        w = rng.random(K)               # משקלים אי-שליליים
        res = _evaluate(Xtr @ w, ftr, fit_q)
        if res and res['n_signals'] >= 20 and res['accuracy'] > best_acc:
            best_acc, best_w = res['accuracy'], w
    if best_w is None:
        best_w = np.ones(K)

    # הערכה על תקופת המבחן (Out-of-Sample) לכל רמת סיכון
    score_te = Xte @ best_w
    tiers = {}
    for name, q in PROFILES.items():
        tiers[name] = _evaluate(score_te, fte, q)

    return dict(weights=best_w, train_accuracy=best_acc, tiers=tiers,
                n_train=len(ftr), n_test=len(fte))


def run_full(datasets):
    """מריץ כיול לכל שילוב של אופק (5/21) — להשוואה."""
    out = {}
    for hname, h in HORIZONS.items():
        out[hname] = optimize(datasets, h)
    return out
