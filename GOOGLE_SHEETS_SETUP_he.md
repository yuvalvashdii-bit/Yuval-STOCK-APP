# ☁️ חיבור Google Sheets לשמירה קבועה של התיק

בלי זה — התיק נשמר, אך עלול להתאפס בכל עדכון קוד. עם זה — התיק **נשמר לתמיד**,
גם אחרי עדכונים, וגם נגיש לך ישירות בגוגל שיטס. הגדרה חד-פעמית (~10 דקות).

## שלב 1: צור Google Sheet
1. היכנס ל-https://sheets.google.com וצור גיליון חדש (שם לבחירתך, למשל "התיק שלי").
2. מתוך הכתובת בדפדפן העתק את **מזהה הגיליון** — החלק שבין `/d/` ל-`/edit`:
   `https://docs.google.com/spreadsheets/d/`**`1AbCdEf... זה המזהה`**`/edit`

## שלב 2: צור חשבון שירות (Service Account) ב-Google Cloud
1. היכנס ל-https://console.cloud.google.com → למעלה צור **New Project** (שם: stock-app).
2. בתפריט חיפוש חפש **Google Sheets API** → **Enable**.
3. בתפריט חפש **Service Accounts** → **Create Service Account** → תן שם → **Done**.
4. לחץ על חשבון השירות שנוצר → לשונית **Keys** → **Add Key → Create new key → JSON** →
   יורד קובץ `.json` למחשב. **שמור אותו — הוא הסיסמה.**
5. פתח את קובץ ה-JSON, ומצא בתוכו את השורה `"client_email": "...@...iam.gserviceaccount.com"`.
   **העתק את כתובת המייל הזו.**

## שלב 3: שתף את הגיליון עם חשבון השירות
1. חזור ל-Google Sheet שלך → לחץ **Share** (שתף).
2. הדבק את כתובת המייל של חשבון השירות (מהשלב הקודם), תן הרשאת **Editor** → **Send**.

## שלב 4: הכנס את הסודות ל-Streamlit
1. באתר Streamlit שלך (share.streamlit.io) → ליד האפליקציה לחץ על ⋮ → **Settings** → **Secrets**.
2. הדבק את הבלוק הבא, כשאתה **ממלא את הערכים מתוך קובץ ה-JSON** שהורדת:

```toml
gsheet_key = "כאן-להדביק-את-מזהה-הגיליון-משלב-1"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

> כל הערכים (`project_id`, `private_key`, `client_email` וכו') נמצאים בקובץ ה-JSON שהורדת —
> פשוט העתק כל ערך למקום המתאים. את ה-`private_key` העתק **כמו שהוא**, כולל ה-`\n`.

3. לחץ **Save**. האפליקציה תעשה Reboot.

## שלב 5: בדיקה
היכנס למסך **"💼 התיק שלי"**. למעלה צריך להופיע:
> ☁️ Google Sheets — שמירה קבועה (לא מתאפסת)

אם מופיע "💾 שמירה מקומית" — משהו בסודות לא תקין (בדוק שהמייל שותף לגיליון ושהמזהה נכון).

מעכשיו כל מניה שתוסיף נשמרת בגיליון Google שלך אוטומטית. 🎉
