# -*- coding: utf-8 -*-
"""
app.py — הממשק הראשי (Streamlit). 6 טאבים:
סורק שוק · ניתוח נכס · בק-טסט · התיק שלי · מחשבון סיכון · התראות.

הרצה מקומית:  streamlit run app.py
"""

import io

import numpy as np
import pandas as pd
import streamlit as st

import config
import data as datamod
import engine
import optimizer
import portfolio as pf

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False

# =============================================================================
# הגדרות עמוד + עיצוב RTL
# =============================================================================
st.set_page_config(page_title="סורק מניות ומדדים", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700&display=swap');
html, body, [data-testid="stSidebar"], .stApp { font-family:'Assistant',sans-serif; direction:rtl; text-align:right; }
[data-testid="stDataFrame"], [data-testid="stTable"] { direction:ltr; }
.stTabs [data-baseweb="tab-list"] { direction:rtl; }
.circles-wrapper { display:flex; flex-wrap:wrap; justify-content:center; gap:18px; margin:16px 0; }
.metric-circle { width:120px; height:120px; border-radius:50%; display:flex; flex-direction:column;
    justify-content:center; align-items:center; text-align:center; box-shadow:0 6px 14px rgba(0,0,0,.18); }
.circle-label { font-size:.74rem; font-weight:600; margin-bottom:3px; }
.circle-value { font-size:1.1rem; font-weight:700; }
.circle-status { font-size:.66rem; opacity:.9; padding:0 5px; }
.circle-bullish { background:radial-gradient(circle,#22c55e,#15803d); color:#fff; border:4px solid #4ade80; }
.circle-bearish { background:radial-gradient(circle,#ef4444,#b91c1c); color:#fff; border:4px solid #f87171; }
.circle-neutral { background:radial-gradient(circle,#6b7280,#374151); color:#fff; border:4px solid #9ca3af; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# עטיפות cache סביב שליפת הנתונים
# =============================================================================
@st.cache_data(ttl=900, show_spinner=False)
def get_one(symbol, mode):
    return datamod.fetch_one(symbol, mode)

@st.cache_data(ttl=900, show_spinner=False)
def get_batch(symbols, mode):
    return datamod.fetch_batch(list(symbols), mode)

@st.cache_data(ttl=900, show_spinner=False)
def get_regime(market, mode):
    bench = config.BENCHMARK.get(market)
    return engine.is_regime_bullish(datamod.fetch_one(bench, mode), mode) if bench else None

# =============================================================================
# כותרת + אזהרות
# =============================================================================
st.markdown("""
<div style="background:linear-gradient(135deg,#0f172a,#1e293b); padding:20px; border-radius:12px;
     margin-bottom:14px; text-align:center; border:1px solid #334155;">
  <h1 style="margin:0; color:#f8fafc; font-size:1.9rem;">📈 סורק מניות ומדדים — טווח קצר</h1>
  <p style="margin:6px 0 0; color:#94a3b8;">ניקוד טכני · דירוג הזדמנויות · רמות כניסה/יציאה · בק-טסט · ארה"ב · ישראל · קריפטו</p>
</div>
""", unsafe_allow_html=True)

st.warning("⚠️ **כלי עזר לניתוח טכני — לא ייעוץ השקעות.** הנתונים מושהים (~15 דק') "
           "ואינדיקטורים אינם מנבאים את העתיד. השתמש תמיד בסטופ-לוס. האחריות עליך בלבד.")

# בקרות עליונות
top1, top2 = st.columns([1, 3])
with top1:
    mode = st.radio("מצב מסחר:", ["swing", "intraday"],
                    format_func=lambda m: "סווינג (יומי)" if m == "swing" else "תוך-יומי (15 דק')",
                    horizontal=True)

tabs = st.tabs(["🔎 סורק שוק", "🔬 ניתוח נכס", "📊 בק-טסט",
                "💼 התיק שלי", "🧮 מחשבון סיכון", "🔔 התראות", "🧪 כיול חכם"])

# =============================================================================
# טאב 1 — סורק שוק (השורה התחתונה)
# =============================================================================
with tabs[0]:
    st.subheader("🏆 השורה התחתונה — דירוג ההזדמנויות")
    c1, c2 = st.columns([3, 1])
    with c1:
        markets = st.multiselect("שווקים לסריקה:", list(config.UNIVERSE.keys()),
                                 default=[list(config.UNIVERSE.keys())[0]])
    with c2:
        only_buys = st.checkbox("רק איתותי קנייה", value=False)

    symbols = tuple(t for m in markets for t in config.UNIVERSE[m])
    run_scan = st.button("🔎 הרץ סריקה", type="primary", use_container_width=True)

    if not symbols:
        st.info("בחר לפחות שוק אחד ולחץ 'הרץ סריקה'.")
    elif run_scan:
        with st.spinner(f"סורק {len(symbols)} נכסים... (עשוי לקחת עד דקה)"):
            batch = get_batch(symbols, mode)
            regimes = {m: get_regime(m, mode) for m in markets}
            rows = []
            for s in symbols:
                mkt = config.market_of(s)
                res = engine.analyze(batch.get(s), mode, regime_bullish=regimes.get(mkt))
                if not res:
                    continue
                rows.append({
                    "טיקר": s, "שם": config.name_he(s),
                    "מחיר": round(res['price'], 2), "שינוי%": round(res['change_pct'], 2),
                    "ניקוד": round(res['score'], 1), "איתות": res['signal'],
                    "RSI": round(res['rsi']), "ADX": round(res['adx']),
                    "כניסה": round(res['entry'], 2), "סטופ": round(res['stop'], 2),
                    "יעד1": round(res['target1'], 2), "יעד2": round(res['target2'], 2),
                    "R:R": round(res['rr'], 2),
                })
        if not rows:
            st.error("לא התקבלו נתונים. yfinance חוסם זמנית — נסה שוב בעוד דקה, "
                     "או בחר פחות שווקים בבת אחת.")
            st.session_state.pop("scan_table", None)
        else:
            st.session_state.scan_table = pd.DataFrame(rows)

    if "scan_table" in st.session_state:
        table = st.session_state.scan_table.sort_values("ניקוד", ascending=False).reset_index(drop=True)
        if only_buys:
            table = table[table["איתות"].str.contains("קנייה")]
        top = table.head(20)

        def c_sig(v):
            if "קנייה" in str(v): return "background-color:#14532d;color:#fff"
            if "מכירה" in str(v): return "background-color:#7f1d1d;color:#fff"
            return "background-color:#374151;color:#fff"

        def c_score(v):
            g = int(np.clip(v, 0, 100))
            return f"background-color:rgba({255-int(g*2.55)},{int(g*2.55)},80,.35)"

        styled = (top.style
                  .map(c_sig, subset=["איתות"])
                  .map(c_score, subset=["ניקוד"])
                  .format({"מחיר": "{:.2f}", "שינוי%": "{:+.2f}", "כניסה": "{:.2f}",
                           "סטופ": "{:.2f}", "יעד1": "{:.2f}", "יעד2": "{:.2f}", "R:R": "{:.2f}"}))
        st.dataframe(styled, use_container_width=True, height=730)

        csv = table.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ הורד טבלה מלאה (CSV)", csv, "screener.csv", "text/csv")
        st.caption("ניקוד 70+ = שורי חזק · מתחת ל-30 = דובי · 50 = ניטרלי. "
                   "**R:R** מעל 1.5 עדיף. הסטופ הוא נקודת היציאה אם התזה נכשלת.")
    elif not run_scan:
        st.info("👆 בחר שווקים ולחץ **הרץ סריקה** כדי לקבל את הדירוג.")

# =============================================================================
# טאב 2 — ניתוח נכס בודד
# =============================================================================
with tabs[1]:
    sym = st.selectbox("בחר נכס:", config.ALL_TICKERS,
                       index=config.ALL_TICKERS.index("NVDA"),
                       format_func=lambda t: f"{t} — {config.name_he(t)}")
    mkt = config.market_of(sym)
    analyze_now = st.button("🔬 נתח נכס", type="primary", use_container_width=True)

    res = None
    if analyze_now:
        with st.spinner(f"מנתח את {config.name_he(sym)}..."):
            res = engine.analyze(get_one(sym, mode), mode, regime_bullish=get_regime(mkt, mode))
        if res is None:
            st.error("אין מספיק נתונים לנכס זה (yfinance עלול לחסום זמנית — נסה שוב).")

    if res is None:
        if not analyze_now:
            st.info("👆 בחר נכס ולחץ **נתח נכס**.")
    else:
        col = "#10b981" if res['bullish'] else "#ef4444"
        st.markdown(f"""
        <div style="background:#1e293b; border-right:6px solid {col}; padding:16px; border-radius:8px;
             border:1px solid #334155; margin-bottom:14px;">
          <h2 style="margin:0; color:#f8fafc;">{sym} — {config.name_he(sym)}</h2>
          <div style="display:flex; gap:30px; margin-top:10px; flex-wrap:wrap; color:#cbd5e1; font-size:1.05rem;">
            <span><b>מחיר:</b> {res['price']:.2f}</span>
            <span style="color:{'#10b981' if res['change_pct']>=0 else '#ef4444'};"><b>שינוי:</b> {res['change_pct']:+.2f}%</span>
            <span style="color:{col}; font-weight:700; background:#0f172a; padding:2px 10px; border-radius:4px;">
              ניקוד {res['score']:.0f}/100 · {res['signal']}</span>
          </div>
          <div style="margin-top:8px; color:#fbbf24;">{res['regime_note']}</div>
        </div>
        """, unsafe_allow_html=True)

        def circle(label, val, extra=""):
            cls = "circle-bullish" if val > 1 else ("circle-bearish" if val < -1 else "circle-neutral")
            return (f'<div class="metric-circle {cls}"><div class="circle-label">{label}</div>'
                    f'<div class="circle-value">{val:+.0f}</div>'
                    f'<div class="circle-status">{extra}</div></div>')

        p = res['parts']
        circles = (
            circle("מגמה EMA", p['מגמה (EMA)'], "ממוצעים נעים") +
            circle("Supertrend", p['Supertrend'], "שורי" if res['st_up'] else "דובי") +
            circle("MACD", p['MACD'], "מומנטום") +
            circle("RSI", p['RSI'], f"RSI {res['rsi']:.0f}") +
            circle("VWAP", p['VWAP'], "קו מוסדי") +
            circle("נפח", p['נפח'], f"x{res['vol_ratio']:.1f}") +
            circle("Squeeze", p['Squeeze'], "סחיטה" if res['sq_on'] else "פרוץ"))
        st.markdown("<h4 style='color:#f1f5f9;'>תרומת כל פרמטר לניקוד:</h4>", unsafe_allow_html=True)
        st.markdown(f'<div class="circles-wrapper">{circles}</div>', unsafe_allow_html=True)

        st.markdown("<h4 style='color:#f1f5f9;'>🎯 תוכנית מסחר (לונג):</h4>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("כניסה", f"{res['entry']:.2f}")
        m2.metric("סטופ-לוס", f"{res['stop']:.2f}", f"{(res['stop']/res['price']-1)*100:.1f}%")
        m3.metric("יעד ראשון", f"{res['target1']:.2f}", f"+{(res['target1']/res['price']-1)*100:.1f}%")
        m4.metric("R:R", f"{res['rr']:.2f}")

        st.info(f"""**מתי למכור / לצאת מ-{config.name_he(sym)}:**
- 🛑 **סטופ:** סגירה מתחת ל-**{res['stop']:.2f}** → צא מיד (התזה נכשלה).
- 📉 **היפוך:** אם ה-Supertrend מתהפך לדובי (מחיר מתחת ל-{res['st_line']:.2f}).
- 🎯 **מימוש:** מכור חצי ביעד 1 ({res['target1']:.2f}), הזז סטופ לנקודת הכניסה, החזק את השאר ליעד 2 ({res['target2']:.2f}).
- ⚠️ **קניית יתר:** RSI מעל 78 + MACD יורד = שקול מימוש חלקי.""")

        if HAS_PLOTLY:
            s = res['series'].tail(140)
            df = res['df'].tail(140)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28],
                                vertical_spacing=0.04)
            fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'],
                          low=df['Low'], close=df['Close'], name="מחיר"), 1, 1)
            fig.add_trace(go.Scatter(x=s.index, y=s['ema_fast'], line=dict(color="#38bdf8", width=1),
                          name="EMA מהיר"), 1, 1)
            fig.add_trace(go.Scatter(x=s.index, y=s['st_line'], line=dict(color="#f59e0b", width=1, dash="dot"),
                          name="Supertrend"), 1, 1)
            for y, cc in [(res['entry'], "#e5e7eb"), (res['stop'], "#ef4444"), (res['target1'], "#22c55e")]:
                fig.add_hline(y=y, line=dict(color=cc, width=1, dash="dash"), row=1, col=1)
            fig.add_trace(go.Scatter(x=s.index, y=s['rsi'], line=dict(color="#a78bfa", width=1.2),
                          name="RSI"), 2, 1)
            fig.add_hline(y=70, line=dict(color="#ef4444", width=.7, dash="dot"), row=2, col=1)
            fig.add_hline(y=30, line=dict(color="#22c55e", width=.7, dash="dot"), row=2, col=1)
            fig.update_layout(template="plotly_dark", height=540, margin=dict(l=10, r=10, t=30, b=10),
                              xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# טאב 3 — בק-טסט
# =============================================================================
with tabs[2]:
    st.subheader("📊 בק-טסט — כמה האסטרטגיה 'עבדה' בעבר")
    b1, b2, b3 = st.columns([2, 1, 1])
    with b1:
        bt_sym = st.selectbox("נכס לבדיקה:", config.ALL_TICKERS,
                              index=config.ALL_TICKERS.index("AAPL"),
                              format_func=lambda t: f"{t} — {config.name_he(t)}", key="bt_sym")
    with b2:
        entry_th = st.slider("סף כניסה", 50, 80, config.SCORE_BUY)
    with b3:
        fee = st.number_input("עמלה % לעסקה", 0.0, 1.0, 0.0, 0.05)

    if st.button("הרץ בק-טסט", type="primary"):
        with st.spinner("מריץ סימולציה על ההיסטוריה..."):
            bt = engine.backtest(get_one(bt_sym, "swing"), "swing",
                                 entry_score=entry_th, fee_pct=fee)
        if not bt:
            st.error("אין מספיק היסטוריה לבק-טסט.")
        else:
            s = bt['stats']
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("מס' עסקאות", s['trades'])
            k2.metric("אחוז הצלחה", f"{s['win_rate']:.0f}%")
            pf_txt = "∞" if s['profit_factor'] == float('inf') else f"{s['profit_factor']:.2f}"
            k3.metric("Profit Factor", pf_txt)
            k4.metric("Max Drawdown", f"{s['max_dd']:.1f}%")
            k5, k6, k7 = st.columns(3)
            k5.metric("תשואת האסטרטגיה", f"{s['strat_return']:+.1f}%")
            k6.metric("קנה-והחזק (Buy&Hold)", f"{s['bh_return']:+.1f}%")
            k7.metric("רווח/הפסד ממוצע", f"{s['avg_win']:.1f}% / {s['avg_loss']:.1f}%")

            if HAS_PLOTLY and len(bt['equity']) > 1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=bt['equity'].index, y=(bt['equity']-1)*100,
                              line=dict(color="#22c55e"), name="אסטרטגיה"))
                fig.update_layout(template="plotly_dark", height=340, title="עקומת הון (%)",
                                  margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig, use_container_width=True)

            if len(bt['trades']):
                st.markdown("**עסקאות אחרונות:**")
                st.dataframe(bt['trades'].tail(15), use_container_width=True)
            st.caption("⚠️ הבק-טסט הוא in-sample (על אותם נתונים) ואינו כולל החלקה. "
                       "עבר אינו מבטיח עתיד — זו בדיקת שפיות, לא הבטחה.")

# =============================================================================
# טאב 4 — התיק שלי
# =============================================================================
with tabs[3]:
    st.subheader("💼 מעקב תיק — רווח/הפסד ומתי למכור")
    if "holdings" not in st.session_state:
        st.session_state.holdings = []

    with st.form("add_pos", clear_on_submit=True):
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            h_sym = st.selectbox("נכס", config.ALL_TICKERS,
                                 format_func=lambda t: f"{t} — {config.name_he(t)}")
        with f2:
            h_price = st.number_input("מחיר קנייה", min_value=0.0, value=100.0, step=0.5)
        with f3:
            h_qty = st.number_input("כמות", min_value=0.0, value=10.0, step=1.0)
        with f4:
            st.write(" ")
            add = st.form_submit_button("➕ הוסף", use_container_width=True)
        if add:
            st.session_state.holdings.append({"ticker": h_sym, "entry_price": h_price, "qty": h_qty})

    up = st.file_uploader("או טען תיק מקובץ CSV (עמודות: ticker, entry_price, qty)", type="csv")
    if up is not None:
        try:
            imp = pd.read_csv(up)
            st.session_state.holdings = imp[["ticker", "entry_price", "qty"]].to_dict("records")
            st.success(f"נטענו {len(st.session_state.holdings)} פוזיציות.")
        except Exception:
            st.error("קובץ לא תקין — ודא עמודות ticker, entry_price, qty.")

    if not st.session_state.holdings:
        st.info("הוסף פוזיציה למעלה כדי לראות מעקב חי.")
    else:
        rows, total = [], 0.0
        for h in st.session_state.holdings:
            res = engine.analyze(get_one(h["ticker"], mode), mode)
            if not res:
                continue
            ev = pf.evaluate_holding(h, res)
            total += ev["pnl_abs"]
            rows.append({
                "טיקר": h["ticker"], "שם": config.name_he(h["ticker"]),
                "קנייה": h["entry_price"], "כמות": h["qty"], "מחיר נוכחי": ev["price"],
                "רווח/הפסד": ev["pnl_abs"], "%": ev["pnl_pct"], "ניקוד": ev["score"],
                "איתות": ev["signal"], "סטופ": ev["stop"],
                "למכור?": ("🔴 " + ev["reason"]) if ev["sell"] else (ev["reason"] or "החזק"),
            })
        pdf = pd.DataFrame(rows)
        st.metric("רווח/הפסד כולל בתיק", f"{total:+,.2f}")
        st.dataframe(pdf, use_container_width=True, height=360)
        st.download_button("⬇️ שמור תיק (CSV)",
                           pd.DataFrame(st.session_state.holdings).to_csv(index=False).encode("utf-8-sig"),
                           "my_portfolio.csv", "text/csv")
        if st.button("🗑️ נקה תיק"):
            st.session_state.holdings = []
            st.rerun()

# =============================================================================
# טאב 5 — מחשבון סיכון
# =============================================================================
with tabs[4]:
    st.subheader("🧮 מחשבון גודל פוזיציה")
    st.write("כמה מניות לקנות כדי לא לסכן יותר מאחוז מסוים מהתיק בעסקה בודדת.")
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        acc = st.number_input("גודל תיק (₪/$)", min_value=0.0, value=float(config.DEFAULT_ACCOUNT), step=1000.0)
    with r2:
        risk = st.number_input("% סיכון לעסקה", min_value=0.1, max_value=10.0,
                               value=config.DEFAULT_RISK_PCT, step=0.25)
    with r3:
        entry = st.number_input("מחיר כניסה", min_value=0.0, value=100.0, step=0.5)
    with r4:
        stop = st.number_input("מחיר סטופ", min_value=0.0, value=95.0, step=0.5)

    calc = pf.position_size(acc, risk, entry, stop)
    if calc["shares"] <= 0:
        st.error("הסטופ חייב להיות מתחת למחיר הכניסה.")
    else:
        o1, o2, o3 = st.columns(3)
        o1.metric("כמות לקנייה", f"{calc['shares']:,} יח'")
        o2.metric("סכום בסיכון", f"{calc['dollar_risk']:,.0f}")
        o3.metric("שווי הפוזיציה", f"{calc['position_value']:,.0f}")
        st.caption(f"אתה מסכן {risk}% מהתיק ({calc['dollar_risk']:,.0f}) — הסיכון למניה הוא "
                   f"{calc['risk_per_share']:.2f}. אם הסטופ נפגע, זה ההפסד המקסימלי המתוכנן.")

# =============================================================================
# טאב 6 — התראות
# =============================================================================
with tabs[5]:
    st.subheader("🔔 התראות אוטומטיות (טלגרם)")
    st.markdown("""
מנוע ההתראות **רץ ברקע גם כשהאתר סגור** (דרך GitHub Actions), ושולח לך הודעת טלגרם
כשמניה עוברת ניקוד גבוה, שוברת סטופ, או מתהפכת. ההגדרה חד-פעמית:

1. **צור בוט טלגרם:** פתח שיחה עם **@BotFather**, שלח `/newbot`, קבל **TOKEN**.
2. **קבל Chat ID:** פתח שיחה עם **@userinfobot** — הוא יראה לך את המספר שלך.
3. ב-GitHub, בתוך ה-repo: **Settings → Secrets and variables → Actions → New secret**,
   הוסף שניים: `TELEGRAM_BOT_TOKEN` ו-`TELEGRAM_CHAT_ID`.
4. ב-**Actions** אפשר ללחוץ **Run workflow** לבדיקה מיידית.

**איזה מניות במעקב?** ערוך את הקובץ `watchlist.json` ב-repo (רשימת הטיקרים).
""")
    st.code('{ "tickers": ["NVDA", "AAPL", "TSLA", "TA125.TA", "BTC-USD", "SMH"] }', language="json")
    st.info("התזמון בקובץ `.github/workflows/alerts.yml` — ברירת מחדל: כל 30 דק' בשעות מסחר ארה\"ב.")

# =============================================================================
# טאב 7 — כיול חכם (Optimizer): איזה שילוב מנבא הכי טוב, ומה הדיוק האמיתי
# =============================================================================
with tabs[6]:
    st.subheader("🧪 כיול חכם — כמה באמת אפשר לנבא?")
    st.markdown("""
המנוע לומד מההיסטוריה את **המשקלים הטובים ביותר** לאינדיקטורים, ובודק את הדיוק על
**תקופה שהוא לא ראה באימון** (Out-of-Sample) — כדי שהמספר יהיה אמיתי ולא "מיופה".
נבדקות 3 רמות סיכון ו-2 אופקי זמן.
""")
    st.warning("💡 **חשוב:** דיוק ריאלי הוא ~50%-60%. אם תראה 'דיוק אימון' גבוה אבל "
               "'דיוק מבחן' נמוך — זה בדיוק ה-Overfitting שמפילים סוחרים. המספר הקובע הוא **דיוק המבחן**.")

    ca, cb = st.columns([3, 1])
    with ca:
        cal_market = st.selectbox("על איזה סל לכייל? (איגום כמה מניות = תוצאה אמינה יותר)",
                                  list(config.UNIVERSE.keys()))
    with cb:
        max_assets = st.slider("כמה מניות מהסל", 3, 12, 6)

    if st.button("🧪 הרץ כיול היסטורי", type="primary", use_container_width=True):
        syms = config.UNIVERSE[cal_market][:max_assets]
        with st.spinner(f"מכייל על {len(syms)} נכסים... (עשוי לקחת עד דקה-שתיים)"):
            batch = get_batch(tuple(syms), "swing")
            datasets = []
            used = []
            for s in syms:
                df = batch.get(s)
                if df is not None and len(df) > 250:
                    X, _, cv = optimizer.subsignal_matrix(df)
                    datasets.append((X, cv)); used.append(s)
            if not datasets:
                st.error("לא התקבלו מספיק נתונים — נסה שוב או בחר סל אחר.")
            else:
                st.session_state.cal_result = optimizer.run_full(datasets)
                st.session_state.cal_used = used

    if "cal_result" in st.session_state:
        st.caption(f"כויל על: {', '.join(config.name_he(s) for s in st.session_state.cal_used)}")
        for hname, r in st.session_state.cal_result.items():
            st.markdown(f"### ⏱️ אופק: {hname}")
            st.caption(f"דיוק אימון (מיופה, לא אמין): {r['train_accuracy']:.1f}% · "
                       f"שורות מבחן: {r['n_test']}")
            rows = []
            for tier, t in r['tiers'].items():
                if t:
                    rows.append({"רמת סיכון": tier, "דיוק מבחן (אמיתי)": f"{t['accuracy']:.1f}%",
                                 "מס' איתותים": t['n_signals'], "כיסוי": f"{t['coverage']:.0f}%",
                                 "תשואה ממוצעת לקנייה": f"{t['avg_buy_ret']:+.2f}%"})
            if rows:
                st.table(pd.DataFrame(rows))
        st.info("**איך להשתמש:** בחר את רמת הסיכון שמתאימה לך. השמרנית נותנת פחות איתותים "
                "אך בדיוק הגבוה ביותר — במסך הסורק זה מתורגם ל'פעל רק כשהניקוד קיצוני' (70+ לקנייה, 30- למכירה).")
        st.caption("⚠️ תוצאות משתנות בין סלים ותקופות. זו הערכה כנה, לא הבטחה. "
                   "אין אסטרטגיה טכנית שמנבאת ב-90%.")
