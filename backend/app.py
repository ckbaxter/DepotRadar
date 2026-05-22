import json
import re
import logging
import os
from datetime import datetime
from urllib.parse import quote as urlquote

import pytz
import yaml
import requests
import apprise as apprise_lib
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request
from flask_cors import CORS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

DATA_DIR      = "/data"
CONFIG_FILE   = "/config/ath-tracker.yml"
STOCKS_FILE   = os.path.join(DATA_DIR, "stocks.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
NOTIF_FILE    = os.path.join(DATA_DIR, "notifications.json")
os.makedirs(DATA_DIR, exist_ok=True)

COMPANY_DB = [
    {"name": "Amazon",           "ticker": "AMZN",    "exchange": "NASDAQ", "keywords": "amazon"},
    {"name": "Apple",            "ticker": "AAPL",    "exchange": "NASDAQ", "keywords": "apple"},
    {"name": "Microsoft",        "ticker": "MSFT",    "exchange": "NASDAQ", "keywords": "microsoft"},
    {"name": "Alphabet/Google",  "ticker": "GOOGL",   "exchange": "NASDAQ", "keywords": "alphabet google"},
    {"name": "Meta Platforms",   "ticker": "META",    "exchange": "NASDAQ", "keywords": "meta facebook"},
    {"name": "NVIDIA",           "ticker": "NVDA",    "exchange": "NASDAQ", "keywords": "nvidia"},
    {"name": "Tesla",            "ticker": "TSLA",    "exchange": "NASDAQ", "keywords": "tesla"},
    {"name": "Netflix",          "ticker": "NFLX",    "exchange": "NASDAQ", "keywords": "netflix"},
    {"name": "AMD",              "ticker": "AMD",     "exchange": "NASDAQ", "keywords": "amd advanced micro"},
    {"name": "Intel",            "ticker": "INTC",    "exchange": "NASDAQ", "keywords": "intel"},
    {"name": "Broadcom",         "ticker": "AVGO",    "exchange": "NASDAQ", "keywords": "broadcom"},
    {"name": "Adobe",            "ticker": "ADBE",    "exchange": "NASDAQ", "keywords": "adobe"},
    {"name": "Salesforce",       "ticker": "CRM",     "exchange": "NYSE",   "keywords": "salesforce"},
    {"name": "Palantir",         "ticker": "PLTR",    "exchange": "NASDAQ", "keywords": "palantir"},
    {"name": "Shopify",          "ticker": "SHOP",    "exchange": "NYSE",   "keywords": "shopify"},
    {"name": "Spotify",          "ticker": "SPOT",    "exchange": "NYSE",   "keywords": "spotify"},
    {"name": "Coinbase",         "ticker": "COIN",    "exchange": "NASDAQ", "keywords": "coinbase"},
    {"name": "PayPal",           "ticker": "PYPL",    "exchange": "NASDAQ", "keywords": "paypal"},
    {"name": "ASML",             "ticker": "ASML",    "exchange": "NASDAQ", "keywords": "asml"},
    {"name": "Visa",             "ticker": "V",       "exchange": "NYSE",   "keywords": "visa"},
    {"name": "Mastercard",       "ticker": "MA",      "exchange": "NYSE",   "keywords": "mastercard"},
    {"name": "JPMorgan",         "ticker": "JPM",     "exchange": "NYSE",   "keywords": "jpmorgan jp morgan"},
    {"name": "Berkshire B",      "ticker": "BRK-B",   "exchange": "NYSE",   "keywords": "berkshire"},
    {"name": "Eli Lilly",        "ticker": "LLY",     "exchange": "NYSE",   "keywords": "eli lilly"},
    {"name": "Novo Nordisk",     "ticker": "NVO",     "exchange": "NYSE",   "keywords": "novo nordisk novo"},
    {"name": "AstraZeneca",      "ticker": "AZN",     "exchange": "NASDAQ", "keywords": "astrazeneca astra"},
    {"name": "Pfizer",           "ticker": "PFE",     "exchange": "NYSE",   "keywords": "pfizer"},
    {"name": "BioNTech",         "ticker": "BNTX",    "exchange": "NASDAQ", "keywords": "biontech"},
    {"name": "Uber",             "ticker": "UBER",    "exchange": "NYSE",   "keywords": "uber"},
    {"name": "Airbnb",           "ticker": "ABNB",    "exchange": "NASDAQ", "keywords": "airbnb"},
    {"name": "Booking Holdings", "ticker": "BKNG",    "exchange": "NASDAQ", "keywords": "booking"},
    {"name": "ServiceNow",       "ticker": "NOW",     "exchange": "NYSE",   "keywords": "servicenow"},
    {"name": "Palo Alto",        "ticker": "PANW",    "exchange": "NASDAQ", "keywords": "palo alto"},
    {"name": "CrowdStrike",      "ticker": "CRWD",    "exchange": "NASDAQ", "keywords": "crowdstrike"},
    {"name": "Datadog",          "ticker": "DDOG",    "exchange": "NASDAQ", "keywords": "datadog"},
    {"name": "Snowflake",        "ticker": "SNOW",    "exchange": "NYSE",   "keywords": "snowflake"},
    {"name": "MongoDB",          "ticker": "MDB",     "exchange": "NASDAQ", "keywords": "mongodb"},
    {"name": "ARM Holdings",     "ticker": "ARM",     "exchange": "NASDAQ", "keywords": "arm holdings"},
    {"name": "Qualcomm",         "ticker": "QCOM",    "exchange": "NASDAQ", "keywords": "qualcomm"},
    {"name": "Texas Instruments","ticker": "TXN",     "exchange": "NASDAQ", "keywords": "texas instruments"},
    {"name": "Micron",           "ticker": "MU",      "exchange": "NASDAQ", "keywords": "micron"},
    {"name": "TSMC",             "ticker": "TSM",     "exchange": "NYSE",   "keywords": "tsmc taiwan semi"},
    {"name": "BASF",             "ticker": "BAS.DE",  "exchange": "XETRA",  "keywords": "basf"},
    {"name": "SAP",              "ticker": "SAP.DE",  "exchange": "XETRA",  "keywords": "sap"},
    {"name": "Siemens",          "ticker": "SIE.DE",  "exchange": "XETRA",  "keywords": "siemens"},
    {"name": "Volkswagen Vz.",   "ticker": "VOW3.DE", "exchange": "XETRA",  "keywords": "volkswagen vw"},
    {"name": "BMW",              "ticker": "BMW.DE",  "exchange": "XETRA",  "keywords": "bmw"},
    {"name": "Mercedes-Benz",    "ticker": "MBG.DE",  "exchange": "XETRA",  "keywords": "mercedes daimler"},
    {"name": "Allianz",          "ticker": "ALV.DE",  "exchange": "XETRA",  "keywords": "allianz"},
    {"name": "Deutsche Bank",    "ticker": "DBK.DE",  "exchange": "XETRA",  "keywords": "deutsche bank"},
    {"name": "Bayer",            "ticker": "BAYN.DE", "exchange": "XETRA",  "keywords": "bayer"},
    {"name": "Adidas",           "ticker": "ADS.DE",  "exchange": "XETRA",  "keywords": "adidas"},
    {"name": "Linde",            "ticker": "LIN.DE",  "exchange": "XETRA",  "keywords": "linde"},
    {"name": "Deutsche Telekom", "ticker": "DTE.DE",  "exchange": "XETRA",  "keywords": "telekom"},
    {"name": "Muenchener Rueck", "ticker": "MUV2.DE", "exchange": "XETRA",  "keywords": "munich re muench rueck"},
    {"name": "Infineon",         "ticker": "IFX.DE",  "exchange": "XETRA",  "keywords": "infineon"},
    {"name": "Rheinmetall",      "ticker": "RHM.DE",  "exchange": "XETRA",  "keywords": "rheinmetall"},
    {"name": "Porsche AG",       "ticker": "P911.DE", "exchange": "XETRA",  "keywords": "porsche ag"},
    {"name": "Zalando",          "ticker": "ZAL.DE",  "exchange": "XETRA",  "keywords": "zalando"},
    {"name": "Beiersdorf",       "ticker": "BEI.DE",  "exchange": "XETRA",  "keywords": "beiersdorf nivea"},
    {"name": "Eon",              "ticker": "EOAN.DE", "exchange": "XETRA",  "keywords": "eon energie"},
    {"name": "RWE",              "ticker": "RWE.DE",  "exchange": "XETRA",  "keywords": "rwe"},
    {"name": "Sartorius",        "ticker": "SRT3.DE", "exchange": "XETRA",  "keywords": "sartorius"},
    {"name": "Continental",      "ticker": "CON.DE",  "exchange": "XETRA",  "keywords": "continental"},
    {"name": "Airbus",           "ticker": "AIR.PA",  "exchange": "Euronext","keywords": "airbus"},
    {"name": "LVMH",             "ticker": "MC.PA",   "exchange": "Euronext","keywords": "lvmh louis vuitton"},
    {"name": "Sanofi",           "ticker": "SAN.PA",  "exchange": "Euronext","keywords": "sanofi"},
    {"name": "TotalEnergies",    "ticker": "TTE.PA",  "exchange": "Euronext","keywords": "total"},
    {"name": "Nestle",           "ticker": "NESN.SW", "exchange": "SIX",    "keywords": "nestle"},
    {"name": "Roche",            "ticker": "ROG.SW",  "exchange": "SIX",    "keywords": "roche"},
    {"name": "Novartis",         "ticker": "NOVN.SW", "exchange": "SIX",    "keywords": "novartis"},
    {"name": "ABB",              "ticker": "ABBN.SW", "exchange": "SIX",    "keywords": "abb"},
    {"name": "Shell",            "ticker": "SHEL",    "exchange": "NYSE",   "keywords": "shell"},
    {"name": "BP",               "ticker": "BP",      "exchange": "NYSE",   "keywords": "bp british petroleum"},
    {"name": "Walt Disney",      "ticker": "DIS",     "exchange": "NYSE",   "keywords": "disney walt"},
]

# ── Config laden ─────────────────────────────────────────────────
_CONFIG_DEFAULTS = {
    "timezone": "Europe/Berlin",
    "trading": {"days": [0, 1, 2, 3, 4], "start_hour": 8, "end_hour": 23},
    "refresh_interval_seconds": 3600,
}

def load_config():
    cfg = dict(_CONFIG_DEFAULTS)
    cfg["trading"] = dict(_CONFIG_DEFAULTS["trading"])
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            if "timezone" in loaded:
                cfg["timezone"] = loaded["timezone"]
            if "trading" in loaded and isinstance(loaded["trading"], dict):
                cfg["trading"].update(loaded["trading"])
            if "refresh_interval_seconds" in loaded:
                cfg["refresh_interval_seconds"] = int(loaded["refresh_interval_seconds"])
        except Exception as e:
            log.error(f"Fehler beim Lesen der config.yml: {e} – Standardwerte werden verwendet")
    return cfg

# ── Persistenz ───────────────────────────────────────────────────
def load_stocks():
    if os.path.exists(STOCKS_FILE):
        with open(STOCKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def save_stocks(stocks):
    with open(STOCKS_FILE, "w", encoding="utf-8") as f:
        json.dump(stocks, f, indent=2, ensure_ascii=False)

def load_settings():
    cfg = load_config()
    defaults = {
        "apprise_urls": [],
        "refresh_interval": cfg["refresh_interval_seconds"],
        "notifications_enabled": True,
    }
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            defaults.update(json.load(f))
    return defaults

def save_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)

def load_notifications():
    if os.path.exists(NOTIF_FILE):
        with open(NOTIF_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def save_notifications(notifs):
    with open(NOTIF_FILE, "w", encoding="utf-8") as f:
        json.dump(notifs[-100:], f, indent=2, ensure_ascii=False)

def add_log_entry(entry_type, title, body, success=True):
    notifs = load_notifications()
    notifs.append({
        "time":    datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        "type":    entry_type,
        "title":   title,
        "body":    body,
        "success": success,
    })
    save_notifications(notifs)

# ── Discount-Block-Logik ─────────────────────────────────────────
def get_block(discount_pct):
    if discount_pct < 20:
        return 0
    return int(discount_pct / 10) * 10

def initial_block(current_eur, ath_eur):
    if ath_eur <= 0:
        return 0
    return get_block((ath_eur - current_eur) / ath_eur * 100)

def check_and_notify(stock, new_current, new_ath):
    if new_ath <= 0:
        return stock.get("last_notified_block", 0)
    discount      = (new_ath - new_current) / new_ath * 100
    current_block = get_block(discount)
    last_block    = stock.get("last_notified_block", current_block)

    if current_block > last_block and current_block >= 20:
        level_price = round(new_ath * (1 - current_block / 100), 2)
        title = f"ATH-Alarm: {stock['name']} -{current_block}%-Block erreicht"
        body  = (
            f"{stock['name']} ({stock['ticker']}) hat den -{current_block}%-Block erreicht!\n\n"
            f"Aktueller Kurs:   {new_current:.2f} EUR\n"
            f"ATH:              {new_ath:.2f} EUR\n"
            f"Abstand zum ATH:  -{discount:.1f}%\n"
            f"-{current_block}%-Level:       {level_price:.2f} EUR"
        )
        log.info(f"Benachrichtigung: {title}")
        send_apprise(title, body)
        return current_block
    elif current_block < last_block:
        log.info(f"{stock['name']}: Block zurueck {last_block} -> {current_block}")
        return current_block
    return last_block

# ── Yahoo Finance & EUR ──────────────────────────────────────────
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

def get_eur_rate(currency):
    if currency == "EUR":
        return 1.0
    try:
        r = requests.get(f"https://api.frankfurter.app/latest?from={currency}&to=EUR", timeout=8)
        return float(r.json()["rates"]["EUR"])
    except Exception:
        fb = {"USD": 0.92, "GBP": 1.17, "CHF": 1.05, "JPY": 0.0062,
              "CAD": 0.68, "AUD": 0.60, "DKK": 0.134, "HKD": 0.118}
        return fb.get(currency, 0.92)

def fetch_stock_data(ticker):
    enc  = urlquote(ticker)
    urls = [
        f"https://query2.finance.yahoo.com/v8/finance/chart/{enc}?range=max&interval=1mo&includePrePost=false",
        f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?range=max&interval=1mo&includePrePost=false",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{enc}?range=5y&interval=1mo",
    ]
    data, last_err = None, "Unbekannter Fehler"
    for url in urls:
        try:
            r = requests.get(url, headers=YAHOO_HEADERS, timeout=15)
            r.raise_for_status()
            j = r.json()
            if j.get("chart", {}).get("result"):
                data = j; break
        except Exception as e:
            last_err = str(e)
    if not data:
        raise ValueError(f"Kein Zugriff auf Yahoo Finance: {last_err}")
    result   = data["chart"]["result"][0]
    meta     = result["meta"]
    currency = meta.get("currency", "USD")
    current  = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
    if not current:
        raise ValueError("Kein aktueller Kurs in der Antwort")
    q0     = (result.get("indicators", {}).get("quote") or [{}])[0]
    highs  = [h for h in (q0.get("high")  or []) if h and h > 0]
    closes = [c for c in (q0.get("close") or []) if c and c > 0]
    all_p  = highs + closes
    if not all_p:
        raise ValueError("Keine historischen Kurse in der Antwort")
    ath      = max(all_p)
    eur_rate = get_eur_rate(currency)
    return {
        "current_eur": round(float(current) * eur_rate, 2),
        "ath_eur":     round(max(float(ath), float(current)) * eur_rate, 2),
        "currency":    currency,
    }

# ── Apprise ──────────────────────────────────────────────────────
def send_apprise(title, body):
    settings = load_settings()
    if not settings.get("notifications_enabled"):
        return True
    urls = settings.get("apprise_urls", [])
    if not urls:
        log.warning("Keine Apprise-URLs konfiguriert")
        return False
    try:
        ap = apprise_lib.Apprise()
        for u in urls:
            ap.add(u)
        ok = ap.notify(title=title, body=body)
        add_log_entry("alert", title, body, ok)
        return ok
    except Exception as e:
        log.error(f"Apprise-Fehler: {e}")
        add_log_entry("alert", title, body, False)
        return False

# ── Refresh-Logik ────────────────────────────────────────────────
def refresh_all_stocks(trigger="auto"):
    log.info(f"Kurs-Refresh gestartet (trigger={trigger})")
    stocks  = load_stocks()
    ok_list, err_list = [], []
    for i, s in enumerate(stocks):
        try:
            data    = fetch_stock_data(s["ticker"])
            new_ath = max(data["ath_eur"], s.get("ath_eur", 0))
            new_blk = check_and_notify(s, data["current_eur"], new_ath)
            stocks[i] = {
                **s,
                "current_eur":         data["current_eur"],
                "ath_eur":             new_ath,
                "currency":            data["currency"],
                "last_notified_block": new_blk,
                "updated":             datetime.now().strftime("%d.%m.%Y %H:%M"),
            }
            ok_list.append(s["name"])
        except Exception as e:
            log.error(f"Fehler bei {s['name']}: {e}")
            err_list.append(f"{s['name']}: {e}")
    save_stocks(stocks)
    label = "Automatisch" if trigger == "auto" else "Manuell"
    body  = f"Aktualisiert: {', '.join(ok_list) or 'keine'}"
    if err_list:
        body += f"\nFehler: {', '.join(err_list)}"
    add_log_entry(f"{trigger}_refresh", f"{label}er Refresh", body, len(err_list) == 0)
    log.info(f"Kurs-Refresh abgeschlossen. OK={len(ok_list)} Fehler={len(err_list)}")

# ── Scheduler ────────────────────────────────────────────────────
# _last_refresh speichert den letzten automatischen Refresh-Zeitpunkt
_last_refresh = None
_start_of_day_done = None   # Datum des letzten 8-Uhr-Refreshes

scheduler = BackgroundScheduler(daemon=True)

def trading_window_check():
    """Wird jede Minute aufgerufen. Entscheidet ob ein Refresh faellig ist."""
    global _last_refresh, _start_of_day_done

    cfg      = load_config()
    tz       = pytz.timezone(cfg["timezone"])
    now      = datetime.now(tz)
    settings = load_settings()
    interval = settings.get("refresh_interval", cfg["refresh_interval_seconds"])

    trading  = cfg["trading"]
    days     = trading.get("days", [0, 1, 2, 3, 4])
    start_h  = trading.get("start_hour", 8)
    end_h    = trading.get("end_hour", 23)

    # Kein Handelstag
    if now.weekday() not in days:
        return

    # Ausserhalb der Handelszeit
    if now.hour < start_h or now.hour >= end_h:
        return

    today = now.date()

    # Erster Refresh des Tages genau um start_hour:00
    if now.hour == start_h and now.minute == 0 and _start_of_day_done != today:
        log.info(f"Tagesstart-Refresh um {start_h}:00 Uhr")
        _start_of_day_done = today
        _last_refresh = now
        refresh_all_stocks(trigger="auto")
        return

    # Regulaerer Intervall-Refresh
    if _last_refresh is None or (now - _last_refresh).total_seconds() >= interval:
        log.info(f"Intervall-Refresh (alle {interval}s)")
        _last_refresh = now
        refresh_all_stocks(trigger="auto")

def start_scheduler():
    # Jede Minute pruefen ob ein Refresh faellig ist
    scheduler.add_job(trading_window_check, "cron", minute="*",
                      id="trading_check", replace_existing=True)
    if not scheduler.running:
        scheduler.start()
    cfg = load_config()
    log.info(f"Scheduler gestartet | Handelstage={cfg['trading']['days']} "
             f"| Fenster={cfg['trading']['start_hour']}-{cfg['trading']['end_hour']} Uhr "
             f"| TZ={cfg['timezone']}")

def get_next_run_info():
    """Gibt einen lesbaren String zum naechsten geplanten Refresh zurueck."""
    cfg      = load_config()
    tz       = pytz.timezone(cfg["timezone"])
    now      = datetime.now(tz)
    settings = load_settings()
    interval = settings.get("refresh_interval", cfg["refresh_interval_seconds"])
    trading  = cfg["trading"]
    days     = trading.get("days", [0, 1, 2, 3, 4])
    start_h  = trading.get("start_hour", 8)
    end_h    = trading.get("end_hour", 23)

    # Naechsten gueltigen Zeitpunkt berechnen
    if _last_refresh:
        from datetime import timedelta
        candidate = _last_refresh + timedelta(seconds=interval)
        # Wenn candidate ausserhalb Handelsfenster -> naechsten start_h nehmen
        if candidate.hour >= end_h or candidate.weekday() not in days:
            # naechsten Handelstag start_h suchen
            d = candidate.date()
            from datetime import timedelta as td
            for i in range(1, 8):
                d = d + td(days=1)
                if d.weekday() in days:
                    next_dt = tz.localize(datetime(d.year, d.month, d.day, start_h, 0))
                    return next_dt.strftime("%d.%m.%Y %H:%M") + " Uhr"
        if candidate.hour < start_h:
            candidate = tz.localize(datetime(candidate.year, candidate.month, candidate.day, start_h, 0))
        return candidate.strftime("%d.%m.%Y %H:%M") + " Uhr"
    # Noch kein Refresh: naechsten Handelstag start_h
    from datetime import timedelta as td
    d = now.date()
    for i in range(0, 8):
        check = d if i == 0 else d + td(days=i)
        if check.weekday() in days:
            if i == 0 and now.hour < start_h:
                return tz.localize(datetime(check.year, check.month, check.day, start_h, 0)).strftime("%d.%m.%Y %H:%M") + " Uhr"
            elif i > 0:
                return tz.localize(datetime(check.year, check.month, check.day, start_h, 0)).strftime("%d.%m.%Y %H:%M") + " Uhr"
    return "unbekannt"

# ── API-Routen ───────────────────────────────────────────────────
@app.route("/api/stocks", methods=["GET"])
def get_stocks():
    return jsonify(load_stocks())

@app.route("/api/stocks", methods=["POST"])
def add_stock():
    body     = request.get_json()
    ticker   = body.get("ticker", "").strip().upper()
    name     = body.get("name", "").strip()
    exchange = body.get("exchange", "").strip()
    if not ticker or not name:
        return jsonify({"error": "ticker und name erforderlich"}), 400
    stocks = load_stocks()
    if any(s["ticker"] == ticker for s in stocks):
        return jsonify({"error": f"{name} ist bereits in der Liste"}), 409
    try:
        data = fetch_stock_data(ticker)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    blk = initial_block(data["current_eur"], data["ath_eur"])
    stock = {
        "name":                name,
        "ticker":              ticker,
        "exchange":            exchange,
        "current_eur":         data["current_eur"],
        "ath_eur":             data["ath_eur"],
        "currency":            data["currency"],
        "last_notified_block": blk,
        "updated":             datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    stocks.append(stock)
    save_stocks(stocks)
    return jsonify(stock), 201

@app.route("/api/stocks/<ticker>", methods=["DELETE"])
def delete_stock(ticker):
    stocks = load_stocks()
    new    = [s for s in stocks if s["ticker"] != ticker.upper()]
    if len(new) == len(stocks):
        return jsonify({"error": "Nicht gefunden"}), 404
    save_stocks(new)
    return jsonify({"ok": True})

@app.route("/api/stocks/<ticker>/refresh", methods=["POST"])
def refresh_stock(ticker):
    stocks = load_stocks()
    idx = next((i for i, s in enumerate(stocks) if s["ticker"] == ticker.upper()), None)
    if idx is None:
        return jsonify({"error": "Nicht gefunden"}), 404
    try:
        data    = fetch_stock_data(ticker)
        s       = stocks[idx]
        new_ath = max(data["ath_eur"], s.get("ath_eur", 0))
        new_blk = check_and_notify(s, data["current_eur"], new_ath)
        stocks[idx] = {
            **s,
            "current_eur":         data["current_eur"],
            "ath_eur":             new_ath,
            "currency":            data["currency"],
            "last_notified_block": new_blk,
            "updated":             datetime.now().strftime("%d.%m.%Y %H:%M"),
        }
        save_stocks(stocks)
        add_log_entry("manual_refresh",
                      f"Manueller Refresh: {s['name']}",
                      f"Kurs: {data['current_eur']} EUR | ATH: {new_ath} EUR", True)
        return jsonify(stocks[idx])
    except Exception as e:
        return jsonify({"error": str(e)}), 502

@app.route("/api/stocks/refresh-all", methods=["POST"])
def api_refresh_all():
    refresh_all_stocks(trigger="manual")
    return jsonify(load_stocks())

@app.route("/api/search", methods=["GET"])
def search_companies():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify([])

    def yahoo_search(query):
        url = (f"https://query1.finance.yahoo.com/v1/finance/search"
               f"?q={urlquote(query)}&quotesCount=10&newsCount=0&listsCount=0")
        r = requests.get(url, headers=YAHOO_HEADERS, timeout=8)
        r.raise_for_status()
        results = []
        for item in r.json().get("quotes", []):
            qtype = item.get("quoteType", "")
            if qtype not in ("EQUITY", "ETF", "MUTUALFUND", "INDEX", "CRYPTOCURRENCY"):
                continue
            name   = item.get("longname") or item.get("shortname") or item.get("symbol", "")
            ticker = item.get("symbol", "")
            exch   = item.get("exchDisp") or item.get("exchange", "")
            if ticker:
                results.append({"name": name, "ticker": ticker, "exchange": exch, "type": qtype})
        return results

    if re.match(r"^[A-Z0-9]{6}$", q.upper()):
        try:
            bff_h = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept":     "application/json",
                "Origin":     "https://www.boerse-frankfurt.de",
                "Referer":    "https://www.boerse-frankfurt.de/",
            }
            url   = f"https://api.boerse-frankfurt.de/v1/search/quick_search?searchTerms={q.upper()}&limit=6"
            r     = requests.get(url, headers=bff_h, timeout=8)
            items = r.json().get("data", [])
            results = []
            for item in items:
                isin    = item.get("isin", "")
                name    = item.get("name", "")
                wkn_val = item.get("wkn", q)
                suffix  = f"  [WKN {wkn_val}]"
                try:
                    yahoo = yahoo_search(isin)
                    if yahoo:
                        for y in yahoo:
                            y["name"] += suffix
                        results.extend(yahoo[:3])
                        continue
                except Exception:
                    pass
                results.append({"name": name + suffix, "ticker": isin,
                                 "exchange": "Frankfurt", "type": "ETF"})
            if results:
                return jsonify(results[:10])
        except Exception as e:
            log.warning(f"Boerse Frankfurt WKN-Suche fehlgeschlagen: {e}")

    try:
        results = yahoo_search(q)
        if results:
            return jsonify(results[:10])
    except Exception as e:
        log.warning(f"Yahoo Finance Suche fehlgeschlagen: {e}")

    ql = q.lower()
    fallback = [c for c in COMPANY_DB
                if ql in c["name"].lower() or ql in c["ticker"].lower() or ql in c["keywords"].lower()]
    return jsonify(fallback[:10])

@app.route("/api/settings", methods=["GET"])
def get_settings():
    s   = load_settings()
    cfg = load_config()
    s["next_refresh"]   = get_next_run_info()
    s["trading_config"] = cfg["trading"]
    s["timezone"]       = cfg["timezone"]
    return jsonify(s)

@app.route("/api/settings", methods=["POST"])
def update_settings():
    body = request.get_json()
    s    = load_settings()
    if "apprise_urls"          in body: s["apprise_urls"]          = body["apprise_urls"]
    if "notifications_enabled" in body: s["notifications_enabled"] = bool(body["notifications_enabled"])
    if "refresh_interval"      in body: s["refresh_interval"]      = int(body["refresh_interval"])
    save_settings(s)
    return jsonify(s)

@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    return jsonify(list(reversed(load_notifications())))

@app.route("/api/notifications/test", methods=["POST"])
def test_notification():
    ok = send_apprise("ATH-Tracker Testbenachrichtigung",
                      "Die Apprise-Verbindung funktioniert korrekt!")
    return jsonify({"ok": ok})

@app.route("/api/health", methods=["GET"])
def health():
    cfg = load_config()
    return jsonify({"status": "ok", "time": datetime.now().isoformat(),
                    "config": cfg, "next_refresh": get_next_run_info()})

if __name__ == "__main__":
    start_scheduler()
    app.run(host="0.0.0.0", port=5000, debug=False)
