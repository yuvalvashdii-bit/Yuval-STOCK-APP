# -*- coding: utf-8 -*-
"""
alerts_bot.py — מנוע התראות רקע (רץ ב-GitHub Actions, לא באתר).
קורא watchlist.json, מריץ analyze על כל נכס, ושולח הודעת טלגרם על איתותים חשובים.

הרצה מקומית לבדיקה:
    set TELEGRAM_BOT_TOKEN=...   (Windows CMD)  /  $env:TELEGRAM_BOT_TOKEN="..." (PowerShell)
    set TELEGRAM_CHAT_ID=...
    python alerts_bot.py
"""

import json
import os

import requests

import config
import data
import engine

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        print("אין TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID — מדפיס במקום לשלוח:\n" + text)
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": text,
                                     "parse_mode": "HTML"}, timeout=20)
        print("Telegram:", r.status_code)
    except Exception as e:
        print("שגיאת שליחה:", e)


def load_watchlist():
    try:
        with open(os.path.join(os.path.dirname(__file__), "watchlist.json"),
                  encoding="utf-8") as f:
            return json.load(f).get("tickers", [])
    except Exception:
        return config.ALL_TICKERS[:8]


def main():
    tickers = load_watchlist()
    print(f"בודק {len(tickers)} נכסים...")
    alerts = []
    for t in tickers:
        df = data.fetch_one(t, mode="swing")
        res = engine.analyze(df, mode="swing")
        if not res:
            continue
        name = config.name_he(t)
        # התראה על ניקוד גבוה (קנייה חזקה)
        if res['score'] >= config.SCORE_STRONG_BUY:
            alerts.append(f"🟢 <b>{name} ({t})</b> — קנייה חזקה! ניקוד {res['score']:.0f}\n"
                          f"מחיר {res['price']:.2f} · כניסה {res['entry']:.2f} · "
                          f"סטופ {res['stop']:.2f} · יעד {res['target1']:.2f}")
        # התראה על חולשה / מכירה
        elif res['score'] <= config.SCORE_STRONG_SELL:
            alerts.append(f"🔴 <b>{name} ({t})</b> — חולשה! ניקוד {res['score']:.0f} · "
                          f"מחיר {res['price']:.2f}")
        # התראה על היפוך מגמה
        elif not res['st_up']:
            alerts.append(f"🟠 <b>{name} ({t})</b> — היפוך מגמה (Supertrend דובי) · "
                          f"מחיר {res['price']:.2f}")

    if alerts:
        header = "📊 <b>עדכון סורק המניות</b>\n\n"
        send_telegram(header + "\n\n".join(alerts))
    else:
        print("אין התראות כרגע.")


if __name__ == "__main__":
    main()
