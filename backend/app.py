import json
import re
import time
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
DEPOTS_FILE   = os.path.join(DATA_DIR, "depots.json")
NOTIF_FILE    = os.path.join(DATA_DIR, "notifications.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
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

# ── Config ───────────────────────────────────────────────────────
_CFG_DEF = {"timezone":"Europe/Berlin",
             "trading":{"days":[0,1,2,3,4],"start_hour":8,"end_hour":23},
             "refresh_interval_seconds":3600}

def load_config():
    cfg = {"timezone":_CFG_DEF["timezone"],"trading":dict(_CFG_DEF["trading"]),
           "refresh_interval_seconds":_CFG_DEF["refresh_interval_seconds"]}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE,encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            if "timezone" in loaded: cfg["timezone"] = loaded["timezone"]
            if "trading"  in loaded: cfg["trading"].update(loaded["trading"])
            if "refresh_interval_seconds" in loaded:
                cfg["refresh_interval_seconds"] = int(loaded["refresh_interval_seconds"])
        except Exception as e:
            log.error(f"config.yml Fehler: {e}")
    return cfg

# ── Datei-Helfer ─────────────────────────────────────────────────
def _safe(s): return re.sub(r'[^a-z0-9_\-]','_',s.lower())

def depot_file(depot_id):
    return os.path.join(DATA_DIR, f"depot_{_safe(depot_id)}.json")

def watchlist_file(depot_id, wl_id):
    return os.path.join(DATA_DIR, f"wl_{_safe(depot_id)}_{_safe(wl_id)}.json")

def load_stocks(depot_id):
    p = depot_file(depot_id)
    return json.load(open(p,encoding="utf-8")) if os.path.exists(p) else []

def save_stocks(depot_id, stocks):
    json.dump(stocks, open(depot_file(depot_id),"w",encoding="utf-8"), indent=2, ensure_ascii=False)

def load_wl_stocks(depot_id, wl_id):
    p = watchlist_file(depot_id, wl_id)
    return json.load(open(p,encoding="utf-8")) if os.path.exists(p) else []

def save_wl_stocks(depot_id, wl_id, stocks):
    json.dump(stocks, open(watchlist_file(depot_id,wl_id),"w",encoding="utf-8"), indent=2, ensure_ascii=False)

def load_depots():
    return json.load(open(DEPOTS_FILE,encoding="utf-8")) if os.path.exists(DEPOTS_FILE) else []

def save_depots(depots):
    json.dump(depots, open(DEPOTS_FILE,"w",encoding="utf-8"), indent=2, ensure_ascii=False)

def load_settings():
    cfg = load_config()
    d   = {"refresh_interval":cfg["refresh_interval_seconds"],"notifications_enabled":True}
    if os.path.exists(SETTINGS_FILE):
        d.update(json.load(open(SETTINGS_FILE,encoding="utf-8")))
    d.pop("apprise_urls", None)
    return d

def save_settings(s):
    json.dump(s, open(SETTINGS_FILE,"w",encoding="utf-8"), indent=2, ensure_ascii=False)

def load_notifications():
    return json.load(open(NOTIF_FILE,encoding="utf-8")) if os.path.exists(NOTIF_FILE) else []

def save_notifications(n):
    json.dump(n[-100:], open(NOTIF_FILE,"w",encoding="utf-8"), indent=2, ensure_ascii=False)

def add_log(etype, title, body, success=True):
    n = load_notifications()
    n.append({"time":datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
               "type":etype,"title":title,"body":body,"success":success})
    save_notifications(n)

# ── Migration ────────────────────────────────────────────────────
def migrate_if_needed():
    if os.path.exists(DEPOTS_FILE):
        depots = load_depots(); changed = False
        for d in depots:
            if "apprise_urls" not in d: d["apprise_urls"] = []; changed = True
            if "watchlists"   not in d: d["watchlists"]   = []; changed = True
        if changed: save_depots(depots)
        return
    old = os.path.join(DATA_DIR,"stocks.json")
    did, dname = "mein_depot", "Mein Depot"
    global_urls = []
    if os.path.exists(SETTINGS_FILE):
        try:
            s = json.load(open(SETTINGS_FILE,encoding="utf-8"))
            global_urls = s.pop("apprise_urls",[])
            json.dump(s, open(SETTINGS_FILE,"w",encoding="utf-8"), indent=2)
        except Exception: pass
    if os.path.exists(old):
        import shutil; shutil.copy(old, depot_file(did))
        log.info("Migration: stocks.json -> depot_mein_depot.json")
    else:
        save_stocks(did, [])
    save_depots([{"id":did,"name":dname,"apprise_urls":global_urls,"watchlists":[]}])
    log.info("Migration abgeschlossen")

# ── Discount-Block ───────────────────────────────────────────────
def get_block(d): return 0 if d < 20 else int(d/10)*10
def initial_block(cur,ath): return 0 if ath<=0 else get_block((ath-cur)/ath*100)

def check_and_notify(stock, new_cur, new_ath, label="", urls=None):
    if new_ath <= 0: return stock.get("last_notified_block",0)
    d  = (new_ath-new_cur)/new_ath*100
    cb = get_block(d); lb = stock.get("last_notified_block",cb)
    if cb > lb and cb >= 20:
        lp    = round(new_ath*(1-cb/100),2)
        title = f"ATH-Alarm [{label}]: {stock['name']} -{cb}%-Block"
        body  = (f"{stock['name']} ({stock['ticker']}) — {label}\n\n"
                 f"Aktueller Kurs:  {new_cur:.2f} EUR\n"
                 f"ATH:             {new_ath:.2f} EUR\n"
                 f"Abstand zum ATH: -{d:.1f}%\n"
                 f"-{cb}%-Level:    {lp:.2f} EUR")
        send_apprise(title, body, urls or [])
        return cb
    elif cb < lb: return cb
    return lb

# ── Yahoo Finance ────────────────────────────────────────────────
YH = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
      "Accept":"application/json"}

def get_eur_rate(currency):
    if currency=="EUR": return 1.0
    try:
        r = requests.get(f"https://api.frankfurter.app/latest?from={currency}&to=EUR",timeout=8)
        return float(r.json()["rates"]["EUR"])
    except Exception:
        return {"USD":0.92,"GBP":1.17,"CHF":1.05,"JPY":0.0062,"CAD":0.68,"AUD":0.60,"DKK":0.134,"HKD":0.118}.get(currency,0.92)

def fetch_stock_data(ticker):
    enc  = urlquote(ticker)
    urls = [f"https://query2.finance.yahoo.com/v8/finance/chart/{enc}?range=max&interval=1mo&includePrePost=false",
            f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?range=max&interval=1mo&includePrePost=false",
            f"https://query2.finance.yahoo.com/v8/finance/chart/{enc}?range=5y&interval=1mo"]
    data, last_err = None, "Unbekannter Fehler"
    for url in urls:
        try:
            r = requests.get(url,headers=YH,timeout=15); r.raise_for_status()
            j = r.json()
            if j.get("chart",{}).get("result"): data=j; break
        except Exception as e: last_err=str(e)
    if not data: raise ValueError(f"Kein Zugriff auf Yahoo Finance: {last_err}")
    result=data["chart"]["result"][0]; meta=result["meta"]
    currency=meta.get("currency","USD")
    current=meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
    if not current: raise ValueError("Kein aktueller Kurs")
    q0=(result.get("indicators",{}).get("quote") or [{}])[0]
    highs=[h for h in (q0.get("high") or []) if h and h>0]
    closes=[c for c in (q0.get("close") or []) if c and c>0]
    all_p=highs+closes
    if not all_p: raise ValueError("Keine historischen Kurse")
    ath=max(all_p); eur=get_eur_rate(currency)
    mt_str=None
    mt=meta.get("regularMarketTime")
    if mt:
        try:
            tz=pytz.timezone(load_config().get("timezone","Europe/Berlin"))
            mt_str=datetime.fromtimestamp(int(mt),tz=tz).strftime("%d.%m.%Y %H:%M")
        except Exception: pass
    return {"current_eur":round(float(current)*eur,2),"ath_eur":round(max(float(ath),float(current))*eur,2),
            "currency":currency,"market_time":mt_str}

# ── Apprise ──────────────────────────────────────────────────────
def send_apprise(title, body, urls):
    if not load_settings().get("notifications_enabled",True): return True
    if not urls: log.warning("Keine Apprise-URLs konfiguriert"); return False
    try:
        ap=apprise_lib.Apprise()
        for u in urls: ap.add(u)
        ok=ap.notify(title=title,body=body)
        add_log("alert",title,body,ok); return ok
    except Exception as e:
        log.error(f"Apprise: {e}"); add_log("alert",title,body,False); return False

# ── Refresh-Helfer ───────────────────────────────────────────────
def _make_stock(data, old=None):
    base = old or {}
    return {**base, "current_eur":data["current_eur"], "ath_eur":max(data["ath_eur"],base.get("ath_eur",0)),
            "currency":data["currency"], "market_time":data.get("market_time"),
            "updated":datetime.now().strftime("%d.%m.%Y %H:%M")}

def _refresh_stock_list(stocks, label, urls):
    ok_list, err_list = [], []
    for i,s in enumerate(stocks):
        try:
            data=fetch_stock_data(s["ticker"])
            new_ath=max(data["ath_eur"],s.get("ath_eur",0))
            new_blk=check_and_notify(s,data["current_eur"],new_ath,label,urls)
            stocks[i]={**_make_stock(data,s),"last_notified_block":new_blk}
            ok_list.append(s["name"])
        except Exception as e:
            log.error(f"[{label}] {s['name']}: {e}"); err_list.append(f"{s['name']}: {e}")
    return stocks, ok_list, err_list

def _refresh_depot(depot, trigger="auto"):
    did=depot["id"]; dname=depot["name"]; urls=depot.get("apprise_urls",[])
    # Bestand
    stocks=load_stocks(did)
    stocks,ok,err=_refresh_stock_list(stocks, f"Bestand: {dname}", urls)
    save_stocks(did,stocks)
    # Beobachtungslisten
    for wl in depot.get("watchlists",[]):
        wl_stocks=load_wl_stocks(did,wl["id"])
        wl_stocks,wok,werr=_refresh_stock_list(wl_stocks, f"Beobachtung: {wl['name']} ({dname})", urls)
        save_wl_stocks(did,wl["id"],wl_stocks)
        ok+=wok; err+=werr
    return ok, err

def refresh_all_depots(trigger="auto"):
    log.info(f"Refresh alle Depots (trigger={trigger})")
    depots=load_depots(); total_ok,total_err=[],[]
    for depot in depots:
        ok,err=_refresh_depot(depot,trigger)
        total_ok+=ok; total_err+=err
    label="Automatisch" if trigger=="auto" else "Manuell"
    add_log(f"{trigger}_refresh",f"{label}er Refresh",
            f"Depots: {len(depots)} | OK: {len(total_ok)} | Fehler: {len(total_err)}",len(total_err)==0)

# ── Scheduler ────────────────────────────────────────────────────
scheduler=BackgroundScheduler(daemon=True)
_last_refresh=None; _start_of_day_done=None

def trading_window_check():
    global _last_refresh, _start_of_day_done
    cfg=load_config(); tz=pytz.timezone(cfg["timezone"]); now=datetime.now(tz)
    settings=load_settings(); interval=settings.get("refresh_interval",cfg["refresh_interval_seconds"])
    t=cfg["trading"]; days=t.get("days",[0,1,2,3,4]); sh=t.get("start_hour",8); eh=t.get("end_hour",23)
    if now.weekday() not in days or now.hour<sh or now.hour>=eh: return
    today=now.date()
    if now.hour==sh and now.minute==0 and _start_of_day_done!=today:
        _start_of_day_done=today; _last_refresh=now; refresh_all_depots("auto"); return
    if _last_refresh is None or (now-_last_refresh).total_seconds()>=interval:
        _last_refresh=now; refresh_all_depots("auto")

def get_next_run_info():
    from datetime import timedelta
    cfg=load_config(); tz=pytz.timezone(cfg["timezone"]); now=datetime.now(tz)
    s=load_settings(); interval=s.get("refresh_interval",cfg["refresh_interval_seconds"])
    t=cfg["trading"]; days=t.get("days",[0,1,2,3,4]); sh=t.get("start_hour",8); eh=t.get("end_hour",23)
    if _last_refresh:
        c=_last_refresh+timedelta(seconds=interval)
        if c.hour>=eh or c.weekday() not in days:
            d=c.date()
            for i in range(1,8):
                d+=timedelta(days=1)
                if d.weekday() in days:
                    return tz.localize(datetime(d.year,d.month,d.day,sh,0)).strftime("%d.%m.%Y %H:%M")+" Uhr"
        if c.hour<sh: c=tz.localize(datetime(c.year,c.month,c.day,sh,0))
        return c.strftime("%d.%m.%Y %H:%M")+" Uhr"
    d=now.date()
    for i in range(0,8):
        check=d if i==0 else d+timedelta(days=i)
        if check.weekday() in days:
            if i==0 and now.hour<sh:
                return tz.localize(datetime(check.year,check.month,check.day,sh,0)).strftime("%d.%m.%Y %H:%M")+" Uhr"
            elif i>0:
                return tz.localize(datetime(check.year,check.month,check.day,sh,0)).strftime("%d.%m.%Y %H:%M")+" Uhr"
    return "unbekannt"

def start_scheduler():
    scheduler.add_job(trading_window_check,"cron",minute="*",id="trading_check",replace_existing=True,misfire_grace_time=120)
    if not scheduler.running: scheduler.start()
    log.info("Scheduler gestartet")

# ── API: Depots ──────────────────────────────────────────────────
def gen_id(name): return f"{re.sub(r'[^a-z0-9]','_',name.lower())[:20].strip('_')}_{int(time.time())}"

@app.route("/api/depots", methods=["GET"])
def get_depots(): return jsonify(load_depots())

@app.route("/api/depots", methods=["POST"])
def create_depot():
    body=request.get_json(); name=body.get("name","").strip()
    if not name: return jsonify({"error":"Name erforderlich"}),400
    depots=load_depots()
    if any(d["name"].lower()==name.lower() for d in depots): return jsonify({"error":"Name existiert bereits"}),409
    did=gen_id(name); save_stocks(did,[])
    depot={"id":did,"name":name,"apprise_urls":[],"watchlists":[]}
    depots.append(depot); save_depots(depots)
    return jsonify(depot),201

@app.route("/api/depots/<depot_id>", methods=["PUT"])
def update_depot(depot_id):
    body=request.get_json(); depots=load_depots()
    for d in depots:
        if d["id"]==depot_id:
            if "name" in body and body["name"].strip(): d["name"]=body["name"].strip()
            if "apprise_urls" in body: d["apprise_urls"]=body["apprise_urls"]
            save_depots(depots); return jsonify(d)
    return jsonify({"error":"Nicht gefunden"}),404

@app.route("/api/depots/<depot_id>", methods=["DELETE"])
def delete_depot(depot_id):
    depots=load_depots()
    if len(depots)<=1: return jsonify({"error":"Letztes Depot kann nicht gelöscht werden"}),400
    depot=next((d for d in depots if d["id"]==depot_id),None)
    if not depot: return jsonify({"error":"Nicht gefunden"}),404
    # Alle Dateien loeschen
    for f in [depot_file(depot_id)]+[watchlist_file(depot_id,wl["id"]) for wl in depot.get("watchlists",[])]:
        if os.path.exists(f): os.remove(f)
    save_depots([d for d in depots if d["id"]!=depot_id])
    return jsonify({"ok":True})

# ── API: Watchlists ──────────────────────────────────────────────
@app.route("/api/depots/<depot_id>/watchlists", methods=["POST"])
def create_watchlist(depot_id):
    body=request.get_json(); name=body.get("name","").strip()
    if not name: return jsonify({"error":"Name erforderlich"}),400
    depots=load_depots()
    depot=next((d for d in depots if d["id"]==depot_id),None)
    if not depot: return jsonify({"error":"Depot nicht gefunden"}),404
    if any(w["name"].lower()==name.lower() for w in depot.get("watchlists",[])):
        return jsonify({"error":"Name existiert bereits"}),409
    wl_id=gen_id(name); save_wl_stocks(depot_id,wl_id,[])
    wl={"id":wl_id,"name":name}
    depot.setdefault("watchlists",[]).append(wl)
    save_depots(depots)
    return jsonify(wl),201

@app.route("/api/depots/<depot_id>/watchlists/<wl_id>", methods=["PUT"])
def update_watchlist(depot_id, wl_id):
    body=request.get_json(); depots=load_depots()
    depot=next((d for d in depots if d["id"]==depot_id),None)
    if not depot: return jsonify({"error":"Nicht gefunden"}),404
    for wl in depot.get("watchlists",[]):
        if wl["id"]==wl_id:
            if "name" in body and body["name"].strip(): wl["name"]=body["name"].strip()
            save_depots(depots); return jsonify(wl)
    return jsonify({"error":"Nicht gefunden"}),404

@app.route("/api/depots/<depot_id>/watchlists/<wl_id>", methods=["DELETE"])
def delete_watchlist(depot_id, wl_id):
    depots=load_depots()
    depot=next((d for d in depots if d["id"]==depot_id),None)
    if not depot: return jsonify({"error":"Nicht gefunden"}),404
    f=watchlist_file(depot_id,wl_id)
    if os.path.exists(f): os.remove(f)
    depot["watchlists"]=[w for w in depot.get("watchlists",[]) if w["id"]!=wl_id]
    save_depots(depots); return jsonify({"ok":True})

# ── API: Stocks (Bestand) ────────────────────────────────────────
@app.route("/api/stocks", methods=["GET"])
def api_get_stocks():
    did=request.args.get("depot","")
    depots=load_depots()
    if not did and depots: did=depots[0]["id"]
    return jsonify(load_stocks(did))

@app.route("/api/stocks", methods=["POST"])
def api_add_stock():
    body=request.get_json()
    did=body.get("depot",""); ticker=body.get("ticker","").strip().upper()
    name=body.get("name","").strip(); exchange=body.get("exchange","").strip()
    if not did or not ticker or not name: return jsonify({"error":"depot, ticker, name erforderlich"}),400
    stocks=load_stocks(did)
    if any(s["ticker"]==ticker for s in stocks): return jsonify({"error":f"{name} bereits im Depot"}),409
    try: data=fetch_stock_data(ticker)
    except Exception as e: return jsonify({"error":str(e)}),502
    stock={"name":name,"ticker":ticker,"exchange":exchange,"current_eur":data["current_eur"],
           "ath_eur":data["ath_eur"],"currency":data["currency"],"market_time":data.get("market_time"),
           "last_notified_block":initial_block(data["current_eur"],data["ath_eur"]),
           "updated":datetime.now().strftime("%d.%m.%Y %H:%M")}
    stocks.append(stock); save_stocks(did,stocks)
    return jsonify(stock),201

@app.route("/api/stocks/<ticker>", methods=["DELETE"])
def api_delete_stock(ticker):
    did=request.args.get("depot","")
    stocks=[s for s in load_stocks(did) if s["ticker"]!=ticker.upper()]
    save_stocks(did,stocks); return jsonify({"ok":True})

@app.route("/api/stocks/<ticker>/refresh", methods=["POST"])
def api_refresh_stock(ticker):
    did=request.args.get("depot","")
    depots=load_depots(); depot=next((d for d in depots if d["id"]==did),{"id":did,"name":did,"apprise_urls":[]})
    stocks=load_stocks(did)
    idx=next((i for i,s in enumerate(stocks) if s["ticker"]==ticker.upper()),None)
    if idx is None: return jsonify({"error":"Nicht gefunden"}),404
    try:
        data=fetch_stock_data(ticker); s=stocks[idx]
        new_ath=max(data["ath_eur"],s.get("ath_eur",0))
        new_blk=check_and_notify(s,data["current_eur"],new_ath,f"Bestand: {depot['name']}",depot.get("apprise_urls",[]))
        stocks[idx]={**_make_stock(data,s),"last_notified_block":new_blk}
        save_stocks(did,stocks)
        add_log("manual_refresh",f"Refresh Bestand: {s['name']}",f"Kurs: {data['current_eur']} EUR",True)
        return jsonify(stocks[idx])
    except Exception as e: return jsonify({"error":str(e)}),502

@app.route("/api/stocks/refresh-all", methods=["POST"])
def api_refresh_all():
    did=request.args.get("depot","")
    if did:
        depots=load_depots(); depot=next((d for d in depots if d["id"]==did),None)
        if depot:
            ok,err=_refresh_depot(depot,"manual")
            add_log("manual_refresh",f"Manueller Refresh: {depot['name']}",f"OK: {len(ok)} Fehler: {len(err)}",len(err)==0)
        return jsonify(load_stocks(did))
    refresh_all_depots("manual"); return jsonify({"ok":True})

# ── API: Stocks (Watchlist) ──────────────────────────────────────
@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks", methods=["GET"])
def wl_get_stocks(depot_id, wl_id):
    return jsonify(load_wl_stocks(depot_id, wl_id))

@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks", methods=["POST"])
def wl_add_stock(depot_id, wl_id):
    body=request.get_json()
    ticker=body.get("ticker","").strip().upper(); name=body.get("name","").strip()
    exchange=body.get("exchange","").strip()
    if not ticker or not name: return jsonify({"error":"ticker und name erforderlich"}),400
    stocks=load_wl_stocks(depot_id,wl_id)
    if any(s["ticker"]==ticker for s in stocks): return jsonify({"error":f"{name} bereits in dieser Beobachtungsliste"}),409
    try: data=fetch_stock_data(ticker)
    except Exception as e: return jsonify({"error":str(e)}),502
    stock={"name":name,"ticker":ticker,"exchange":exchange,"current_eur":data["current_eur"],
           "ath_eur":data["ath_eur"],"currency":data["currency"],"market_time":data.get("market_time"),
           "last_notified_block":initial_block(data["current_eur"],data["ath_eur"]),
           "updated":datetime.now().strftime("%d.%m.%Y %H:%M")}
    stocks.append(stock); save_wl_stocks(depot_id,wl_id,stocks)
    return jsonify(stock),201

@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks/<ticker>", methods=["DELETE"])
def wl_delete_stock(depot_id, wl_id, ticker):
    stocks=[s for s in load_wl_stocks(depot_id,wl_id) if s["ticker"]!=ticker.upper()]
    save_wl_stocks(depot_id,wl_id,stocks); return jsonify({"ok":True})

@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks/<ticker>/refresh", methods=["POST"])
def wl_refresh_stock(depot_id, wl_id, ticker):
    depots=load_depots(); depot=next((d for d in depots if d["id"]==depot_id),{"name":depot_id,"apprise_urls":[]})
    wl_name=next((w["name"] for w in depot.get("watchlists",[]) if w["id"]==wl_id),wl_id)
    stocks=load_wl_stocks(depot_id,wl_id)
    idx=next((i for i,s in enumerate(stocks) if s["ticker"]==ticker.upper()),None)
    if idx is None: return jsonify({"error":"Nicht gefunden"}),404
    try:
        data=fetch_stock_data(ticker); s=stocks[idx]
        new_ath=max(data["ath_eur"],s.get("ath_eur",0))
        new_blk=check_and_notify(s,data["current_eur"],new_ath,f"Beobachtung: {wl_name}",depot.get("apprise_urls",[]))
        stocks[idx]={**_make_stock(data,s),"last_notified_block":new_blk}
        save_wl_stocks(depot_id,wl_id,stocks)
        add_log("manual_refresh",f"Refresh Beobachtung: {s['name']}",f"Liste: {wl_name} | Kurs: {data['current_eur']} EUR",True)
        return jsonify(stocks[idx])
    except Exception as e: return jsonify({"error":str(e)}),502

@app.route("/api/stocks/<ticker>/move-to-watchlist", methods=["POST"])
def move_to_watchlist(ticker):
    """Aktie aus Bestand in eine Beobachtungsliste verschieben."""
    body     = request.get_json()
    depot_id = body.get("depot_id","")
    wl_id    = body.get("wl_id","")
    stocks   = load_stocks(depot_id)
    stock    = next((s for s in stocks if s["ticker"]==ticker.upper()),None)
    if not stock: return jsonify({"error":"Nicht gefunden"}),404
    wl_stocks = load_wl_stocks(depot_id,wl_id)
    if any(s["ticker"]==ticker.upper() for s in wl_stocks):
        return jsonify({"error":f"{stock['name']} ist bereits in dieser Beobachtungsliste"}),409
    stock = dict(stock)
    stock["last_notified_block"] = initial_block(stock["current_eur"],stock["ath_eur"])
    wl_stocks.append(stock); save_wl_stocks(depot_id,wl_id,wl_stocks)
    save_stocks(depot_id,[s for s in stocks if s["ticker"]!=ticker.upper()])
    depots = load_depots(); depot = next((d for d in depots if d["id"]==depot_id),{"name":depot_id})
    wl_name = next((w["name"] for w in depot.get("watchlists",[]) if w["id"]==wl_id),wl_id)
    add_log("manual_refresh",f"In Beobachtung verschoben: {stock['name']}",
            f"Von Bestand '{depot['name']}' zur Beobachtungsliste '{wl_name}'",True)
    return jsonify({"ok":True})

@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks/<ticker>/move", methods=["POST"])
def wl_move_to_depot(depot_id, wl_id, ticker):
    """Aktie aus Beobachtungsliste ins Depot verschieben."""
    wl_stocks=load_wl_stocks(depot_id,wl_id)
    stock=next((s for s in wl_stocks if s["ticker"]==ticker.upper()),None)
    if not stock: return jsonify({"error":"Nicht gefunden"}),404
    depot_stocks=load_stocks(depot_id)
    if any(s["ticker"]==ticker.upper() for s in depot_stocks):
        return jsonify({"error":f"{stock['name']} ist bereits im Depot"}),409
    # Benachrichtigungsstand zurücksetzen
    stock=dict(stock); stock["last_notified_block"]=initial_block(stock["current_eur"],stock["ath_eur"])
    depot_stocks.append(stock); save_stocks(depot_id,depot_stocks)
    save_wl_stocks(depot_id,wl_id,[s for s in wl_stocks if s["ticker"]!=ticker.upper()])
    depots=load_depots(); depot=next((d for d in depots if d["id"]==depot_id),{"name":depot_id})
    wl_name=next((w["name"] for w in depot.get("watchlists",[]) if w["id"]==wl_id),wl_id)
    add_log("manual_refresh",f"Ins Depot verschoben: {stock['name']}",
            f"Von Beobachtung '{wl_name}' ins Depot '{depot['name']}'",True)
    return jsonify({"ok":True,"stock":stock})

# ── API: Search & Settings & Notifications ───────────────────────
@app.route("/api/search", methods=["GET"])
def search_companies():
    q=request.args.get("q","").strip()
    if not q: return jsonify([])
    def yahoo(query):
        url=f"https://query1.finance.yahoo.com/v1/finance/search?q={urlquote(query)}&quotesCount=10&newsCount=0&listsCount=0"
        r=requests.get(url,headers=YH,timeout=8); r.raise_for_status()
        res=[]
        for item in r.json().get("quotes",[]):
            qt=item.get("quoteType","")
            if qt not in ("EQUITY","ETF","MUTUALFUND","INDEX","CRYPTOCURRENCY"): continue
            name=item.get("longname") or item.get("shortname") or item.get("symbol","")
            ticker=item.get("symbol",""); exch=item.get("exchDisp") or item.get("exchange","")
            if ticker: res.append({"name":name,"ticker":ticker,"exchange":exch,"type":qt})
        return res
    if re.match(r"^[A-Z0-9]{6}$",q.upper()):
        try:
            bh={"User-Agent":"Mozilla/5.0","Accept":"application/json",
                "Origin":"https://www.boerse-frankfurt.de","Referer":"https://www.boerse-frankfurt.de/"}
            r=requests.get(f"https://api.boerse-frankfurt.de/v1/search/quick_search?searchTerms={q.upper()}&limit=6",headers=bh,timeout=8)
            res=[]
            for item in r.json().get("data",[]):
                isin=item.get("isin",""); wkn=item.get("wkn",q); sfx=f"  [WKN {wkn}]"
                try:
                    yres=yahoo(isin)
                    if yres:
                        for y in yres: y["name"]+=sfx
                        res.extend(yres[:3]); continue
                except Exception: pass
                res.append({"name":item.get("name","")+sfx,"ticker":isin,"exchange":"Frankfurt","type":"ETF"})
            if res: return jsonify(res[:10])
        except Exception as e: log.warning(f"BFF: {e}")
    try:
        res=yahoo(q)
        if res: return jsonify(res[:10])
    except Exception as e: log.warning(f"Yahoo: {e}")
    ql=q.lower()
    return jsonify([c for c in COMPANY_DB if ql in c["name"].lower() or ql in c["ticker"].lower() or ql in c["keywords"].lower()][:10])

@app.route("/api/settings", methods=["GET"])
def get_settings():
    s=load_settings(); cfg=load_config()
    s["next_refresh"]=get_next_run_info(); s["trading_config"]=cfg["trading"]; s["timezone"]=cfg["timezone"]
    return jsonify(s)

@app.route("/api/settings", methods=["POST"])
def update_settings():
    body=request.get_json(); s=load_settings()
    if "notifications_enabled" in body: s["notifications_enabled"]=bool(body["notifications_enabled"])
    if "refresh_interval"      in body: s["refresh_interval"]=int(body["refresh_interval"])
    save_settings(s); return jsonify(s)

@app.route("/api/notifications", methods=["GET"])
def get_notifications(): return jsonify(list(reversed(load_notifications())))

@app.route("/api/notifications/test", methods=["POST"])
def test_notification():
    body=request.get_json(silent=True) or {}; urls=body.get("urls",[])
    ok=send_apprise("ATH-Tracker Testbenachrichtigung","Verbindung funktioniert!",urls)
    return jsonify({"ok":ok})

@app.route("/api/health", methods=["GET"])
def health(): return jsonify({"status":"ok","time":datetime.now().isoformat(),"next_refresh":get_next_run_info()})

if __name__=="__main__":
    migrate_if_needed(); start_scheduler()
    app.run(host="0.0.0.0",port=5000,debug=False)
