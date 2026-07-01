# -*- coding: utf-8 -*-
"""
config.py — יקום הנכסים, שמות בעברית, וסיפים.
זה הקובץ שאתה עורך כדי להוסיף/להסיר מניות. פשוט מוסיפים טיקר לרשימה המתאימה.
"""

# ספי הניקוד לאיתותים (0-100). אפשר לכוונן.
SCORE_STRONG_BUY = 70
SCORE_BUY = 58
SCORE_SELL = 42
SCORE_STRONG_SELL = 30

# ברירות מחדל לניהול סיכון
DEFAULT_ACCOUNT = 100000      # גודל תיק לדוגמה
DEFAULT_RISK_PCT = 1.0        # % סיכון לעסקה
ATR_STOP_MULT = 2.0           # סטופ = כניסה - 2*ATR
ATR_TARGET1_MULT = 2.0
ATR_TARGET2_MULT = 3.5

# ------------------------------------------------------------------
# יקום הנכסים, מחולק לפי שוק
# ------------------------------------------------------------------
UNIVERSE = {
    "מניות ומדדי ארה\"ב": [
        "SPY", "QQQ", "DIA", "IWM",
        "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "NFLX",
        "AMD", "AVGO", "PLTR", "COIN", "JPM", "GS", "V", "QCOM", "CHKP", "NICE",
    ],
    "ישראל (בורסת ת\"א)": [
        "TA35.TA", "TA125.TA",
        "LUMI.TA", "POLI.TA", "MZTF.TA", "DSCT.TA", "TEVA.TA",
        "ESLT.TA", "NVMI.TA", "CAMT.TA", "PHOE.TA", "ICL.TA",
    ],
    "קריפטו": [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD",
        "XRP-USD", "DOGE-USD", "ADA-USD", "AVAX-USD",
    ],
    "סקטורים / ETF": [
        "XLK", "XLE", "XLF", "XLV", "SMH", "GLD", "SLV", "TLT", "ARKK",
    ],
}

# מדד הייחוס לכל שוק — לבדיקת "מגמת השוק הכללית" (Market Regime)
BENCHMARK = {
    "מניות ומדדי ארה\"ב": "SPY",
    "ישראל (בורסת ת\"א)": "TA125.TA",
    "קריפטו": "BTC-USD",
    "סקטורים / ETF": "SPY",
}

# שמות ידידותיים בעברית (מה שאין כאן — יוצג לפי הטיקר)
NAMES_HE = {
    "SPY": "S&P 500", "QQQ": "נאסד\"ק 100", "DIA": "דאו ג'ונס", "IWM": "ראסל 2000",
    "AAPL": "אפל", "MSFT": "מיקרוסופט", "NVDA": "אנבידיה", "TSLA": "טסלה",
    "AMZN": "אמזון", "META": "מטא", "GOOGL": "גוגל", "NFLX": "נטפליקס",
    "AMD": "AMD", "AVGO": "ברודקום", "PLTR": "פלנטיר", "COIN": "קוינבייס",
    "JPM": "ג'יי.פי מורגן", "GS": "גולדמן זאקס", "V": "ויזה", "QCOM": "קוואלקום",
    "CHKP": "צ'ק פוינט", "NICE": "נייס",
    "TA35.TA": "ת\"א 35", "TA125.TA": "ת\"א 125", "LUMI.TA": "בנק לאומי",
    "POLI.TA": "בנק הפועלים", "MZTF.TA": "מזרחי טפחות", "DSCT.TA": "בנק דיסקונט",
    "TEVA.TA": "טבע", "ESLT.TA": "אלביט מערכות", "NVMI.TA": "נובה",
    "CAMT.TA": "כמטק", "PHOE.TA": "הפניקס", "ICL.TA": "כיל",
    "BTC-USD": "ביטקוין", "ETH-USD": "את'ריום", "SOL-USD": "סולנה",
    "BNB-USD": "בייננס קוין", "XRP-USD": "ריפל", "DOGE-USD": "דוג'קוין",
    "ADA-USD": "קרדנו", "AVAX-USD": "אבלנצ'י",
    "XLK": "טכנולוגיה (ETF)", "XLE": "אנרגיה (ETF)", "XLF": "פיננסים (ETF)",
    "XLV": "בריאות (ETF)", "SMH": "מוליכים למחצה (ETF)", "GLD": "זהב (ETF)",
    "SLV": "כסף (ETF)", "TLT": "אג\"ח ארה\"ב (ETF)", "ARKK": "ARK חדשנות (ETF)",
}

ALL_TICKERS = [t for lst in UNIVERSE.values() for t in lst]

def market_of(ticker):
    for market, lst in UNIVERSE.items():
        if ticker in lst:
            return market
    return None

def name_he(ticker):
    return NAMES_HE.get(ticker, ticker)
