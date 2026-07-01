# -*- coding: utf-8 -*-
"""
engine.py — מנוע הניתוח: אינדיקטורים, ניקוד (analyze), ובק-טסט.
כל הלוגיקה ה"חכמה" נמצאת כאן, מופרדת מה-UI.
"""

import numpy as np
import pandas as pd

import config

# =============================================================================
# אינדיקטורים בסיסיים
# =============================================================================
def ema(s, span):
    return s.ewm(span=span, adjust=False).mean()

def rsi(close, length=14):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/length, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/length, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)

def true_range(df):
    hl = df['High'] - df['Low']
    hc = (df['High'] - df['Close'].shift()).abs()
    lc = (df['Low'] - df['Close'].shift()).abs()
    return pd.concat([hl, hc, lc], axis=1).max(axis=1)

def atr(df, length=14):
    return true_range(df).ewm(alpha=1/length, adjust=False).mean()

def macd_hist(close):
    line = ema(close, 12) - ema(close, 26)
    signal = ema(line, 9)
    return line - signal

def adx(df, length=14):
    """עוצמת מגמה (לא כיוון). מעל 25 = מגמה חזקה."""
    up = df['High'].diff()
    down = -df['Low'].diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = true_range(df)
    atr_ = tr.ewm(alpha=1/length, adjust=False).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).ewm(alpha=1/length, adjust=False).mean() / atr_
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(alpha=1/length, adjust=False).mean() / atr_
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1/length, adjust=False).mean().fillna(0)

def anchored_vwap(df):
    """VWAP מעוגן מתחילת התקופה (חלופה תקינה ל-VWAP המצטבר השבור של הגרסה הישנה)."""
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    return (tp * df['Volume']).cumsum() / df['Volume'].cumsum().replace(0, np.nan)

def supertrend(df, period=10, mult=3.0):
    """Supertrend מהיר (numpy). מחזיר סדרת True/False (שורי/דובי) + קו הסטופ."""
    hl2 = (df['High'] + df['Low']).values / 2
    atr_ = atr(df, period).values
    close = df['Close'].values
    n = len(df)
    upper = hl2 + mult * atr_
    lower = hl2 - mult * atr_
    f_up, f_lo = upper.copy(), lower.copy()
    trend = np.ones(n, dtype=bool)
    for i in range(1, n):
        f_up[i] = min(upper[i], f_up[i-1]) if close[i-1] <= f_up[i-1] else upper[i]
        f_lo[i] = max(lower[i], f_lo[i-1]) if close[i-1] >= f_lo[i-1] else lower[i]
        if close[i] > f_up[i-1]:
            trend[i] = True
        elif close[i] < f_lo[i-1]:
            trend[i] = False
        else:
            trend[i] = trend[i-1]
    line = np.where(trend, f_lo, f_up)
    return pd.Series(trend, index=df.index), pd.Series(line, index=df.index)

def ttm_squeeze(df, length=20):
    ma = df['Close'].rolling(length).mean()
    std = df['Close'].rolling(length).std()
    atr_ = atr(df, length)
    squeeze_on = ((ma - 2*std) > (ma - 1.5*atr_)) & ((ma + 2*std) < (ma + 1.5*atr_))
    momentum = df['Close'] - ma
    return squeeze_on, momentum

# =============================================================================
# חישוב סדרת הניקוד לכל ההיסטוריה (משמש גם לניתוח וגם לבק-טסט)
# =============================================================================
def _mode_params(mode):
    if mode == "intraday":
        return dict(rsi_len=9, atr_len=10, st_period=7, ema_fast=20, ema_slow=50)
    return dict(rsi_len=14, atr_len=14, st_period=10, ema_fast=50, ema_slow=200)

def compute_series(df, mode="swing"):
    """מחשב את כל האינדיקטורים ואת סדרת הניקוד לאורך כל ההיסטוריה."""
    p = _mode_params(mode)
    close = df['Close']
    out = pd.DataFrame(index=df.index)
    out['close'] = close
    out['ema_fast'] = ema(close, p['ema_fast'])
    out['ema_slow'] = ema(close, p['ema_slow'])
    out['rsi'] = rsi(close, p['rsi_len'])
    out['macd'] = macd_hist(close)
    out['adx'] = adx(df, p['atr_len'])
    out['atr'] = atr(df, p['atr_len'])
    st_trend, st_line = supertrend(df, p['st_period'])
    out['st_up'] = st_trend
    out['st_line'] = st_line
    sq_on, sq_mom = ttm_squeeze(df)
    out['sq_on'] = sq_on
    out['sq_mom'] = sq_mom
    out['vwap'] = anchored_vwap(df)
    out['vol_ratio'] = df['Volume'] / df['Volume'].rolling(20).mean()

    # --- רכיבי הניקוד (חיובי = שורי) ---
    trend = np.where(out['close'] > out['ema_fast'], 1, -1) + \
            np.where(out['ema_fast'] > out['ema_slow'], 1, -1)
    part_trend = trend / 2 * 22
    part_st = np.where(out['st_up'], 1, -1) * 20
    part_macd = np.sign(out['macd']) * 10 + np.where(out['macd'] > out['macd'].shift(), 1, -1) * 5
    rsi_score = (out['rsi'] - 50) / 50 * 12
    rsi_score = rsi_score - np.where(out['rsi'] > 78, 8, 0) + np.where(out['rsi'] < 25, 6, 0)
    part_rsi = rsi_score
    part_vwap = np.where(out['close'] > out['vwap'], 8, -8)
    part_vol = np.where(out['vol_ratio'] > 1.2, 6, np.where(out['vol_ratio'] < 0.7, -3, 0))
    part_sq = np.where(out['sq_on'], 0, np.where(out['sq_mom'] > 0, 8, -8))

    raw = part_trend + part_st + part_macd + part_rsi + part_vwap + part_vol + part_sq
    conf = np.clip(out['adx'] / 25, 0.5, 1.4)
    out['score'] = np.clip(50 + raw * conf * 0.55, 0, 100)

    # שמירת התרומות האחרונות (לעיגולים)
    out.attrs['parts_last'] = {
        'מגמה (EMA)': float(pd.Series(part_trend, index=out.index).iloc[-1]),
        'Supertrend': float(pd.Series(part_st, index=out.index).iloc[-1]),
        'MACD': float(pd.Series(part_macd, index=out.index).iloc[-1]),
        'RSI': float(pd.Series(part_rsi, index=out.index).iloc[-1]),
        'VWAP': float(pd.Series(part_vwap, index=out.index).iloc[-1]),
        'נפח': float(pd.Series(part_vol, index=out.index).iloc[-1]),
        'Squeeze': float(pd.Series(part_sq, index=out.index).iloc[-1]),
    }
    return out

def signal_from_score(score):
    if score >= config.SCORE_STRONG_BUY: return "קנייה חזקה", "circle-bullish"
    if score >= config.SCORE_BUY:        return "קנייה", "circle-bullish"
    if score <= config.SCORE_STRONG_SELL:return "מכירה חזקה", "circle-bearish"
    if score <= config.SCORE_SELL:       return "מכירה", "circle-bearish"
    return "ניטרלי / המתנה", "circle-neutral"

# =============================================================================
# analyze — צילום מצב נוכחי + רמות מסחר
# =============================================================================
def analyze(df, mode="swing", regime_bullish=None):
    """מקבל DataFrame OHLCV ומחזיר dict עם ניקוד, איתות ורמות מסחר. None אם אין דאטה."""
    if df is None or len(df) < 60:
        return None
    df = df.dropna().copy()
    s = compute_series(df, mode)
    last = s.iloc[-1]
    price = float(last['close'])
    a = float(last['atr'])
    score = float(last['score'])

    # Market regime — הורדת ניקוד ללונג נגד שוק יורד
    regime_note = ""
    if regime_bullish is False and score > 50:
        score = 50 + (score - 50) * 0.6
        regime_note = "⚠️ רוח נגדית: מגמת השוק הכללית שלילית"
    elif regime_bullish is True:
        regime_note = "✅ רוח גבית: השוק הכללי חיובי"

    signal, sig_style = signal_from_score(score)
    bullish = score >= 50

    stop_atr = price - config.ATR_STOP_MULT * a
    st_line = float(last['st_line'])
    trail = st_line if (bool(last['st_up']) and st_line < price) else stop_atr
    stop = max(stop_atr, trail) if bullish else stop_atr
    target1 = price + config.ATR_TARGET1_MULT * a
    target2 = price + config.ATR_TARGET2_MULT * a
    risk = price - stop
    # יחס סיכוי-סיכון מחושב ליעד הסופי (target2) — משקף את פוטנציאל העסקה המלא
    rr = (target2 - price) / risk if risk > 0 else 0.0

    prev_close = float(df['Close'].iloc[-2])
    return {
        'price': price, 'change_pct': (price / prev_close - 1) * 100,
        'score': score, 'signal': signal, 'sig_style': sig_style, 'bullish': bullish,
        'rsi': float(last['rsi']), 'adx': float(last['adx']), 'atr': a,
        'st_up': bool(last['st_up']), 'st_line': st_line,
        'vol_ratio': float(last['vol_ratio']) if not np.isnan(last['vol_ratio']) else 1.0,
        'sq_on': bool(last['sq_on']),
        'entry': price, 'stop': stop, 'target1': target1, 'target2': target2, 'rr': rr,
        'regime_note': regime_note, 'parts': s.attrs['parts_last'],
        'series': s, 'df': df,
    }

def is_regime_bullish(bench_df, mode="swing"):
    """האם מדד הייחוס מעל ה-EMA200 (שוק שורי)."""
    if bench_df is None or len(bench_df) < 60:
        return None
    close = bench_df['Close'].dropna()
    span = 200 if mode == "swing" else 50
    return bool(close.iloc[-1] > ema(close, min(span, len(close)-1)).iloc[-1])

# =============================================================================
# backtest — סימולציית עסקאות היסטורית
# =============================================================================
def backtest(df, mode="swing", entry_score=None, exit_score=None, fee_pct=0.0):
    """מדמה אסטרטגיית לונג על ההיסטוריה. מחזיר סטטיסטיקות + עקומת הון + עסקאות."""
    if df is None or len(df) < 120:
        return None
    entry_score = entry_score if entry_score is not None else config.SCORE_BUY
    exit_score = exit_score if exit_score is not None else config.SCORE_SELL
    df = df.dropna().copy()
    s = compute_series(df, mode)

    score = s['score'].values
    st_up = s['st_up'].values
    st_line = s['st_line'].values
    atr_v = s['atr'].values
    op = df['Open'].values
    close = df['Close'].values
    idx = df.index

    in_pos = False
    entry_price = 0.0
    stop = 0.0
    trades = []
    equity = [1.0]
    eq = 1.0

    for i in range(1, len(df)):
        # ניהול פוזיציה פתוחה (בדיקה על בר i)
        if in_pos:
            ret_bar = close[i] / close[i-1] - 1
            eq *= (1 + ret_bar)
            exit_now, reason = False, ""
            if df['Low'].values[i] <= stop:
                exit_now, reason, exit_price = True, "סטופ", stop
            elif not st_up[i]:
                exit_now, reason, exit_price = True, "היפוך Supertrend", close[i]
            elif score[i] < exit_score:
                exit_now, reason, exit_price = True, "ניקוד נחלש", close[i]
            if exit_now:
                pnl = (exit_price / entry_price - 1) - 2 * fee_pct / 100
                trades.append({'entry_date': entry_date, 'exit_date': idx[i],
                               'entry': entry_price, 'exit': exit_price,
                               'pnl_pct': pnl * 100, 'reason': reason})
                in_pos = False
        else:
            # כניסה: איתות בבר i-1, ביצוע בפתיחת בר i (בלי lookahead)
            if score[i-1] >= entry_score and st_up[i-1]:
                in_pos = True
                entry_price = op[i]
                entry_date = idx[i]
                stop = entry_price - config.ATR_STOP_MULT * atr_v[i-1]
        equity.append(eq)

    tr = pd.DataFrame(trades)
    bh_return = (close[-1] / close[0] - 1) * 100
    eq_series = pd.Series(equity, index=idx[:len(equity)])
    dd = (eq_series / eq_series.cummax() - 1).min() * 100

    if len(tr) == 0:
        stats = dict(trades=0, win_rate=0, avg_win=0, avg_loss=0, profit_factor=0,
                     strat_return=(eq-1)*100, bh_return=bh_return, max_dd=dd)
    else:
        wins = tr[tr['pnl_pct'] > 0]['pnl_pct']
        losses = tr[tr['pnl_pct'] <= 0]['pnl_pct']
        gross_win = wins.sum()
        gross_loss = abs(losses.sum())
        stats = dict(
            trades=len(tr),
            win_rate=len(wins) / len(tr) * 100,
            avg_win=wins.mean() if len(wins) else 0,
            avg_loss=losses.mean() if len(losses) else 0,
            profit_factor=(gross_win / gross_loss) if gross_loss > 0 else float('inf'),
            strat_return=(eq - 1) * 100,
            bh_return=bh_return,
            max_dd=dd,
        )
    return {'stats': stats, 'equity': eq_series, 'trades': tr}
