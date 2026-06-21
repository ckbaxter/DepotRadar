import json, re, time as time_mod, hashlib, base64, secrets, logging, os, math, shutil, uuid as _uuid
from collections import Counter
from datetime import datetime, timedelta
from urllib.parse import quote as urlquote

import pytz, requests, apprise as apprise_lib
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, jsonify, request, redirect

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)
app = Flask(__name__)

DATA_DIR      = "/data"
DEPOTS_FILE   = os.path.join(DATA_DIR, "depots.json")
NOTIF_FILE     = os.path.join(DATA_DIR, "notifications.json")
SPLITS_FILE    = os.path.join(DATA_DIR, "splits.json")
SETTINGS_FILE  = os.path.join(DATA_DIR, "settings.json")
USERS_FILE     = os.path.join(DATA_DIR, "users.json")
SNAPSHOTS_FILE = os.path.join(DATA_DIR, "snapshots.json")
os.makedirs(DATA_DIR, exist_ok=True)

VERSION           = "2.7.2"
APP_URL           = os.environ.get("APP_URL", "").rstrip("/")
PARQET_API_BASE   = "https://connect.parqet.com"
PARQET_AUTH_URL   = "https://connect.parqet.com/oauth2/authorize"
PARQET_TOKEN_URL  = "https://connect.parqet.com/oauth2/token"

# Bekannte Aktiensplits: ISIN → [(datum_str, multiplikator)]
DEFAULT_SPLITS = [
    {"isin": "US67066G1040", "name": "NVIDIA",          "date": "2024-06-10", "ratio": 10},
    {"isin": "US11135F1012", "name": "Broadcom",         "date": "2024-07-15", "ratio": 10},
    {"isin": "US09857L1089", "name": "Booking Holdings", "date": "2026-04-06", "ratio": 25},
]

def load_splits():
    """Lädt Splits aus data/splits.json. Legt Datei mit Defaults an wenn nicht vorhanden."""
    if not os.path.exists(SPLITS_FILE):
        _save_json(SPLITS_FILE, DEFAULT_SPLITS)
    return _load_json(SPLITS_FILE, DEFAULT_SPLITS)

def splits_as_dict():
    """Gibt Splits als Dict {isin: [(date, ratio)]} zurück."""
    result = {}
    for s in load_splits():
        result.setdefault(s["isin"], []).append((s["date"], s["ratio"]))
    return result



# ── Config ────────────────────────────────────────────────────────
_CFG_DEF = {
    "timezone": "Europe/Berlin",
    "trading":  {"days": [0,1,2,3,4], "start_hour": 8, "start_minute": 0, "end_hour": 23, "end_minute": 0},
    "refresh_interval_seconds": 3600,
}

# ── File helpers ──────────────────────────────────────────────────
def _safe(s):            return re.sub(r'[^a-z0-9_\-]', '_', s.lower())
def depot_file(d):        return os.path.join(DATA_DIR, f"depot_{_safe(d)}.json")
def depot_backup_file(d): return os.path.join(DATA_DIR, f"depot_{_safe(d)}_backup.json")
def watchlist_file(d,w): return os.path.join(DATA_DIR, f"wl_{_safe(d)}_{_safe(w)}.json")

def _load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def _save_json(path, data):
    """Schreibt atomar: erst in eine eindeutige Temp-Datei im selben Verzeichnis
    (gleiche Filesystem-Partition garantiert atomares os.replace), dann fsync
    vor dem Rename. Verhindert eine kaputte/halb geschriebene JSON-Datei falls
    der Prozess mitten im Schreiben abstürzt oder neu startet."""
    tmp = f"{path}.{secrets.token_hex(4)}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except OSError: pass
        raise

def load_stocks(d):       return _load_json(depot_file(d), [])
def save_stocks(d, s):    _save_json(depot_file(d), s)
def load_wl_stocks(d, w): return _load_json(watchlist_file(d, w), [])
def save_wl_stocks(d,w,s):_save_json(watchlist_file(d, w), s)
def load_depots():        return _load_json(DEPOTS_FILE, [])
def save_depots(d):       _save_json(DEPOTS_FILE, d)
def load_notifications(): return _load_json(NOTIF_FILE, [])
def load_snapshots():     return _load_json(SNAPSHOTS_FILE, [])
def save_snapshots(s):    _save_json(SNAPSHOTS_FILE, s)

# ── User helpers ──────────────────────────────────────────────────
def hash_pin(pin):
    if not pin: return None
    return hashlib.sha256(str(pin).encode()).hexdigest()

def load_users():  return _load_json(USERS_FILE, [])
def save_users(u): _save_json(USERS_FILE, u)

def get_depot_user(depot_id):
    for u in load_users():
        if depot_id in u.get("depots", []):
            return u
    return None

def resolve_notification_settings(depot_id):
    """Liefert (urls, mention, confirm) für ein Depot. Da jedes Depot immer genau
    einem Benutzer gehört (Benutzer sind jetzt Pflicht), kommen diese Werte
    ausschließlich vom zugeordneten User — kein Depot-Fallback mehr nötig.
    Die leeren Defaults greifen nur defensiv falls ein Depot wider Erwarten
    keinem Benutzer zugeordnet ist."""
    user = get_depot_user(depot_id)
    if not user:
        return [], "", False
    return (user.get("apprise_urls", []),
            user.get("notification_mention", ""),
            user.get("notification_confirm", False))

def load_settings():
    """Einstellungen mit Priorität: settings.json > _CFG_DEF"""
    s = {
        "refresh_interval":      _CFG_DEF["refresh_interval_seconds"],
        "notifications_enabled": True,
        "digest_enabled":        False,
        "digest_day":            6,
        "digest_time":           "18:00",
        "verlauf_retention_days": 60,
        "timezone":              _CFG_DEF["timezone"],
        "trading":               {
            "days":         list(_CFG_DEF["trading"]["days"]),
            "start_hour":   _CFG_DEF["trading"]["start_hour"],
            "start_minute": _CFG_DEF["trading"].get("start_minute", 0),
            "end_hour":     _CFG_DEF["trading"]["end_hour"],
            "end_minute":   _CFG_DEF["trading"].get("end_minute", 0),
        },
    }
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        for key in ("notifications_enabled", "refresh_interval", "timezone", "next_refresh_ts",
                    "verlauf_retention_days", "digest_enabled", "digest_day", "digest_time"):
            if key in saved: s[key] = saved[key]
        if "trading" in saved:
            s["trading"].update(saved["trading"])
    s.pop("apprise_urls", None)
    return s

def save_settings(s):     _save_json(SETTINGS_FILE, s)

def save_notifications(n): _save_json(NOTIF_FILE, n[-100:])

def add_log(etype, title, body, success=True, depot_id=None):
    n = load_notifications()
    entry = {"time": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
             "type": etype, "title": title, "body": body, "success": success}
    if depot_id:
        entry["depot_id"] = depot_id
        user = get_depot_user(depot_id)
        if user:
            entry["user_id"]   = user["id"]
            entry["user_name"] = user.get("name", "")
    n.append(entry)
    save_notifications(n)

def get_depot(depot_id):
    """Hilfsfunktion: Gibt Depot-Dict zurück oder None."""
    return next((d for d in load_depots() if d["id"] == depot_id), None)

def get_depot_or_404(depot_id):
    """Hilfsfunktion: Gibt Depot zurück oder Flask 404-Response als Tupel (None, response)."""
    depot = get_depot(depot_id)
    if not depot:
        return None, ({"error": "Depot nicht gefunden"}, 404)
    return depot, None

def gen_id(name):
    return f"{re.sub(r'[^a-z0-9]', '_', name.lower())[:20].strip('_')}_{int(time_mod.time())}"

# ── Migration ─────────────────────────────────────────────────────
def reset_pin_from_env():
    """Setzt den PIN eines Users zurück wenn RESET_PIN_USER gesetzt ist."""
    reset_name = os.environ.get("RESET_PIN_USER", "").strip()
    if not reset_name: return
    users = load_users()
    for u in users:
        if u.get("name", "").lower() == reset_name.lower():
            u["pin_hash"] = None
            save_users(users)
            log.info(f"PIN für User '{u['name']}' via RESET_PIN_USER zurückgesetzt")
            return
    log.warning(f"RESET_PIN_USER: User '{reset_name}' nicht gefunden")

def delete_user_from_env():
    """Löscht einen User (und seine exklusiven Depots) wenn DELETE_USER gesetzt ist."""
    del_name = os.environ.get("DELETE_USER", "").strip()
    if not del_name: return
    users   = load_users()
    target  = next((u for u in users if u.get("name","").lower() == del_name.lower()), None)
    if not target:
        log.warning(f"DELETE_USER: User '{del_name}' nicht gefunden"); return
    target_depots = set(target.get("depots", []))
    remaining_users = [u for u in users if u["id"] != target["id"]]
    # Depots die anderen Usern gehören — nicht löschen
    shared = {did for u in remaining_users for did in u.get("depots", [])}
    exclusive = target_depots - shared
    # Exklusive Depots löschen
    depots = load_depots()
    for did in exclusive:
        depot = next((d for d in depots if d["id"] == did), None)
        if not depot: continue
        for f in [depot_file(did)] + [watchlist_file(did, wl["id"]) for wl in depot.get("watchlists", [])]:
            if os.path.exists(f): os.remove(f)
        log.info(f"Depot '{depot.get('name', did)}' gelöscht (war exklusiv für '{target['name']}')")
    save_depots([d for d in depots if d["id"] not in exclusive])
    if not remaining_users:
        log.error("DELETE_USER: Abgebrochen — würde alle Benutzer löschen. Mindestens ein Benutzer muss verbleiben.")
        return
    save_users(remaining_users)
    log.info(f"User '{target['name']}' via DELETE_USER gelöscht ({len(exclusive)} Depot(s) entfernt)")

def migrate_if_needed():
    """Stellt sicher dass splits.json existiert. Alle Datenmigration bereits abgeschlossen."""
    if not os.path.exists(SPLITS_FILE):
        load_splits()

# ── Discount / Notification logic ─────────────────────────────────
def get_block(d):            return 0 if d < 20 else int(d / 10) * 10
def initial_block(cur, ath): return 0 if ath <= 0 else get_block((ath - cur) / ath * 100)

def build_alert_html(title, stock, label, new_cur, new_ath, d, cb, lp, buy_budget=None,
                      multiplier=1, is_nachkauf=False, is_sector_gap=False):
    """Baut eine HTML-Version des ATH-Alarms für E-Mail-Versand (analog zum Wochenbericht)."""
    nk_badge = ('<span style="display:inline-block;padding:2px 8px;background:#fef3c7;'
                'color:#92400e;border-radius:4px;font-size:11px;font-weight:600;margin-left:6px">'
                '🛒 Nachkauf-Kandidat</span>') if is_nachkauf else ""
    gap_badge = ('<span style="display:inline-block;padding:2px 8px;background:#e0e7ff;'
                 'color:#3730a3;border-radius:4px;font-size:11px;font-weight:600;margin-left:6px">'
                 '⚖️ Sektor unterrepräsentiert</span>') if is_sector_gap else ""

    buy_html = ""
    if buy_budget:
        qty = calc_buy_quantity(buy_budget, multiplier, new_cur)
        if qty:
            eff_budget = buy_budget * multiplier
            cost       = round(qty * new_cur, 2)
            buy_html = (f'<tr><td style="padding:4px 8px;color:#64748b">Kaufempfehlung</td>'
                        f'<td style="padding:4px 8px;font-weight:600;color:#22c55e">'
                        f'{qty} Stk. (~{cost:.2f} € / Budget {multiplier}×{buy_budget:.0f}={eff_budget:.0f} €)</td></tr>')

    link_html = (f'<p style="margin-top:20px"><a href="{APP_URL}" style="color:#6366f1">'
                 f'→ DepotRadar öffnen</a></p>') if APP_URL else ""

    return f"""<!DOCTYPE html><html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#1e293b">
    <div style="background:#ef4444;color:#fff;padding:16px 20px;border-radius:10px 10px 0 0">
      <h2 style="margin:0;font-size:18px">🔔 ATH-Alarm — {label}</h2>
      <div style="opacity:.85;font-size:13px;margin-top:4px">-{cb}%-Block erreicht</div>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:20px;border-radius:0 0 10px 10px">
      <h3 style="margin:0 0 4px">{stock['name']} <span style="color:#94a3b8;font-weight:400;font-size:13px">({stock['ticker']})</span>{nk_badge}{gap_badge}</h3>
      <table style="width:100%;border-collapse:collapse;margin-top:12px">
        <tr><td style="padding:4px 8px;color:#64748b">Aktueller Kurs</td><td style="padding:4px 8px;font-weight:600">{new_cur:.2f} €</td></tr>
        <tr style="background:#f9fafb"><td style="padding:4px 8px;color:#64748b">ATH</td><td style="padding:4px 8px;font-weight:600">{new_ath:.2f} €</td></tr>
        <tr><td style="padding:4px 8px;color:#64748b">Abstand</td><td style="padding:4px 8px;font-weight:600;color:#ef4444">-{d:.1f}%</td></tr>
        <tr style="background:#f9fafb"><td style="padding:4px 8px;color:#64748b">-{cb}%-Level bei</td><td style="padding:4px 8px;font-weight:600">{lp:.2f} €</td></tr>
        {buy_html}
        <tr><td style="padding:4px 8px;color:#64748b">Kursstand</td><td style="padding:4px 8px;color:#94a3b8;font-size:12px">{stock.get('market_time', '—')}</td></tr>
      </table>
      {link_html}
    </div>
    <p style="font-size:11px;color:#94a3b8;text-align:center;margin-top:12px">Gesendet von DepotRadar</p>
    </body></html>"""

def check_and_notify(stock, new_cur, new_ath, label="", urls=None, buy_budget=None, is_nachkauf=False, mention="", confirm=False, depot_id=None, is_sector_gap=False):
    if new_ath <= 0: return stock.get("last_notified_block", 0)
    d  = (new_ath - new_cur) / new_ath * 100
    cb = get_block(d)
    lb = stock.get("last_notified_block", cb)
    confirm_mode = confirm
    pending_key  = f"pending_notify_{cb}"
    # Existiert ein ausstehendes Flag für ein Level <= cb? (z.B. -20% pending, jetzt -33%)
    has_pending  = any(stock.get(f"pending_notify_{lvl}") for lvl in [20, 30, 40, 50, 60] if lvl <= cb)
    if cb > lb and cb >= 20:
        if confirm_mode and not has_pending:
            # Erst-Unterschreitung: Flag setzen, Verlauf-Eintrag, noch nicht senden
            stock[pending_key] = True
            pct_dist = round((new_ath - new_cur) / new_ath * 100, 1)
            add_log("pending_notify",
                    f"[{label}]: {stock['name']} (-{cb}%-Level)",
                    f"Kurs: {new_cur:.2f} EUR | ATH: {new_ath:.2f} EUR | Abstand: -{pct_dist}%\nBest\u00e4tigung beim n\u00e4chsten Refresh erwartet.",
                    success=True, depot_id=depot_id)
            return lb  # last_notified_block noch nicht erhöhen
        lp         = round(new_ath * (1 - cb / 100), 2)
        link       = f"\n\n{APP_URL}" if APP_URL else ""
        multiplier = 3 if cb >= 60 else (2 if cb >= 40 else 1)
        nk_icon    = "🛒 " if is_nachkauf else ""
        gap_icon   = "⚖️ " if is_sector_gap else ""
        title      = f"ATH-Alarm [{label}]: {nk_icon}{gap_icon}{stock['name']} -{cb}%-Block"
        # Kaufempfehlung wenn Budget definiert
        buy_line = ""
        if buy_budget:
            qty = calc_buy_quantity(buy_budget, multiplier, new_cur)
            if qty:
                eff_budget = buy_budget * multiplier
                cost       = round(qty * new_cur, 2)
                buy_line   = (f"\nKaufempfehlung:  {qty} Stk. "
                              f"(~{cost:.2f} EUR / Budget {multiplier}×{buy_budget:.0f}={eff_budget:.0f} EUR)")
        nk_line  = "\n🛒 Nachkauf-Kandidat" if is_nachkauf else ""
        gap_line = "\n⚖️ Sektor unterrepräsentiert" if is_sector_gap else ""
        body = (f"{stock['name']} ({stock['ticker']}) — {label}{nk_line}{gap_line}\n\n"
                f"Aktueller Kurs:  {new_cur:.2f} EUR\n"
                f"ATH:             {new_ath:.2f} EUR\n"
                f"Abstand:         -{d:.1f}%{buy_line}\n"
                f"-{cb}%-Level:    {lp:.2f} EUR\n"
                f"Kursstand:       {stock.get('market_time', '—')}{link}")
        html_body = build_alert_html(title, stock, label, new_cur, new_ath, d, cb, lp,
                                      buy_budget=buy_budget, multiplier=multiplier, is_nachkauf=is_nachkauf,
                                      is_sector_gap=is_sector_gap)
        send_apprise(title, body, urls or [], mention=mention, html_body=html_body, depot_id=depot_id)
        # Bestätigung abgeschlossen — alle Flags <= cb löschen + Verlauf-Eintrag
        cleared = [lvl for lvl in [20, 30, 40, 50, 60] if lvl <= cb and stock.pop(f"pending_notify_{lvl}", None)]
        if cleared:
            pct_dist = round(d, 1)
            skipped  = [lvl for lvl in cleared if lvl != cb]
            skip_note = (f"\n(Übersprungene Level ohne separate Meldung: "
                         f"{', '.join(f'-{l}%' for l in skipped)})") if skipped else ""
            add_log("pending_confirmed",
                    f"[{label}]: {stock['name']} (-{cb}%-Level)",
                    f"Kurs: {new_cur:.2f} EUR | ATH: {new_ath:.2f} EUR | Abstand: -{pct_dist}%\n"
                    f"Benachrichtigung wurde gesendet.{skip_note}",
                    success=True, depot_id=depot_id)
        return cb
    elif cb < lb:
        # Kurs hat sich erholt — alle pending flags löschen
        cancelled = [lvl for lvl in [20, 30, 40, 50, 60] if stock.pop(f"pending_notify_{lvl}", None)]
        if cancelled:
            lvl_str = ", ".join(f"-{lvl}%" for lvl in cancelled)
            add_log("pending_notify",
                    f"↩ Bestätigung abgebrochen [{label}]: {stock['name']}",
                    f"Kurs hat sich erholt — ausstehende Level ({lvl_str}) wurden nicht bestätigt.\n"
                    f"Kurs: {new_cur:.2f} EUR | ATH: {new_ath:.2f} EUR",
                    success=True, depot_id=depot_id)
        return cb
    # Ausstehende Flags für Level oberhalb des aktuellen cb bereinigen
    for lvl in [20, 30, 40, 50, 60]:
        if lvl > cb:
            stock.pop(f"pending_notify_{lvl}", None)
    return lb

# ── Yahoo Finance ─────────────────────────────────────────────────
YH = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

def get_eur_rate(currency):
    """Gibt EUR-Umrechnungskurs zurück. Normalisiert GBp → GBP automatisch."""
    if currency == "EUR": return 1.0
    if currency == "GBp": currency = "GBP"
    try:
        r = requests.get(f"https://api.frankfurter.app/latest?from={currency}&to=EUR", timeout=8)
        return float(r.json()["rates"]["EUR"])
    except:
        return {"USD":0.92,"GBP":1.17,"CHF":1.05,"JPY":0.0062,
                "CAD":0.68,"AUD":0.60,"DKK":0.134,"HKD":0.118}.get(currency, 0.92)

SECTOR_MAP = {
    # Industrie (spezifisch) → hat Vorrang
    "Semiconductors":                   "🔬 Halbleiter",
    "Semiconductor Equipment & Materials": "🔬 Halbleiter",
    "Biotechnology":                    "🧬 Biotech",
    "Drug Manufacturers—General":       "🏥 Gesundheit",
    "Drug Manufacturers—Specialty & Generic": "🏥 Gesundheit",
    "Pharmaceuticals":                  "🏥 Gesundheit",
    "Auto Manufacturers":               "🚗 Automobil",
    "Auto Parts":                       "🚗 Automobil",
    "Aerospace & Defense":              "🛡️ Rüstung & Sicherheit",
    "REIT":                             "🏠 Immobilien",
    "Real Estate":                      "🏠 Immobilien",
    "Exchange Traded Fund":             "🌐 ETF / Fonds",
    "Asset Management":                 "🏦 Finanzen",
    "Banks—Diversified":                "🏦 Finanzen",
    "Banks—Regional":                   "🏦 Finanzen",
    "Insurance—Life":                   "🏦 Finanzen",
    "Insurance—Diversified":            "🏦 Finanzen",
    # Sektor (Fallback)
    "Technology":                       "💻 Technologie",
    "Healthcare":                       "🏥 Gesundheit",
    "Financial Services":               "🏦 Finanzen",
    "Financial":                        "🏦 Finanzen",
    "Consumer Cyclical":                "🛒 Konsum (zyklisch)",
    "Consumer Defensive":               "🧴 Konsum (defensiv)",
    "Energy":                           "⚡ Energie",
    "Communication Services":           "📡 Kommunikation",
    "Industrials":                      "🏭 Industrie",
    "Basic Materials":                  "⛏️ Rohstoffe",
    "Utilities":                        "💡 Versorger",
}

def fetch_sector_from_yahoo(ticker):
    """Holt Sektor über Yahoo Finance Search-API — kein Crumb nötig."""
    candidates = [ticker]
    if "." in ticker:
        candidates.append(ticker.rsplit(".", 1)[0])
    for t in candidates:
        try:
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={urlquote(t)}&quotesCount=5&newsCount=0"
            r   = requests.get(url, headers=YH, timeout=10)
            r.raise_for_status()
            quotes = r.json().get("quotes", [])
            # Exakten Ticker-Match bevorzugen, sonst ersten Equity-Eintrag nehmen
            match = next((q for q in quotes if q.get("symbol","").upper() == t.upper()), None)
            if not match:
                match = next((q for q in quotes if q.get("quoteType") == "EQUITY"), None)
            if not match:
                continue
            industry = match.get("industry", "")
            sector   = match.get("sector",   "")
            log.info(f"Sektor-Fetch {t}: industry='{industry}' sector='{sector}'")
            for key in [industry, sector]:
                if key and key in SECTOR_MAP:
                    return SECTOR_MAP[key]
            if industry or sector:
                log.info(f"Kein Mapping für '{industry}'/'{sector}' ({t}) — bitte SECTOR_MAP ergänzen")
                return None
        except Exception as e:
            log.info(f"Sektor-Fetch {t}: {e}")
    return None

def fetch_stock_data(ticker):
    enc  = urlquote(ticker)
    urls = [
        f"https://query2.finance.yahoo.com/v8/finance/chart/{enc}?range=10y&interval=1mo&includePrePost=false",
        f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?range=10y&interval=1mo&includePrePost=false",
        f"https://query2.finance.yahoo.com/v8/finance/chart/{enc}?range=5y&interval=1mo",
    ]
    data, last_err = None, "Unbekannter Fehler"
    for url in urls:
        try:
            r = requests.get(url, headers=YH, timeout=15); r.raise_for_status()
            j = r.json()
            if j.get("chart", {}).get("result"): data = j; break
        except Exception as e: last_err = str(e)
    if not data:
        if '404' in last_err:
            raise ValueError(f"Ticker '{ticker}' bei Yahoo Finance nicht gefunden")
        raise ValueError("Yahoo Finance nicht erreichbar (Timeout oder Fehler)")

    result   = data["chart"]["result"][0]; meta = result["meta"]
    currency = meta.get("currency", "USD")
    current  = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
    if not current: raise ValueError("Kein aktueller Kurs")

    q0         = (result.get("indicators", {}).get("quote") or [{}])[0]
    timestamps = result.get("timestamp") or []
    highs      = [h for h in (q0.get("high")  or []) if h and h > 0]
    closes     = [c for c in (q0.get("close") or []) if c and c > 0]
    if not highs and not closes: raise ValueError("Keine historischen Kurse")
    all_prices = highs + closes
    ath        = max(all_prices)
    # ATH-Datum ermitteln — Index des Maximalwerts in rohen Daten suchen
    ath_date  = None
    raw_high  = q0.get("high")  or []
    raw_close = q0.get("close") or []
    try:
        for raw_arr in [raw_high, raw_close]:
            if not raw_arr or not timestamps: continue
            valid = [(i, v) for i, v in enumerate(raw_arr) if v and v > 0]
            if not valid: continue
            best_i, best_v = max(valid, key=lambda x: x[1])
            if abs(best_v - ath) < 0.01 and best_i < len(timestamps):
                ath_date = datetime.fromtimestamp(timestamps[best_i], tz=pytz.UTC).strftime("%d.%m.%Y")
                break
    except Exception as _e:
        log.debug(f"ATH-Datum nicht ermittelbar: {_e}")

    # GBp (Pence) → GBP normalisieren
    if currency == "GBp":
        current  = float(current) / 100
        ath      = float(ath)     / 100
        currency = "GBP"

    eur     = get_eur_rate(currency)
    cur_eur = round(float(current) * eur, 2)
    ath_eur = round(max(float(ath), float(current)) * eur, 2)
    mt_str  = None
    mt      = meta.get("regularMarketTime")
    if mt:
        try:
            tz     = pytz.timezone(load_settings().get("timezone", "Europe/Berlin"))
            mt_str = datetime.fromtimestamp(int(mt), tz=tz).strftime("%d.%m.%Y %H:%M")
        except: pass

    perfs = fetch_performance(ticker, cur_eur, eur, currency)
    return {"current_eur": cur_eur, "ath_eur": ath_eur, "ath_date": ath_date, "currency": currency,
            "market_time": mt_str, **perfs}

def fetch_performance(ticker, current_eur, eur_rate, currency="USD"):
    """Berechnet 1T/1W/1M/3M/1J/3J Performance. perf_1w wird nur noch intern für die
    Wochenzusammenfassung ("Beste/schlechteste Woche") berechnet, ist aber kein
    Badge mehr im Frontend (siehe perfWrap in index.html). Behandelt GBp korrekt."""
    try:
        enc = urlquote(ticker)
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{enc}?range=5y&interval=1d&includePrePost=false"
        r   = requests.get(url, headers=YH, timeout=10); r.raise_for_status()
        res = r.json()["chart"]["result"][0]
        # GBp-Kurse auf GBP normalisieren (sonst 100x zu hoch)
        chart_currency = res.get("meta", {}).get("currency", "")
        divisor        = 100.0 if chart_currency == "GBp" else 1.0
        tss    = res.get("timestamp", [])
        closes = res["indicators"]["quote"][0].get("close", [])
        now    = time_mod.time()
        targets = {
            "perf_1d": now -   1 * 86400,
            "perf_1w": now -   7 * 86400,
            "perf_1m": now -  30 * 86400,
            "perf_3m": now -  90 * 86400,
            "perf_1y": now - 365 * 86400,
            "perf_3y": now - 3 * 365 * 86400,
        }
        result = {}
        for key, target_ts in targets.items():
            best, min_diff = None, float("inf")
            for ts, price in zip(tss, closes):
                if ts and price and price > 0 and ts < now - 3600:
                    diff = abs(ts - target_ts)
                    if diff < min_diff:
                        min_diff = diff
                        best     = float(price) / divisor * eur_rate
            result[key] = round((current_eur - best) / best * 100, 1) if best else None
        return result
    except Exception as e:
        log.warning(f"Performance {ticker}: {e}")
        return {"perf_1d": None, "perf_1w": None, "perf_1m": None, "perf_3m": None, "perf_1y": None, "perf_3y": None}

# ── Apprise ───────────────────────────────────────────────────────
EMAIL_PREFIXES = ("mailto://", "mailtos://", "sendgrid://", "sparkpost://", "postmark://", "ses://")

def _is_email_url(u):
    return u.lower().startswith(EMAIL_PREFIXES)

def send_apprise(title, body, urls, mention="", html_body=None, depot_id=None):
    if not urls: return False
    try:
        ok = True
        for u in urls:
            ap = apprise_lib.Apprise()
            ap.add(u)
            is_discord = u.lower().startswith("discord")
            msg = f"{mention}\n{body}" if (mention and is_discord) else body
            if html_body and _is_email_url(u):
                if not ap.notify(title=title, body=html_body,
                                 body_format=apprise_lib.NotifyFormat.HTML):
                    ok = False
            else:
                if not ap.notify(title=title, body=msg):
                    ok = False
        add_log("alert", title, body, ok, depot_id=depot_id)
        return ok
    except Exception as e:
        log.error(f"Apprise: {e}")
        add_log("alert", title, body, False, depot_id=depot_id)
        return False

# ── Stock helpers ─────────────────────────────────────────────────
def _make_stock(data, old=None):
    """
    Erstellt einen aktualisierten Stock-Dict aus frischen Yahoo-Daten.
    Parqet-Felder (isin, buy_price_eur, shares) und user-Felder werden explizit erhalten.
    """
    base = old or {}
    return {
        **base,
        "current_eur":   data["current_eur"],
        "ath_eur":       max(data["ath_eur"], base.get("ath_eur", 0)),
        "currency":      data["currency"],
        "market_time":   data.get("market_time"),
        "perf_1d":       data.get("perf_1d"),
        "perf_1w":       data.get("perf_1w"),
        "perf_1m":       data.get("perf_1m"),
        "perf_3m":       data.get("perf_3m"),
        "perf_1y":       data.get("perf_1y"),
        "perf_3y":       data.get("perf_3y"),
        # Parqet-Felder explizit beibehalten (nicht durch **base überschreiben lassen)
        "isin":          base.get("isin"),
        "buy_price_eur": base.get("buy_price_eur"),
        "shares":        base.get("shares"),
        "updated":       datetime.now().strftime("%d.%m.%Y %H:%M"),
        "ath_date":      data.get("ath_date") if data.get("ath_eur",0) >= base.get("ath_eur",0) else (base.get("ath_date") or data.get("ath_date")),
    }

def _fetch_prices(stocks):
    """Phase 1: Kurse holen und Stocks aktualisieren — noch keine Benachrichtigungen.
    Sammelt nebenbei Aktien, die in diesem Durchlauf ein NEUES ATH erreicht haben
    UND dafür den ATH-Alarm aktiviert haben (ath_alert_enabled)."""
    ok_list, err_list, ath_hits = [], [], []
    for i, s in enumerate(stocks):
        try:
            old_ath   = float(s.get("ath_eur") or 0)
            data      = fetch_stock_data(s["ticker"])
            stocks[i] = _make_stock(data, s)
            new_ath   = float(stocks[i].get("ath_eur") or 0)
            # old_ath > 0 verhindert einen Fehlalarm beim allerersten Refresh
            # einer neu hinzugefügten Aktie (da hätte sie ja noch gar kein
            # "bisheriges" ATH zum Vergleich)
            if stocks[i].get("ath_alert_enabled") and old_ath > 0 and new_ath > old_ath + 0.001:
                ath_hits.append({**stocks[i], "_prev_ath": old_ath})
            # Sektor auto-holen wenn noch nicht gesetzt
            if not stocks[i].get("sector"):
                sec = fetch_sector_from_yahoo(s["ticker"])
                if sec:
                    stocks[i]["sector"] = sec
                    log.info(f"Sektor gesetzt: {s['name']} → {sec}")
            ok_list.append(s["name"])
        except Exception as e:
            log.error(f"{s['name']}: {e}")
            err_list.append(f"{s['name']}: {e}")
    return stocks, ok_list, err_list, ath_hits

def build_ath_reached_html(stock, prev_ath):
    """HTML-Version der Neues-ATH-Benachrichtigung, im Stil der anderen Alarm-Mails
    (analog build_alert_html), aber positiv/grün statt rot."""
    link_html = (f'<p style="margin-top:20px"><a href="{APP_URL}" style="color:#6366f1">'
                 f'→ DepotRadar öffnen</a></p>') if APP_URL else ""
    return f"""<!DOCTYPE html><html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#1e293b">
    <div style="background:#22c55e;color:#fff;padding:16px 20px;border-radius:10px 10px 0 0">
      <h2 style="margin:0;font-size:18px">🎉 Neues Allzeithoch</h2>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:20px;border-radius:0 0 10px 10px">
      <h3 style="margin:0 0 4px">{stock['name']} <span style="color:#94a3b8;font-weight:400;font-size:13px">({stock['ticker']})</span></h3>
      <table style="width:100%;border-collapse:collapse;margin-top:12px">
        <tr><td style="padding:4px 8px;color:#64748b">Neues ATH</td><td style="padding:4px 8px;font-weight:600;color:#22c55e">{stock['ath_eur']:.2f} €</td></tr>
        <tr style="background:#f9fafb"><td style="padding:4px 8px;color:#64748b">Bisheriges ATH</td><td style="padding:4px 8px;font-weight:600">{prev_ath:.2f} €</td></tr>
        <tr><td style="padding:4px 8px;color:#64748b">Kursstand</td><td style="padding:4px 8px;color:#94a3b8;font-size:12px">{stock.get('market_time', '—')}</td></tr>
      </table>
      {link_html}
    </div>
    <p style="font-size:11px;color:#94a3b8;text-align:center;margin-top:12px">Gesendet von DepotRadar</p>
    </body></html>"""

def send_ath_alerts(hits, label, urls, mention="", depot_id=None):
    """Sendet für jede Aktie in hits (neues ATH + ath_alert_enabled) eine eigene
    Benachrichtigung. Anders als die Discount-Alarme braucht das keinen
    Bestätigungsmodus — ein neues ATH ist ein eindeutiges, einmaliges Ereignis."""
    if not urls: return
    for s in hits:
        prev_ath = s.get("_prev_ath", 0)
        title = f"🎉 Neues ATH — {s['name']}"
        body  = (f"{s['name']} ({s['ticker']}) — {label}\n\n"
                 f"Neues ATH:      {s['ath_eur']:.2f} EUR\n"
                 f"Bisheriges ATH: {prev_ath:.2f} EUR\n"
                 f"Kursstand:      {s.get('market_time', '—')}")
        html_body = build_ath_reached_html(s, prev_ath)
        try:
            send_apprise(title, body, urls, mention=mention, html_body=html_body, depot_id=depot_id)
        except Exception as e:
            log.error(f"ATH-Alarm {s.get('name','?')}: {e}")


def _send_notifications(stocks, label, urls, buy_budget, nachkauf_set, sector_gap_set=None, mention="", confirm=False, depot_id=None):
    """Phase 2: Benachrichtigungen auslösen nachdem alle Kurse bekannt sind."""
    sector_gap_set = sector_gap_set or set()
    for i, s in enumerate(stocks):
        try:
            is_nk   = s["ticker"] in nachkauf_set
            is_gap  = s["ticker"] in sector_gap_set
            new_blk = check_and_notify(
                s, s["current_eur"], s["ath_eur"],
                label, urls, buy_budget, is_nk, mention, confirm=confirm, depot_id=depot_id, is_sector_gap=is_gap
            )
            stocks[i]["last_notified_block"] = new_blk
        except Exception as e:
            log.error(f"Notify {s.get('name','?')}: {e}")
    return stocks

def _refresh_depot(depot, trigger="auto"):
    did       = depot["id"]; dname = depot["name"]
    urls, mention, confirm = resolve_notification_settings(did)
    budget    = depot.get("buy_budget") or None
    raw_t = depot.get("nachkauf_threshold"); threshold = int(raw_t) if raw_t is not None else 30

    # ── Phase 1: Alle Kurse holen ─────────────────────────────────
    stocks = load_stocks(did)
    stocks, ok, err, ath_hits = _fetch_prices(stocks)

    # Watchlist-Preise holen
    wl_data = {}
    for wl in depot.get("watchlists", []):
        wls, wok, werr, wl_ath_hits = _fetch_prices(load_wl_stocks(did, wl["id"]))
        wl_data[wl["id"]] = (wl, wls, wok, werr, wl_ath_hits)
        ok += wok; err += werr

    # Nachkauf-Sets berechnen
    nachkauf_set = calc_nachkauf_set(stocks, threshold)
    wl_nachkauf  = {wl_id: calc_nachkauf_set(wls, threshold)
                    for wl_id, (_, wls, _, _, _) in wl_data.items()}

    # Sektor-Lücke berechnen — Basis ist immer der echte Bestand, auch für Watchlists
    # (eine Watchlist-Aktie kann eine Lücke im Bestand füllen, auch wenn ihr Sektor
    # innerhalb der Watchlist selbst nicht knapp ist)
    sector_gap_set = calc_sector_gap_set(stocks)
    wl_sector_gap  = {wl_id: calc_sector_gap_set(stocks, wls)
                      for wl_id, (_, wls, _, _, _) in wl_data.items()}

    # Benachrichtigungen — nur wenn für dieses Depot aktiviert
    if depot.get("notifications_enabled", True):
        stocks = _send_notifications(stocks, f"Bestand: {dname}", urls, budget, nachkauf_set,
                                      sector_gap_set, mention, confirm, depot_id=did)
        send_ath_alerts(ath_hits, f"Bestand: {dname}", urls, mention, depot_id=did)
        for wl_id, (wl, wls, _, _, wl_ath_hits) in wl_data.items():
            wls = _send_notifications(wls, f"Beobachtung: {wl['name']} ({dname})",
                                      urls, budget, wl_nachkauf[wl_id], wl_sector_gap[wl_id],
                                      mention, confirm, depot_id=did)
            send_ath_alerts(wl_ath_hits, f"Beobachtung: {wl['name']} ({dname})", urls, mention, depot_id=did)
            save_wl_stocks(did, wl_id, wls)
    else:
        for wl_id, (wl, wls, _, _, _) in wl_data.items():
            save_wl_stocks(did, wl_id, wls)

    save_stocks(did, stocks)
    return ok, err

def take_snapshot():
    """Erstellt einen täglichen Portfolio-Snapshot (einmal pro Tag beim Auto-Refresh)."""
    today = datetime.now().strftime("%Y-%m-%d")
    snaps = load_snapshots()
    if any(s["date"] == today for s in snaps):
        return  # Heute bereits gespeichert
    depots   = load_depots()
    entry    = {"date": today, "depots": {}}
    has_data = False
    for dc in depots:
        stocks    = load_stocks(dc["id"])
        total_val = 0.0; total_cost = 0.0
        for s in stocks:
            if s.get("current_eur") and s.get("shares"):
                total_val  += s["current_eur"] * s["shares"]
                if s.get("buy_price_eur"):
                    total_cost += s["buy_price_eur"] * s["shares"]
        if total_val > 0:
            entry["depots"][dc["id"]] = {
                "name":  dc["name"],
                "value": round(total_val, 2),
                "cost":  round(total_cost, 2) if total_cost else None,
            }
            has_data = True
    if has_data:
        snaps.append(entry)
        # Max. 5 Jahre aufbewahren
        cutoff = (datetime.now() - timedelta(days=1825)).strftime("%Y-%m-%d")
        snaps  = [s for s in snaps if s["date"] >= cutoff]
        save_snapshots(snaps)
        log.info(f"Portfolio-Snapshot erstellt: {today}")

def refresh_all_depots(trigger="auto"):
    depots = load_depots(); total_ok, total_err = [], []
    for depot in depots:
        ok, err = _refresh_depot(depot, trigger)
        total_ok += ok; total_err += err
    label = "Automatisch" if trigger == "auto" else "Manuell"
    add_log(f"{trigger}_refresh", f"{label}er Refresh",
            f"Depots: {len(depots)} | OK: {len(total_ok)} | Fehler: {len(total_err)}",
            len(total_err) == 0)
    if trigger == "auto":
        take_snapshot()

# ── Scheduler ─────────────────────────────────────────────────────
scheduler = BackgroundScheduler(daemon=True)
_last_refresh = None; _start_of_day_done = None

def _restore_last_refresh():
    """Liest next_refresh_ts aus settings.json und setzt _last_refresh so dass der
    geplante nächste Refresh korrekt eingehalten wird — auch nach Neustart."""
    global _last_refresh
    try:
        raw      = _load_json(SETTINGS_FILE, {})
        next_ts  = raw.get("next_refresh_ts")
        interval = raw.get("refresh_interval", 3600)
        tz       = pytz.timezone(raw.get("timezone", "Europe/Berlin"))
        now_dt   = datetime.now(tz)
        # Migration: falls next_refresh_ts fehlt, aus last_refresh_ts berechnen
        if not next_ts and raw.get("last_refresh_ts"):
            next_ts = float(raw["last_refresh_ts"]) + interval
            log.info("Migration: next_refresh_ts aus last_refresh_ts berechnet")
        if next_ts:
            next_dt = datetime.fromtimestamp(float(next_ts), tz)
            if next_dt > now_dt:
                # Nächster Refresh liegt in der Zukunft — darauf warten
                _last_refresh = next_dt - timedelta(seconds=interval)
                log.info(f"Nächster Refresh geplant: {next_dt.strftime('%d.%m.%Y %H:%M')}")
            else:
                # Nächster Refresh verpasst — sofort nachholen
                _last_refresh = None
                log.info(f"Geplanter Refresh ({next_dt.strftime('%H:%M')}) verpasst — wird sofort nachgeholt")
        else:
            log.info("Kein gespeicherter Refresh-Zeitpunkt — warte volles Intervall")
    except Exception as e:
        log.warning(f"Konnte Refresh-Zeitpunkt nicht wiederherstellen: {e}")

def cleanup_old_logs():
    """Entfernt Verlauf-Einträge die älter als konfigurierte Tage sind."""
    try:
        s        = load_settings()
        days     = s.get("verlauf_retention_days", 60)
        tz       = pytz.timezone(s.get("timezone", "Europe/Berlin"))
        cutoff   = datetime.now(tz) - timedelta(days=days)
        notifs   = load_notifications()
        before   = len(notifs)

        def is_fresh(n):
            t = n.get("time", "")  # Feld heißt "time" nicht "timestamp"
            if not t: return True
            try:
                entry_dt = tz.localize(datetime.strptime(t, "%d.%m.%Y %H:%M:%S"))
                return entry_dt >= cutoff
            except Exception:
                return True  # bei Parse-Fehler behalten

        notifs  = [n for n in notifs if is_fresh(n)]
        removed = before - len(notifs)
        if removed > 0:
            save_notifications(notifs)
            log.info(f"Verlauf bereinigt: {removed} Einträge älter als {days} Tage entfernt")
    except Exception as e:
        log.warning(f"Verlauf-Bereinigung fehlgeschlagen: {e}")

def trading_window_check():
    global _last_refresh, _start_of_day_done
    s        = load_settings(); tz = pytz.timezone(s["timezone"]); now = datetime.now(tz)
    interval = s["refresh_interval"]
    t = s["trading"]; days = t.get("days", [0,1,2,3,4])
    sh = t.get("start_hour", 8);  sm = t.get("start_minute", 0)
    eh = t.get("end_hour", 23);   em = t.get("end_minute", 0)
    now_mins = now.hour * 60 + now.minute
    start_mins = sh * 60 + sm; end_mins = eh * 60 + em
    if now.weekday() not in days or now_mins < start_mins or now_mins > end_mins: return
    today = now.date()
    if now.hour == sh and now.minute == sm and _start_of_day_done != today:
        _start_of_day_done = today; _last_refresh = now.replace(second=0, microsecond=0); s["next_refresh_ts"] = (_last_refresh + timedelta(seconds=interval)).timestamp(); save_settings(s); cleanup_old_logs(); refresh_all_depots("auto"); return
    if _last_refresh is None or (now - _last_refresh).total_seconds() >= interval:
        _last_refresh = now.replace(second=0, microsecond=0)  # auf volle Minute abrunden → kein Drift
        s["next_refresh_ts"] = (_last_refresh + timedelta(seconds=interval)).timestamp(); save_settings(s)
        refresh_all_depots("auto")

def get_next_run_info():
    s        = load_settings(); tz = pytz.timezone(s["timezone"]); now = datetime.now(tz)
    interval = s["refresh_interval"]
    t = s["trading"]; days = t.get("days", [0,1,2,3,4])
    sh = t.get("start_hour", 8);  sm = t.get("start_minute", 0)
    eh = t.get("end_hour", 23);   em = t.get("end_minute", 0)
    start_mins = sh * 60 + sm; end_mins = eh * 60 + em
    if _last_refresh:
        c = _last_refresh + timedelta(seconds=interval)
        c_mins = c.hour * 60 + c.minute
        if c_mins > end_mins or c.weekday() not in days:
            d = c.date()
            for _ in range(1, 8):
                d += timedelta(days=1)
                if d.weekday() in days:
                    return tz.localize(datetime(d.year, d.month, d.day, sh, sm)).strftime("%d.%m.%Y %H:%M") + " Uhr"
        if c_mins < start_mins:
            c = tz.localize(datetime(c.year, c.month, c.day, sh, sm))
        return c.strftime("%d.%m.%Y %H:%M") + " Uhr"
    # Kein letzter Refresh bekannt — falls wir gerade in der Handelszeit sind,
    # now als Referenz nehmen damit das Intervall korrekt berechnet wird
    ref = now
    now_mins = now.hour * 60 + now.minute
    d = now.date()
    for i in range(0, 8):
        check = d if i == 0 else d + timedelta(days=i)
        if check.weekday() in days:
            if i == 0 and start_mins <= now_mins <= end_mins:
                # Mitten in der Handelszeit: Intervall ab jetzt
                c = ref + timedelta(seconds=interval)
                return c.strftime("%d.%m.%Y %H:%M") + " Uhr"
            if i == 0 and now_mins < start_mins:
                return tz.localize(datetime(check.year, check.month, check.day, sh, sm)).strftime("%d.%m.%Y %H:%M") + " Uhr"
            elif i > 0:
                return tz.localize(datetime(check.year, check.month, check.day, sh, sm)).strftime("%d.%m.%Y %H:%M") + " Uhr"
    return "unbekannt"

def build_digest_body(depot, stocks):
    """Baut den Digest-Text für ein Depot."""
    name   = depot.get("name", "Depot")
    total  = len(stocks)
    if total == 0:
        return None, None

    now       = datetime.now()
    kw        = now.isocalendar()[1]
    title     = f"📊 DepotRadar Wochenbericht — KW {kw}"

    # ATH-Verteilung
    buckets = {"<20": [], "20-39": [], "40-59": [], ">60": []}
    for s in stocks:
        cur = s.get("current_eur"); ath = s.get("ath_eur")
        if not cur or not ath or ath == 0: continue
        d = (ath - cur) / ath * 100
        if   d < 20: buckets["<20"].append(s)
        elif d < 40: buckets["20-39"].append(s)
        elif d < 60: buckets["40-59"].append(s)
        else:        buckets[">60"].append(s)

    dist = (f"  < 20% unter ATH:  {len(buckets['<20'])} Aktie(n) ✅\n"
            f"  20–39%:           {len(buckets['20-39'])} Aktie(n) 🟡\n"
            f"  40–59%:           {len(buckets['40-59'])} Aktie(n) 🟠\n"
            f"  ≥60%:             {len(buckets['>60'])} Aktie(n) 🔴")

    # Nachkauf-Kandidaten
    threshold = int(depot.get("nachkauf_threshold") or 30)
    nk_set    = calc_nachkauf_set(stocks, threshold)
    nk_lines  = ""
    if nk_set:
        budget = depot.get("buy_budget")
        lines  = []
        for s in stocks:
            if s.get("ticker") not in nk_set: continue
            cur = s.get("current_eur"); ath = s.get("ath_eur")
            if not cur or not ath or ath == 0: continue
            d   = (ath - cur) / ath * 100
            mul = 3 if d >= 60 else (2 if d >= 40 else 1)
            qty_str = ""
            if budget:
                qty = calc_buy_quantity(budget, mul, cur)
                if qty:
                    cost = round(qty * cur, 2)
                    qty_str = f" — {qty} Stk. · ~{cost:.0f} €"
            lines.append(f"  {s['name']} (-{d:.1f}%){qty_str}")
        if lines:
            nk_lines = "\n\n🛒 Nachkauf-Kandidaten:\n" + "\n".join(lines)

    # Beste/schlechteste Woche
    perf_stocks = [(s, s.get("perf_1w")) for s in stocks if s.get("perf_1w") is not None]
    perf_section = ""
    if perf_stocks:
        best  = max(perf_stocks, key=lambda x: x[1])
        worst = min(perf_stocks, key=lambda x: x[1])
        perf_section = (f"\n\n📈 Beste Woche:    {best[0]['name']} {best[1]:+.1f}%"
                        f"\n📉 Schlechteste:  {worst[0]['name']} {worst[1]:+.1f}%")

    # Nah am nächsten Level (< 3% Puffer)
    near_lines = []
    for s in stocks:
        cur = s.get("current_eur"); ath = s.get("ath_eur")
        if not cur or not ath or ath == 0: continue
        d  = (ath - cur) / ath * 100
        lb = s.get("last_notified_block", 0)
        for lvl in [20, 30, 40, 50, 60]:
            if lvl > lb:
                next_price = round(ath * (1 - lvl / 100), 2)
                gap        = (cur - next_price) / cur * 100
                if 0 < gap < 3:
                    near_lines.append(f"  {s['name']} -{d:.1f}% (→ -{lvl}%-Block bei {next_price:.2f} €)")
                break
    near_section = ""
    if near_lines:
        near_section = "\n\n⚠️ Nah am nächsten Level:\n" + "\n".join(near_lines)

    # Sektor-Verteilung
    sector_section = ""
    sector_counts = {}
    for s in stocks:
        sec = s.get("sector")
        if sec:
            sector_counts[sec] = sector_counts.get(sec, 0) + 1
    if sector_counts:
        parts = " · ".join(f"{k} {v}" for k, v in sorted(sector_counts.items(), key=lambda x: -x[1]))
        sector_section = f"\n\n📂 Sektoren: {parts}"

    link    = f"\n\n{APP_URL}" if APP_URL else ""
    body = (f"Depot: {name} ({total} Aktien)\n\n"
            f"📊 Verteilung:\n{dist}"
            f"{nk_lines}"
            f"{perf_section}"
            f"{near_section}"
            f"{sector_section}"
            f"{link}")
    return title, body


def build_digest_html(depot, stocks, kw):
    """Baut eine HTML-Version des Digests für E-Mail-Versand."""
    name  = depot.get("name", "Depot")
    total = len(stocks)

    # Verteilung
    b = {"<20": 0, "20-39": 0, "40-59": 0, ">60": 0}
    for s in stocks:
        cur = s.get("current_eur"); ath = s.get("ath_eur")
        if not cur or not ath or ath == 0: continue
        d = (ath - cur) / ath * 100
        if   d < 20: b["<20"]   += 1
        elif d < 40: b["20-39"] += 1
        elif d < 60: b["40-59"] += 1
        else:        b[">60"]   += 1

    dist_html = f"""
    <table style="width:100%;border-collapse:collapse;margin-top:8px">
      <tr><td style="padding:4px 8px">✅ &lt; 20% unter ATH</td><td style="padding:4px 8px;font-weight:600;color:#22c55e">{b['<20']}</td></tr>
      <tr style="background:#f9fafb"><td style="padding:4px 8px">🟡 20–39%</td><td style="padding:4px 8px;font-weight:600;color:#eab308">{b['20-39']}</td></tr>
      <tr><td style="padding:4px 8px">🟠 40–59%</td><td style="padding:4px 8px;font-weight:600;color:#f97316">{b['40-59']}</td></tr>
      <tr style="background:#f9fafb"><td style="padding:4px 8px">🔴 ≥60%</td><td style="padding:4px 8px;font-weight:600;color:#ef4444">{b['>60']}</td></tr>
    </table>"""

    # Nachkauf-Kandidaten
    threshold = int(depot.get("nachkauf_threshold") or 30)
    nk_set    = calc_nachkauf_set(stocks, threshold)
    nk_html   = ""
    if nk_set:
        budget = depot.get("buy_budget")
        rows   = []
        for s in stocks:
            if s.get("ticker") not in nk_set: continue
            cur = s.get("current_eur"); ath = s.get("ath_eur")
            if not cur or not ath or ath == 0: continue
            d   = (ath - cur) / ath * 100
            mul = 3 if d >= 60 else (2 if d >= 40 else 1)
            qty_str = ""
            if budget:
                qty = calc_buy_quantity(budget, mul, cur)
                if qty:
                    qty_str = f" &nbsp;→&nbsp; {qty} Stk. · ~{qty*cur:.0f} €"
            rows.append(f"<tr><td style='padding:4px 8px'>{s['name']}</td>"
                        f"<td style='padding:4px 8px;color:#f97316'>-{d:.1f}%</td>"
                        f"<td style='padding:4px 8px;color:#22c55e'>{qty_str}</td></tr>")
        if rows:
            nk_html = f"""<h3 style="color:#f97316;margin:20px 0 8px">🛒 Nachkauf-Kandidaten</h3>
            <table style="width:100%;border-collapse:collapse">{''.join(rows)}</table>"""

    # Performance
    perf_stocks = [(s, s.get("perf_1w")) for s in stocks if s.get("perf_1w") is not None]
    perf_html   = ""
    if perf_stocks:
        best  = max(perf_stocks, key=lambda x: x[1])
        worst = min(perf_stocks, key=lambda x: x[1])
        perf_html = f"""<h3 style="margin:20px 0 8px">📈 Wochenperformance</h3>
        <table style="width:100%;border-collapse:collapse">
          <tr><td style="padding:4px 8px">📈 Beste</td><td style="padding:4px 8px;font-weight:600">{best[0]['name']}</td><td style="padding:4px 8px;color:#22c55e">{best[1]:+.1f}%</td></tr>
          <tr style="background:#f9fafb"><td style="padding:4px 8px">📉 Schlechteste</td><td style="padding:4px 8px;font-weight:600">{worst[0]['name']}</td><td style="padding:4px 8px;color:#ef4444">{worst[1]:+.1f}%</td></tr>
        </table>"""

    # Nah am Level
    near_rows = []
    for s in stocks:
        cur = s.get("current_eur"); ath = s.get("ath_eur")
        if not cur or not ath or ath == 0: continue
        d  = (ath - cur) / ath * 100
        lb = s.get("last_notified_block", 0)
        for lvl in [20, 30, 40, 50, 60]:
            if lvl > lb:
                next_price = round(ath * (1 - lvl / 100), 2)
                gap        = (cur - next_price) / cur * 100
                if 0 < gap < 3:
                    near_rows.append(f"<tr><td style='padding:4px 8px'>{s['name']}</td>"
                                     f"<td style='padding:4px 8px;color:#f97316'>-{d:.1f}%</td>"
                                     f"<td style='padding:4px 8px;color:#94a3b8'>→ -{lvl}%-Block bei {next_price:.2f} €</td></tr>")
                break
    near_html = ""
    if near_rows:
        near_html = f"""<h3 style="color:#f59e0b;margin:20px 0 8px">⚠️ Nah am nächsten Level</h3>
        <table style="width:100%;border-collapse:collapse">{''.join(near_rows)}</table>"""

    # Sektoren
    sector_counts = {}
    for s in stocks:
        sec = s.get("sector")
        if sec: sector_counts[sec] = sector_counts.get(sec, 0) + 1
    sector_html = ""
    if sector_counts:
        chips = " ".join(f"<span style='display:inline-block;padding:3px 8px;background:#f1f5f9;border-radius:4px;font-size:12px;margin:2px'>{k} {v}</span>"
                         for k, v in sorted(sector_counts.items(), key=lambda x: -x[1]))
        sector_html = f"""<h3 style="margin:20px 0 8px">📂 Sektoren</h3><div>{chips}</div>"""

    link_html = f'<p style="margin-top:20px"><a href="{APP_URL}" style="color:#6366f1">→ DepotRadar öffnen</a></p>' if APP_URL else ""

    return f"""<!DOCTYPE html><html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#1e293b">
    <div style="background:#6366f1;color:#fff;padding:16px 20px;border-radius:10px 10px 0 0">
      <h2 style="margin:0;font-size:18px">📊 DepotRadar Wochenbericht — KW {kw}</h2>
      <div style="opacity:.8;font-size:13px;margin-top:4px">Depot: {name} · {total} Aktien</div>
    </div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-top:none;padding:20px;border-radius:0 0 10px 10px">
      <h3 style="margin:0 0 8px">📊 ATH-Verteilung</h3>
      {dist_html}
      {nk_html}
      {perf_html}
      {near_html}
      {sector_html}
      {link_html}
    </div>
    <p style="font-size:11px;color:#94a3b8;text-align:center;margin-top:12px">Gesendet von DepotRadar</p>
    </body></html>"""


def send_weekly_digests():
    """Sendet den Wochenbericht an alle Depots die es aktiviert haben."""
    s = load_settings()
    if not s.get("digest_enabled", False): return
    log.info("Wöchentlicher Digest wird versendet…")
    depots = load_depots()
    kw     = datetime.now().isocalendar()[1]
    for dc in depots:
        if not dc.get("weekly_digest", False): continue
        did = dc["id"]
        urls, mention, _confirm = resolve_notification_settings(did)
        if not urls: continue
        stocks  = load_stocks(did)
        title, body = build_digest_body(dc, stocks)
        if title:
            html_body = build_digest_html(dc, stocks, kw)
            add_log("digest", f"📊 Wochenbericht [{dc['name']}]",
                    f"Gesendet an {len(urls)} URL(s).", success=True, depot_id=dc['id'])
            send_apprise(title, body, urls, mention=mention, html_body=html_body, depot_id=dc['id'])


def schedule_digest_job():
    """Plant den Digest-Job anhand der aktuellen Einstellungen."""
    s        = load_settings()
    tz       = pytz.timezone(s.get("timezone", "Europe/Berlin"))
    enabled  = s.get("digest_enabled", False)
    day      = int(s.get("digest_day", 6))          # 0=Mo … 6=So
    t        = s.get("digest_time", "18:00")
    try:
        hour, minute = map(int, t.split(":"))
    except Exception:
        hour, minute = 18, 0
    # APScheduler day_of_week: 0=Mon … 6=Sun
    dow_map  = {0:"mon",1:"tue",2:"wed",3:"thu",4:"fri",5:"sat",6:"sun"}
    scheduler.add_job(
        send_weekly_digests, CronTrigger(
            day_of_week=dow_map[day], hour=hour, minute=minute, timezone=tz),
        id="weekly_digest", replace_existing=True, misfire_grace_time=None)
    log.info(f"Digest-Job geplant: {dow_map[day]} {hour:02d}:{minute:02d} ({'aktiv' if enabled else 'inaktiv — Job läuft, prüft intern'})")


def start_scheduler():
    _restore_last_refresh()
    scheduler.add_job(trading_window_check, "cron", minute="*", id="trading_check",
                      replace_existing=True, misfire_grace_time=None)
    schedule_digest_job()
    if not scheduler.running: scheduler.start()
    log.info("Scheduler gestartet")

# ── Parqet OAuth (PKCE) ───────────────────────────────────────────
_oauth_states = {}

def calc_nachkauf_set(stocks, threshold=30):
    """
    Berechnet welche Aktien Nachkauf-Kandidaten sind:
    ≥20% unter ATH UND in den unteren threshold% nach Positionswert.
    threshold=0 bedeutet deaktiviert → leeres Set.
    Gibt ein Set von Tickern zurück.
    """
    if not threshold:
        return set()
    with_val = [s for s in stocks
                if s.get("buy_price_eur") and s.get("shares") and s.get("current_eur", 0) > 0]
    if len(with_val) < 2:
        return set()
    values   = sorted(s["current_eur"] * s["shares"] for s in with_val)
    cutoff_i = max(0, math.ceil(len(values) * threshold / 100) - 1)
    cutoff   = values[cutoff_i]
    result   = set()
    for s in with_val:
        pos_val  = s["current_eur"] * s["shares"]
        discount = (s["ath_eur"] - s["current_eur"]) / s["ath_eur"] * 100 if s.get("ath_eur", 0) > 0 else 0
        if discount >= 20 and pos_val <= cutoff:
            result.add(s["ticker"])
    return result

def calc_sector_gap_set(basis_stocks, target_stocks=None, factor=0.5):
    """
    Diversifikations-Lücke: ermittelt anhand von basis_stocks (immer der tatsächliche
    Bestand, nie eine Watchlist) welche Sektoren unterrepräsentiert sind, und gibt die
    Ticker aus target_stocks zurück, deren Sektor betroffen ist. Ohne target_stocks wird
    das Ergebnis auf basis_stocks selbst angewendet (für den Bestand gegen sich selbst).
    So kann z.B. eine Watchlist-Aktie als Lücken-Kandidat markiert werden, auch wenn der
    Sektor in der Watchlist selbst gar nicht knapp ist — entscheidend ist immer der
    echte Bestand.
    Ein Sektor gilt als unterrepräsentiert wenn seine Positionsanzahl im Bestand unter
    factor (Standard 50%) des Durchschnitts liegt. Aktien ohne Sektor werden bei der
    Durchschnittsberechnung ignoriert. Gibt ein Set von Tickern zurück.
    """
    target  = target_stocks if target_stocks is not None else basis_stocks
    sectors = [s.get("sector") for s in basis_stocks if s.get("sector")]
    if len(sectors) < 2:
        return set()
    counts    = Counter(sectors)
    avg       = len(sectors) / len(counts)
    underrep  = {sec for sec, cnt in counts.items() if cnt < avg * factor}
    if not underrep:
        return set()
    return {s["ticker"] for s in target if s.get("sector") in underrep}

def calc_buy_quantity(budget, multiplier, price):
    """
    Berechnet empfohlene Kaufmenge basierend auf Budget × Multiplikator.
    Erlaubt genau +1 Aktie wenn diese noch innerhalb von 120% des Budgets liegt.
    Gibt None zurück wenn kein Budget definiert oder Preis 0.
    """
    if not budget or not price or price <= 0:
        return None
    effective = budget * multiplier
    qty = int(effective / price)          # floor
    if qty < 1:
        return None
    if (qty + 1) * price <= effective * 1.2:
        qty += 1
    return qty

def get_client_id(depot):
    """Gibt die Parqet Client ID des Depots zurück."""
    return depot.get("parqet_client_id", "").strip()

def pkce_verifier():   return secrets.token_urlsafe(64)
def pkce_challenge(v): return base64.urlsafe_b64encode(hashlib.sha256(v.encode("ascii")).digest()).rstrip(b"=").decode("ascii")

def _try_refresh_token(depot_id, pq):
    rt = pq.get("refresh_token")
    if not rt: return None
    depots2   = load_depots()
    depot2    = next((d for d in depots2 if d["id"] == depot_id), {})
    client_id = get_client_id(depot2)
    if not client_id: return None
    try:
        r = requests.post(PARQET_TOKEN_URL,
                          data={"grant_type":"refresh_token","refresh_token":rt,"client_id":client_id},
                          timeout=15)
        r.raise_for_status(); tokens = r.json()
        new_pq = {**pq, "access_token": tokens["access_token"],
                  "refresh_token": tokens.get("refresh_token", rt),
                  "expires_at": int(time_mod.time()) + tokens.get("expires_in", 3600)}
        depots = load_depots()
        for d in depots:
            if d["id"] == depot_id: d["parqet"] = new_pq; break
        save_depots(depots); log.info(f"Parqet Token erneuert: {depot_id}"); return new_pq
    except Exception as e:
        log.error(f"Token Refresh fehlgeschlagen: {e}"); return None

def parqet_api_get(depot, path, depot_id=None):
    pq    = depot.get("parqet", {}); token = pq.get("access_token", "")
    if not token: raise ValueError("Nicht mit Parqet verbunden")
    r = requests.get(f"{PARQET_API_BASE}{path}",
                     headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                     timeout=15)
    if r.status_code == 401 and depot_id:
        log.warning(f"Parqet 401 — Token-Refresh für {depot_id}")
        new_pq = _try_refresh_token(depot_id, pq)
        if new_pq:
            r = requests.get(f"{PARQET_API_BASE}{path}",
                             headers={"Authorization": f"Bearer {new_pq['access_token']}", "Accept": "application/json"},
                             timeout=15)
    r.raise_for_status(); return r.json()

# ── Parqet Split-Berechnung ───────────────────────────────────────
def _split_adj(isin, buy_dt_str, raw_shares):
    """Splitbereinigte Stückzahl: multipliziert Käufe VOR dem Split-Datum mit dem Faktor."""
    adjusted = raw_shares
    buy_date = buy_dt_str[:10]
    for split_date, ratio in splits_as_dict().get(isin, []):
        if buy_date < split_date:
            adjusted *= ratio
    return adjusted

def _names_match(n1, n2):
    """Strenger Namens-Abgleich: erstes signifikantes Wort muss übereinstimmen.
    Punkte werden zu Leerzeichen, generische Suffixe (Inc, Corp, SE...) werden ignoriert.
    Verhindert False-Matches z.B. PayPal vs SAP SE."""
    GENERIC = {"corp", "inc", "ltd", "llc", "plc", "holding", "holdings",
               "group", "company", "international", "global"}
    clean = lambda n: re.sub(r"[^a-z0-9 ]", " ", n.lower())  # Sonderzeichen → Leerzeichen
    sig   = lambda n: [w for w in clean(n).split() if len(w) >= 4 and w not in GENERIC]
    w1, w2 = sig(n1), sig(n2)
    if not w1 or not w2: return False   # kein signifikantes Wort → kein Match
    return w1[0] == w2[0]               # erstes signifikantes Wort muss übereinstimmen

def calculate_holdings(activities):
    """
    Berechnet splitbereinigten Durchschnittspreis und Stückzahl aus Parqet-Aktivitäten.
    Formel: avg = Σ(tatsächlich gezahlter Betrag) ÷ Σ(splitbereinigte Stückzahl)
    Korrekt unabhängig davon ob vor, nach oder beidseitig des Splits gekauft wurde.
    """
    holdings = {}
    for a in sorted(activities, key=lambda a: a.get("datetime", "")):
        asset    = a.get("asset", {}); isin = asset.get("isin")
        if not isin: continue
        atype    = a.get("type", "")
        raw_shrs = float(a.get("shares") or 0)
        price    = float(a.get("price") or 0)
        curr     = a.get("currency", "EUR")
        eur      = get_eur_rate(curr)
        cost_eur = raw_shrs * price * eur
        buy_dt   = a.get("datetime", "")

        if isin not in holdings:
            holdings[isin] = {"isin": isin, "name": asset.get("name", ""),
                              "shares": 0.0, "total_cost": 0.0}
        h = holdings[isin]
        if not h["name"] and asset.get("name"): h["name"] = asset["name"]

        if atype in ("buy", "transfer_in"):
            adj           = _split_adj(isin, buy_dt, raw_shrs)
            h["shares"]     += adj
            h["total_cost"] += cost_eur
        elif atype in ("sell", "transfer_out") and h["shares"] > 0:
            adj        = min(_split_adj(isin, buy_dt, raw_shrs), h["shares"])
            proportion = adj / h["shares"]
            h["shares"]     = max(0, h["shares"] - adj)
            h["total_cost"] = max(0, h["total_cost"] * (1 - proportion))

    return {
        isin: {**h, "avg_price_eur": round(h["total_cost"] / h["shares"], 4)}
        for isin, h in holdings.items()
        if h["shares"] > 0.001
    }

# ── Parqet Routes ─────────────────────────────────────────────────
@app.route("/api/depots/<depot_id>/parqet/connect", methods=["POST"])
def parqet_connect(depot_id):
    depots = load_depots()
    depot  = next((d for d in depots if d["id"] == depot_id), None)
    if not depot: return jsonify({"error": "Depot nicht gefunden"}), 404
    client_id = get_client_id(depot)
    if not client_id:
        return jsonify({"error": "Keine Parqet Client ID hinterlegt — bitte zuerst in den Depot-Einstellungen eintragen"}), 400
    verifier  = pkce_verifier(); challenge = pkce_challenge(verifier)
    state     = secrets.token_urlsafe(16)
    _oauth_states[state] = {"depot_id": depot_id, "verifier": verifier,
                             "client_id": client_id, "ts": int(time_mod.time())}
    for k in [k for k,v in _oauth_states.items() if time_mod.time()-v.get("ts",0)>600]:
        _oauth_states.pop(k, None)
    callback = f"{APP_URL}/api/parqet/callback"
    auth_url = (f"{PARQET_AUTH_URL}?client_id={client_id}&response_type=code"
                f"&scope=portfolio%3Aread&redirect_uri={urlquote(callback)}"
                f"&code_challenge={challenge}&code_challenge_method=S256&state={state}")
    return jsonify({"auth_url": auth_url})

@app.route("/api/parqet/callback", methods=["GET"])
def parqet_callback():
    code  = request.args.get("code", ""); state = request.args.get("state", "")
    error = request.args.get("error", "")
    if error: return redirect(f"{APP_URL}?parqet_error={urlquote(error)}")
    entry = _oauth_states.pop(state, None)
    if not entry: return redirect(f"{APP_URL}?parqet_error=invalid_state")
    depot_id  = entry["depot_id"]; verifier = entry["verifier"]
    client_id = entry["client_id"]
    callback  = f"{APP_URL}/api/parqet/callback"
    try:
        r = requests.post(PARQET_TOKEN_URL,
                          data={"grant_type":"authorization_code","code":code,
                                "redirect_uri":callback,"client_id":client_id,
                                "code_verifier":verifier}, timeout=15)
        r.raise_for_status(); tokens = r.json()
    except Exception as e:
        log.error(f"Token Exchange: {e}")
        return redirect(f"{APP_URL}?parqet_error=token_exchange_failed")
    depots = load_depots()
    for d in depots:
        if d["id"] == depot_id:
            d["parqet"] = {"access_token": tokens["access_token"],
                           "refresh_token": tokens.get("refresh_token"),
                           "expires_at": int(time_mod.time()) + tokens.get("expires_in", 3600),
                           "portfolio_id": None, "connected": True, "last_sync": None}
            break
    save_depots(depots); log.info(f"Parqet verbunden: {depot_id}")
    return redirect(f"{APP_URL}?parqet_connected={depot_id}")

@app.route("/api/depots/<depot_id>/parqet/undo-sync", methods=["POST"])
def parqet_undo_sync(depot_id):
    """Stellt den Depot-Stand vor dem letzten Parqet-Sync wieder her."""
    bak = depot_backup_file(depot_id)
    if not os.path.exists(bak):
        return jsonify({"error": "Kein Backup vorhanden"}), 404
    shutil.copy2(bak, depot_file(depot_id))
    os.remove(bak)
    add_log("manual_refresh", "Sync rückgängig gemacht",
            f"Depot {depot_id} auf Stand vor letztem Sync zurückgesetzt", True, depot_id=depot_id)
    log.info(f"Parqet Sync rückgängig: {depot_id}")
    return jsonify({"ok": True})

@app.route("/api/depots/<depot_id>/parqet/disconnect", methods=["POST"])
def parqet_disconnect(depot_id):
    depots = load_depots()
    for d in depots:
        if d["id"] == depot_id: d.pop("parqet", None); break
    save_depots(depots); return jsonify({"ok": True})

@app.route("/api/depots/<depot_id>/parqet/reconnect", methods=["POST"])
def parqet_reconnect(depot_id):
    depots = load_depots()
    for d in depots:
        if d["id"] == depot_id and "parqet" in d: d["parqet"] = {"connected": False}; break
    save_depots(depots); return jsonify({"ok": True})

@app.route("/api/depots/<depot_id>/parqet/status", methods=["GET"])
def parqet_status(depot_id):
    depot = get_depot(depot_id)
    if not depot: return jsonify({"error": "Nicht gefunden"}), 404
    pq = depot.get("parqet", {})
    return jsonify({"connected": pq.get("connected", False), "portfolio_id": pq.get("portfolio_id"),
                    "last_sync": pq.get("last_sync"),
                    "has_client_id": bool(get_client_id(depot)),
                    "needs_reconnect": pq.get("needs_reconnect", False),
                    "has_backup": os.path.exists(depot_backup_file(depot_id)),
                    "backup_time": (
                        datetime.fromtimestamp(os.path.getmtime(depot_backup_file(depot_id)))
                        .strftime("%d.%m.%Y %H:%M")
                        if os.path.exists(depot_backup_file(depot_id)) else None
                    )})

@app.route("/api/depots/<depot_id>/parqet/portfolios", methods=["GET"])
def parqet_portfolios(depot_id):
    depot = get_depot(depot_id)
    if not depot or not depot.get("parqet", {}).get("connected"):
        return jsonify({"error": "Nicht verbunden"}), 400
    try:
        raw  = parqet_api_get(depot, "/portfolios", depot_id)
        pf   = (raw if isinstance(raw, list)
                else raw.get("portfolios") or raw.get("items") or raw.get("data")
                or raw.get("result") or raw.get("content") or raw.get("records")
                or ([raw] if "id" in raw else []))
        return jsonify(pf)
    except Exception as e:
        log.error(f"Parqet /portfolios Fehler: {e}")
        return jsonify({"error": str(e)}), 502

@app.route("/api/depots/<depot_id>/parqet/select-portfolio", methods=["POST"])
def parqet_select_portfolio(depot_id):
    pid = (request.get_json() or {}).get("portfolio_id", "")
    if not pid: return jsonify({"error": "portfolio_id erforderlich"}), 400
    depots = load_depots()
    for d in depots:
        if d["id"] == depot_id: d.setdefault("parqet", {})["portfolio_id"] = pid; break
    save_depots(depots); return jsonify({"ok": True})

@app.route("/api/depots/<depot_id>/parqet/sync", methods=["POST"])
def parqet_sync(depot_id):
    depots = load_depots()
    depot = next((d for d in depots if d["id"] == depot_id), None)
    if not depot or not depot.get("parqet", {}).get("connected"):
        return jsonify({"error": "Nicht verbunden"}), 400
    pq = depot["parqet"]; pid = pq.get("portfolio_id")
    if not pid: return jsonify({"error": "Kein Portfolio ausgewählt"}), 400

    def handle_401(e):
        d2 = load_depots()
        for d in d2:
            if d["id"] == depot_id and "parqet" in d: d["parqet"]["needs_reconnect"] = True; break
        save_depots(d2); return jsonify({"error": str(e), "needs_reconnect": True}), 401

    # 1) Holdings → ISIN-Map aufbauen
    try:
        hld = parqet_api_get(depot, f"/portfolios/{pid}/holdings", depot_id)
        pq_holdings = hld.get("items", []) if isinstance(hld, dict) else []
    except Exception as e:
        err = str(e)
        if "401" in err or "Unauthorized" in err: return handle_401(e)
        return jsonify({"error": f"Holdings-Fehler: {e}"}), 502

    isin_map = {ph.get("asset", {}).get("isin"): ph.get("asset", {}).get("name", "")
                for ph in pq_holdings if ph.get("asset", {}).get("isin")}

    # 2) Fehlende ISINs in Depot-Aktien ergänzen (strenger Namens-Abgleich)
    stocks = load_stocks(depot_id); enriched = 0
    for s in stocks:
        if s.get("isin"): continue
        for isin, pname in isin_map.items():
            if _names_match(s["name"], pname):
                s["isin"] = isin; enriched += 1
                log.info(f"ISIN ergänzt: '{s['name']}' → {isin} (via '{pname}')")
                break
    if enriched: save_stocks(depot_id, stocks); log.info(f"{enriched} ISINs ergänzt")

    # 3) Aktivitäten laden (paginiert)
    all_activities = []; cursor = None
    try:
        while True:
            url = (f"/portfolios/{pid}/activities"
                   f"?activityType=buy&activityType=sell"
                   f"&activityType=transfer_in&activityType=transfer_out"
                   f"&assetType=security&limit=500")
            if cursor: url += f"&cursor={cursor}"
            data   = parqet_api_get(depot, url, depot_id)
            acts   = data.get("activities", data) if isinstance(data, dict) else data
            if isinstance(acts, list): all_activities.extend(acts)
            cursor = data.get("nextCursor") if isinstance(data, dict) else None
            if not cursor: break
    except Exception as e:
        err = str(e)
        if "401" in err or "Unauthorized" in err: return handle_401(e)
        return jsonify({"error": f"Parqet API Fehler: {e}"}), 502

    log.info(f"Parqet Sync {depot['name']}: {len(all_activities)} Aktivitäten")

    # 4) Splitbereinigten Einstand berechnen und abgleichen
    holdings = calculate_holdings(all_activities)
    stocks   = load_stocks(depot_id)
    src = depot_file(depot_id); bak = depot_backup_file(depot_id)
    updated, new_stocks, mismatches = [], [], []

    for isin, h in holdings.items():
        match = next((s for s in stocks if s.get("isin") == isin), None)
        if match:
            # ISIN stimmt überein → direkt aktualisieren (kein Namens-Check nötig)
            new_price  = h["avg_price_eur"]
            new_shares = round(h["shares"], 6)
            # Nur als geändert markieren wenn sich Werte wirklich unterscheiden
            actually_changed = (
                round(match.get("buy_price_eur") or 0, 4) != round(new_price or 0, 4) or
                round(match.get("shares") or 0, 6) != new_shares
            )
            match["buy_price_eur"] = new_price
            match["shares"]        = new_shares
            match["isin"]          = isin
            if actually_changed:
                updated.append(match["name"])
                log.info(f"Sync GEÄNDERT: {match['name']} Einstand={new_price:.2f}€ Stk={new_shares:.4f}")
            else:
                log.debug(f"Sync unverändert: {match['name']}")
        else:
            new_stocks.append({"isin": isin, "name": h["name"],
                               "shares": round(h["shares"], 6), "buy_price_eur": h["avg_price_eur"]})

    # Backup nur wenn sich etwas ändert
    if (updated or new_stocks) and os.path.exists(src):
        shutil.copy2(src, bak)
    save_stocks(depot_id, stocks)
    for d in depots:
        if d["id"] == depot_id:
            d["parqet"]["last_sync"] = datetime.now().strftime("%d.%m.%Y %H:%M")
            d["parqet"].pop("needs_reconnect", None)
            break
    save_depots(depots)
    add_log("manual_refresh", f"Parqet Sync: {depot['name']}",
            f"Aktualisiert: {len(updated)} | Neu: {len(new_stocks)} | Konflikte: {len(mismatches)}", True, depot_id=depot_id)
    return jsonify({"ok": True, "updated": updated, "new_stocks": new_stocks, "mismatches": mismatches})

@app.route("/api/depots/<depot_id>/parqet/apply-mismatch", methods=["POST"])
def parqet_apply_mismatch(depot_id):
    body      = request.get_json() or {}
    isin      = body.get("isin", "")
    buy_price = float(body.get("buy_price_eur") or 0)
    shares    = float(body.get("shares") or 0)
    stocks    = load_stocks(depot_id)
    match     = next((s for s in stocks if s.get("isin") == isin), None)
    if not match: return jsonify({"error": "Nicht gefunden"}), 404
    match["buy_price_eur"] = buy_price; match["shares"] = round(shares, 6)
    save_stocks(depot_id, stocks); return jsonify({"ok": True})

@app.route("/api/depots/<depot_id>/parqet/import-bulk", methods=["POST"])
def parqet_import_bulk(depot_id):
    """Importiert mehrere neue Aktien in einem einzigen Schreibvorgang.
    Gibt Ergebnisse als Liste zurück — Index entspricht Input-Index."""
    items  = request.get_json()
    if not items: return jsonify({"error": "Keine Daten"}), 400
    stocks          = load_stocks(depot_id)
    # Backup vor Import anlegen (Import = immer Änderung)
    src = depot_file(depot_id); bak = depot_backup_file(depot_id)
    if os.path.exists(src): shutil.copy2(src, bak)
    existing_isins  = {s.get("isin","").upper() for s in stocks if s.get("isin")}
    existing_ticker = {s["ticker"].upper() for s in stocks}
    results = []
    for item in items:
        ticker = item.get("ticker","").strip()
        isin   = (item.get("isin") or "").strip().upper()
        # Duplikat-Check: ISIN oder Ticker bereits vorhanden
        if isin and isin in existing_isins:
            results.append({"ok": False, "skipped": True, "reason": "ISIN bereits im Depot"})
            continue
        if ticker.upper() in existing_ticker:
            # Ticker existiert — ISIN nachträglich ergänzen falls fehlend
            if isin:
                for s in stocks:
                    if s["ticker"].upper() == ticker.upper() and not s.get("isin"):
                        s["isin"] = item.get("isin","")
                        log.info(f"ISIN nachträglich gesetzt: {ticker} → {isin}")
                        break
            results.append({"ok": False, "skipped": True, "reason": "Ticker bereits im Depot"})
            continue
        if not ticker:
            results.append({"ok": False, "error": "Kein Ticker"})
            continue
        try:
            data  = fetch_stock_data(ticker)
            stock = _make_stock(data, {
                "ticker": ticker, "name": item.get("name",""), "exchange": item.get("exchange",""),
                "isin": item.get("isin",""), "buy_price_eur": item.get("buy_price_eur"),
                "shares": item.get("shares"), "last_notified_block": 0
            })
            stocks.append(stock)
            existing_ticker.add(ticker.upper())
            if isin: existing_isins.add(isin)
            results.append({"ok": True})
        except Exception as e:
            results.append({"ok": False, "error": str(e)})
    save_stocks(depot_id, stocks)
    return jsonify(results)

@app.route("/api/depots/<depot_id>/parqet/import", methods=["POST"])
def parqet_import_stock(depot_id):
    body      = request.get_json() or {}
    ticker    = body.get("ticker", "").strip().upper()
    name      = body.get("name", "").strip()
    exchange  = body.get("exchange", "").strip()
    isin      = body.get("isin", "").strip()
    buy_price = float(body.get("buy_price_eur") or 0)
    shares    = float(body.get("shares") or 0)
    if not ticker or not name: return jsonify({"error": "ticker und name erforderlich"}), 400
    stocks   = load_stocks(depot_id)
    existing = next((s for s in stocks if s["ticker"] == ticker), None)
    if existing:
        existing.update({"isin": isin, "buy_price_eur": buy_price, "shares": shares})
        save_stocks(depot_id, stocks)
        return jsonify({"ok": True, "action": "updated", "stock": existing})
    try: data = fetch_stock_data(ticker)
    except ValueError as e:
        msg = str(e)
        code = 404 if "nicht gefunden" in msg else 502
        return jsonify({"error": msg, "ticker_not_found": code == 404}), code
    except Exception as e: return jsonify({"error": str(e)}), 502
    stock = {**_make_stock(data), "name": name, "ticker": ticker, "exchange": exchange,
             "isin": isin, "buy_price_eur": buy_price, "shares": shares,
             "last_notified_block": initial_block(data["current_eur"], data["ath_eur"])}
    stocks.append(stock); save_stocks(depot_id, stocks)
    return jsonify({"ok": True, "action": "added", "stock": stock}), 201

@app.route("/api/depots/<depot_id>/parqet/debug", methods=["GET"])
def parqet_debug(depot_id):
    """Debug-Endpunkt: zeigt Aktivitätszahl, berechnete Holdings und ISINs im Depot."""
    depot = get_depot(depot_id)
    if not depot or not depot.get("parqet", {}).get("connected"):
        return jsonify({"error": "Nicht verbunden"}), 400
    pq = depot.get("parqet", {}); pid = pq.get("portfolio_id", ""); out = {}
    try:
        all_acts, cursor = [], None
        while True:
            url = (f"/portfolios/{pid}/activities?activityType=buy&activityType=sell"
                   f"&activityType=transfer_in&activityType=transfer_out&assetType=security&limit=500")
            if cursor: url += f"&cursor={cursor}"
            d2   = parqet_api_get(depot, url, depot_id)
            a2   = d2.get("activities", d2) if isinstance(d2, dict) else d2
            if isinstance(a2, list): all_acts.extend(a2)
            cursor = d2.get("nextCursor") if isinstance(d2, dict) else None
            if not cursor: break
        out["total_activities"] = len(all_acts)
        holdings = calculate_holdings(all_acts); out["holdings_count"] = len(holdings)
        for isin in [s["isin"] for s in load_splits()[:3]]:
            out[f"holding_{isin}"] = (
                {k: holdings[isin][k] for k in ("name","shares","avg_price_eur","total_cost")}
                if isin in holdings else "NOT IN ACTIVITIES"
            )
        stocks = load_stocks(depot_id)
        out["depot_isins"] = {s["ticker"]: s.get("isin", "MISSING") for s in stocks}
    except Exception as e:
        out["error"] = str(e)
    return jsonify(out)


# ── ATH-Prüfung ──────────────────────────────────────────────────
@app.route("/api/depots/<depot_id>/ath-check", methods=["GET"])
def ath_check(depot_id):
    """Vergleicht gespeicherte ATH-Werte mit aktuellen Yahoo-Daten."""
    stocks    = load_stocks(depot_id)
    threshold = float(request.args.get("threshold", 5)) / 100
    results   = []
    for s in stocks:
        try:
            data      = fetch_stock_data(s["ticker"])
            yahoo_ath = data["ath_eur"]
            stored    = s.get("ath_eur", 0)
            if stored <= 0:
                continue
            diff_pct = abs(yahoo_ath - stored) / stored
            if diff_pct > threshold:
                results.append({
                    "ticker":      s["ticker"],
                    "name":        s["name"],
                    "stored_ath":  round(stored, 2),
                    "yahoo_ath":   round(yahoo_ath, 2),
                    "diff_pct":    round(diff_pct * 100, 1),
                    "direction":   "lower" if yahoo_ath < stored else "higher"
                })
        except Exception as e:
            log.warning(f"ATH-Check {s['ticker']}: {e}")
    depots = load_depots()
    depot  = next((d for d in depots if d["id"] == depot_id), {})
    if results:
        add_log("manual_refresh",
                f"ATH-Prüfung: {depot.get('name', depot_id)}",
                f"{len(results)} Abweichung(en) gefunden — " +
                ", ".join(f"{r['name']}: {r['stored_ath']:.2f}→{r['yahoo_ath']:.2f} EUR ({r['direction']})" for r in results),
                True, depot_id=depot_id)
    else:
        add_log("manual_refresh",
                f"ATH-Prüfung: {depot.get('name', depot_id)}",
                "Alle ATH-Werte sind korrekt ✓", True, depot_id=depot_id)
    return jsonify(results)

@app.route("/api/depots/<depot_id>/ath-log", methods=["POST"])
def ath_log(depot_id):
    """Schreibt das Ergebnis einer ATH-Prüfung in den Verlauf."""
    data   = request.get_json() or {}
    depots = load_depots()
    depot  = next((d for d in depots if d["id"] == depot_id), {})
    count  = data.get("count", 0)
    items  = data.get("items", [])
    if count:
        body = f"{count} Abweichung(en) gefunden — " +                ", ".join(f"{r['name']}: {r['stored_ath']:.2f}→{r['yahoo_ath']:.2f} EUR" for r in items)
    else:
        body = "Alle ATH-Werte sind korrekt ✓"
    add_log("manual_refresh", f"ATH-Prüfung: {depot.get('name', depot_id)}", body, True, depot_id=depot_id)
    return jsonify({"ok": True})

@app.route("/api/ath-check-single", methods=["GET"])
def ath_check_single():
    """Gibt den aktuellen Yahoo-ATH für einen einzelnen Ticker zurück."""
    ticker = request.args.get("ticker", "").strip()
    if not ticker: return jsonify({"error": "ticker fehlt"}), 400
    try:
        data = fetch_stock_data(ticker)
        return jsonify({"ticker": ticker, "yahoo_ath": data["ath_eur"]})
    except Exception as e:
        return jsonify({"ticker": ticker, "error": str(e)}), 502

@app.route("/api/depots/<depot_id>/ath-correct", methods=["POST"])
def ath_correct(depot_id):
    """Übernimmt korrigierte ATH-Werte in die Depot-Datei."""
    corrections = request.get_json()  # [{ticker, new_ath}]
    if not corrections:
        return jsonify({"error": "Keine Korrekturen übergeben"}), 400
    stocks  = load_stocks(depot_id)
    depots  = load_depots()
    depot   = next((d for d in depots if d["id"] == depot_id), {})
    updated = []
    details = []
    for c in corrections:
        for s in stocks:
            if s["ticker"] == c["ticker"]:
                old_ath = s.get("ath_eur", 0)
                s["ath_eur"] = round(float(c["new_ath"]), 2)
                updated.append(s["ticker"])
                details.append(f"{s['name']}: {old_ath:.2f} → {s['ath_eur']:.2f} EUR")
                break
    save_stocks(depot_id, stocks)
    if updated:
        add_log("manual_refresh",
                f"ATH-Korrektur: {depot.get('name', depot_id)}",
                f"{len(updated)} Wert(e) korrigiert — " + ", ".join(details),
                True, depot_id=depot_id)
    return jsonify({"updated": updated})

# ── Splits CRUD ──────────────────────────────────────────────────
@app.route("/api/splits", methods=["GET"])
def get_splits():
    return jsonify(load_splits())

@app.route("/api/splits", methods=["POST"])
def add_split():
    body  = request.get_json()
    isin  = body.get("isin",  "").strip()
    name  = body.get("name",  "").strip()
    date  = body.get("date",  "").strip()
    ratio = body.get("ratio", 0)
    if not isin or not date or not ratio:
        return jsonify({"error": "isin, date und ratio erforderlich"}), 400
    splits = load_splits()
    # Duplikat prüfen
    if any(s["isin"] == isin and s["date"] == date for s in splits):
        return jsonify({"error": "Split bereits vorhanden"}), 409
    entry = {"isin": isin, "name": name, "date": date, "ratio": int(ratio)}
    splits.append(entry)
    splits.sort(key=lambda s: (s["date"], s["isin"]))
    _save_json(SPLITS_FILE, splits)
    return jsonify(entry), 201

@app.route("/api/splits/<isin>/<date>", methods=["DELETE"])
def delete_split(isin, date):
    splits = load_splits()
    new    = [s for s in splits if not (s["isin"] == isin and s["date"] == date)]
    if len(new) == len(splits):
        return jsonify({"error": "Nicht gefunden"}), 404
    _save_json(SPLITS_FILE, new)
    return jsonify({"ok": True})

@app.route("/api/splits/stocks-with-isin", methods=["GET"])
def splits_stocks_with_isin():
    """Gibt alle Aktien aus allen Depots und Watchlists zurück die eine ISIN haben."""
    result = {}  # isin → {name, ticker, isin}
    for depot in load_depots():
        did = depot["id"]
        for s in load_stocks(did):
            if s.get("isin"):
                result[s["isin"]] = {"name": s["name"], "ticker": s["ticker"], "isin": s["isin"]}
        for wl in depot.get("watchlists", []):
            for s in load_wl_stocks(did, wl["id"]):
                if s.get("isin"):
                    result[s["isin"]] = {"name": s["name"], "ticker": s["ticker"], "isin": s["isin"]}
    return jsonify(sorted(result.values(), key=lambda x: x["name"]))

# ── Depot CRUD ────────────────────────────────────────────────────
@app.route("/api/depots", methods=["GET"])
def get_depots(): return jsonify(load_depots())

@app.route("/api/depots", methods=["POST"])
def create_depot():
    body = request.get_json(); name = body.get("name", "").strip()
    if not name: return jsonify({"error": "Name erforderlich"}), 400
    depots = load_depots()
    if any(d["name"].lower() == name.lower() for d in depots):
        return jsonify({"error": "Name existiert bereits"}), 409
    did = gen_id(name); save_stocks(did, [])
    depot = {"id": did, "name": name, "watchlists": []}
    depots.append(depot); save_depots(depots)
    # Depot dem aktuellen User zuordnen
    user_id = body.get("user_id")
    if user_id:
        users = load_users()
        user  = next((u for u in users if u["id"] == user_id), None)
        if user:
            user.setdefault("depots", []).append(did)
            save_users(users)
    return jsonify(depot), 201

def clear_pending_flags(depot_id):
    """Entfernt alle pending_notify_*-Flags für ein Depot (Bestand + alle Watchlists).
    Wird beim Umschalten von notifications_enabled aufgerufen, damit ein Flag aus einer
    früheren Phase (z.B. vor dem Deaktivieren) nicht später fälschlich als 'jetzt gerade
    bestätigt' interpretiert wird."""
    PENDING_PREFIX = "pending_notify_"
    stocks = load_stocks(depot_id)
    changed = False
    for s in stocks:
        for key in [k for k in s if k.startswith(PENDING_PREFIX)]:
            del s[key]; changed = True
    if changed:
        save_stocks(depot_id, stocks)

    depots = load_depots()
    depot  = next((d for d in depots if d["id"] == depot_id), None)
    for wl in (depot.get("watchlists", []) if depot else []):
        wls = load_wl_stocks(depot_id, wl["id"])
        wl_changed = False
        for s in wls:
            for key in [k for k in s if k.startswith(PENDING_PREFIX)]:
                del s[key]; wl_changed = True
        if wl_changed:
            save_wl_stocks(depot_id, wl["id"], wls)

@app.route("/api/depots/<depot_id>", methods=["PUT"])
def update_depot(depot_id):
    body = request.get_json(); depots = load_depots()
    for d in depots:
        if d["id"] == depot_id:
            if "name" in body and body["name"].strip(): d["name"] = body["name"].strip()
            if "parqet_client_id" in body: d["parqet_client_id"] = body["parqet_client_id"].strip()
            if "buy_budget" in body:
                raw = body["buy_budget"]
                d["buy_budget"] = float(raw) if raw else None
            if "nachkauf_threshold" in body:
                raw = body["nachkauf_threshold"]
                d["nachkauf_threshold"] = max(0, min(50, int(raw))) if raw is not None else 30
            if "weekly_digest" in body:
                d["weekly_digest"] = bool(body["weekly_digest"])
            notif_toggled = False
            if "notifications_enabled" in body:
                old_enabled = d.get("notifications_enabled", True)
                new_enabled = bool(body["notifications_enabled"])
                if old_enabled != new_enabled:
                    notif_toggled = True
                d["notifications_enabled"] = new_enabled
            save_depots(depots)
            if notif_toggled:
                # Tatsächlicher Wechsel (an↔aus) — alte Pending-Flags verwerfen,
                # damit keine veraltete "Bestätigung" beim nächsten Refresh entsteht
                clear_pending_flags(depot_id)
                log.info(f"notifications_enabled für Depot {depot_id} geändert auf {d['notifications_enabled']} — Pending-Flags zurückgesetzt")
            return jsonify(d)
    return jsonify({"error": "Nicht gefunden"}), 404

@app.route("/api/depots/<depot_id>", methods=["DELETE"])
def delete_depot(depot_id):
    depots = load_depots()
    if len(depots) <= 1: return jsonify({"error": "Letztes Depot kann nicht gelöscht werden"}), 400
    depot = next((d for d in depots if d["id"] == depot_id), None)
    if not depot: return jsonify({"error": "Nicht gefunden"}), 404
    for f in [depot_file(depot_id)] + [watchlist_file(depot_id, wl["id"]) for wl in depot.get("watchlists", [])]:
        if os.path.exists(f): os.remove(f)
    save_depots([d for d in depots if d["id"] != depot_id])
    # Aus users.json entfernen
    users = load_users()
    changed = False
    for u in users:
        if depot_id in u.get("depots", []):
            u["depots"].remove(depot_id); changed = True
    if changed: save_users(users)
    return jsonify({"ok": True})

# ── Watchlist CRUD ────────────────────────────────────────────────
@app.route("/api/depots/<depot_id>/watchlists", methods=["POST"])
def create_watchlist(depot_id):
    body = request.get_json(); name = body.get("name", "").strip()
    if not name: return jsonify({"error": "Name erforderlich"}), 400
    depots = load_depots()
    depot = next((d for d in depots if d["id"] == depot_id), None)  # aus GLEICHER Liste!
    if not depot: return jsonify({"error": "Depot nicht gefunden"}), 404
    if any(w["name"].lower() == name.lower() for w in depot.get("watchlists", [])):
        return jsonify({"error": "Name existiert bereits"}), 409
    wl_id = gen_id(name); save_wl_stocks(depot_id, wl_id, [])
    wl = {"id": wl_id, "name": name}
    depot.setdefault("watchlists", []).append(wl); save_depots(depots); return jsonify(wl), 201

@app.route("/api/depots/<depot_id>/watchlists/<wl_id>", methods=["PUT"])
def update_watchlist(depot_id, wl_id):
    body = request.get_json(); depots = load_depots()
    depot = next((d for d in depots if d["id"] == depot_id), None)
    if not depot: return jsonify({"error": "Nicht gefunden"}), 404
    for wl in depot.get("watchlists", []):
        if wl["id"] == wl_id:
            if "name" in body and body["name"].strip(): wl["name"] = body["name"].strip()
            save_depots(depots); return jsonify(wl)
    return jsonify({"error": "Nicht gefunden"}), 404

@app.route("/api/depots/<depot_id>/watchlists/<wl_id>", methods=["DELETE"])
def delete_watchlist(depot_id, wl_id):
    depots = load_depots()
    depot = next((d for d in depots if d["id"] == depot_id), None)
    if not depot: return jsonify({"error": "Nicht gefunden"}), 404
    f = watchlist_file(depot_id, wl_id)
    if os.path.exists(f): os.remove(f)
    depot["watchlists"] = [w for w in depot.get("watchlists", []) if w["id"] != wl_id]
    save_depots(depots); return jsonify({"ok": True})

# ── Stocks (Bestand) ──────────────────────────────────────────────
@app.route("/api/stocks", methods=["GET"])
def api_get_stocks():
    did = request.args.get("depot", ""); depots = load_depots()
    if not did and depots: did = depots[0]["id"]
    return jsonify(load_stocks(did))

@app.route("/api/stocks", methods=["POST"])
def api_add_stock():
    body     = request.get_json()
    did      = body.get("depot", ""); ticker = body.get("ticker", "").strip().upper()
    name     = body.get("name", "").strip(); exchange = body.get("exchange", "").strip()
    isin     = body.get("isin", "").strip()
    if not did or not ticker or not name:
        return jsonify({"error": "depot, ticker, name erforderlich"}), 400
    stocks = load_stocks(did)
    if any(s["ticker"] == ticker for s in stocks):
        return jsonify({"error": f"{name} bereits im Depot"}), 409
    try: data = fetch_stock_data(ticker)
    except ValueError as e:
        msg = str(e)
        code = 404 if "nicht gefunden" in msg else 502
        return jsonify({"error": msg, "ticker_not_found": code == 404}), code
    except Exception as e: return jsonify({"error": str(e)}), 502
    stock = {**_make_stock(data), "name": name, "ticker": ticker, "exchange": exchange,
             "isin": isin, "last_notified_block": initial_block(data["current_eur"], data["ath_eur"])}
    stocks.append(stock); save_stocks(did, stocks); return jsonify(stock), 201

@app.route("/api/stocks/<ticker>", methods=["DELETE"])
def api_delete_stock(ticker):
    did = request.args.get("depot", "")
    save_stocks(did, [s for s in load_stocks(did) if s["ticker"] != ticker.upper()])
    return jsonify({"ok": True})

@app.route("/api/stocks/<ticker>/refresh", methods=["POST"])
def api_refresh_stock(ticker):
    did    = request.args.get("depot", ""); depots = load_depots()
    depot  = next((d for d in depots if d["id"] == did), {"id": did, "name": did})
    stocks = load_stocks(did)
    idx    = next((i for i, s in enumerate(stocks) if s["ticker"] == ticker.upper()), None)
    if idx is None: return jsonify({"error": "Nicht gefunden"}), 404
    try:
        data    = fetch_stock_data(ticker); s = stocks[idx]
        old_ath = float(s.get("ath_eur") or 0)
        new_ath = max(data["ath_eur"], s.get("ath_eur", 0))
        u_urls, u_ment, u_conf = resolve_notification_settings(did)
        new_blk = check_and_notify(s, data["current_eur"], new_ath,
                                   f"Bestand: {depot['name']}", u_urls,
                                   mention=u_ment, confirm=u_conf)
        stocks[idx] = {**_make_stock(data, s), "last_notified_block": new_blk}
        if (s.get("ath_alert_enabled") and old_ath > 0 and new_ath > old_ath + 0.001
                and depot.get("notifications_enabled", True)):
            send_ath_alerts([{**stocks[idx], "_prev_ath": old_ath}],
                             f"Bestand: {depot['name']}", u_urls, u_ment, depot_id=did)
        save_stocks(did, stocks)
        add_log("manual_refresh", f"Refresh: {s['name']}", f"Kurs: {data['current_eur']} EUR", True, depot_id=did)
        return jsonify(stocks[idx])
    except Exception as e: return jsonify({"error": str(e)}), 502

@app.route("/api/stocks/refresh-all", methods=["POST"])
def api_refresh_all():
    did = request.args.get("depot", "")
    if did:
        depots = load_depots(); depot = next((d for d in depots if d["id"] == did), None)
        if depot:
            ok, err = _refresh_depot(depot, "manual")
            add_log("manual_refresh", f"Refresh: {depot['name']}",
                    f"OK: {len(ok)} Fehler: {len(err)}", len(err) == 0, depot_id=did)
        return jsonify(load_stocks(did))
    refresh_all_depots("manual"); return jsonify({"ok": True})

@app.route("/api/stocks/<ticker>/change-ticker", methods=["POST"])
def change_ticker(ticker):
    did       = request.args.get("depot", ""); body = request.get_json() or {}
    new_tick  = body.get("ticker", "").strip().upper()
    new_name  = body.get("name", "").strip(); new_exch = body.get("exchange", "").strip()
    if not new_tick: return jsonify({"error": "Neuer Ticker erforderlich"}), 400
    stocks = load_stocks(did)
    idx    = next((i for i, s in enumerate(stocks) if s["ticker"] == ticker.upper()), None)
    if idx is None: return jsonify({"error": "Nicht gefunden"}), 404
    old = stocks[idx]
    try: data = fetch_stock_data(new_tick)
    except Exception as e: return jsonify({"error": str(e)}), 502
    stocks[idx] = {**_make_stock(data, old), "name": new_name or old["name"], "ticker": new_tick,
                   "exchange": new_exch or old.get("exchange", ""), "last_notified_block": old.get("last_notified_block", 0)}
    save_stocks(did, stocks)
    depots = load_depots()
    depot  = next((d for d in depots if d["id"] == did), {})
    add_log("manual_refresh", f"Ticker geändert: {old['name']} ({depot.get('name', did)})", f"{ticker} → {new_tick}", True, depot_id=did)
    return jsonify(stocks[idx])

@app.route("/api/depots/<depot_id>/stocks/<ticker>", methods=["PATCH"])
def patch_stock(depot_id, ticker):
    """Aktualisiert einzelne Felder eines Stocks direkt in der Depot-Datei."""
    body   = request.get_json() or {}
    stocks = load_stocks(depot_id)
    stock  = next((s for s in stocks if s["ticker"] == ticker), None)
    if not stock: return jsonify({"error": "Aktie nicht gefunden"}), 404
    # Erlaubte Felder die per PATCH gesetzt werden dürfen
    ALLOWED = {"bought_levels", "notes", "sector", "ath_alert_enabled"}
    for key, val in body.items():
        if key in ALLOWED:
            stock[key] = val
    save_stocks(depot_id, stocks)
    return jsonify(stock)

@app.route("/api/stocks/<ticker>/move-to-watchlist", methods=["POST"])
def move_to_watchlist(ticker):
    body  = request.get_json() or {}; did = body.get("depot_id", ""); wl_id = body.get("wl_id", "")
    stocks = load_stocks(did); stock = next((s for s in stocks if s["ticker"] == ticker.upper()), None)
    if not stock: return jsonify({"error": "Nicht gefunden"}), 404
    wl_stocks = load_wl_stocks(did, wl_id)
    if any(s["ticker"] == ticker.upper() for s in wl_stocks):
        return jsonify({"error": "Bereits in dieser Liste"}), 409
    s = dict(stock); s["last_notified_block"] = initial_block(s["current_eur"], s["ath_eur"])
    wl_stocks.append(s); save_wl_stocks(did, wl_id, wl_stocks)
    save_stocks(did, [s for s in stocks if s["ticker"] != ticker.upper()])
    return jsonify({"ok": True})

# ── Watchlist Stocks ──────────────────────────────────────────────
@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks", methods=["GET"])
def wl_get_stocks(depot_id, wl_id): return jsonify(load_wl_stocks(depot_id, wl_id))

@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks", methods=["POST"])
def wl_add_stock(depot_id, wl_id):
    body     = request.get_json()
    ticker   = body.get("ticker", "").strip().upper(); name = body.get("name", "").strip()
    exchange = body.get("exchange", "").strip(); isin = body.get("isin", "").strip()
    if not ticker or not name: return jsonify({"error": "ticker und name erforderlich"}), 400
    stocks = load_wl_stocks(depot_id, wl_id)
    if any(s["ticker"] == ticker for s in stocks): return jsonify({"error": "Bereits in dieser Liste"}), 409
    try: data = fetch_stock_data(ticker)
    except ValueError as e:
        msg = str(e)
        code = 404 if "nicht gefunden" in msg else 502
        return jsonify({"error": msg, "ticker_not_found": code == 404}), code
    except Exception as e: return jsonify({"error": str(e)}), 502
    stock = {**_make_stock(data), "name": name, "ticker": ticker, "exchange": exchange,
             "isin": isin, "last_notified_block": initial_block(data["current_eur"], data["ath_eur"])}
    stocks.append(stock); save_wl_stocks(depot_id, wl_id, stocks); return jsonify(stock), 201

@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks/<ticker>", methods=["PATCH"])
def wl_patch_stock(depot_id, wl_id, ticker):
    body   = request.get_json() or {}
    stocks = load_wl_stocks(depot_id, wl_id)
    stock  = next((s for s in stocks if s["ticker"] == ticker.upper()), None)
    if not stock: return jsonify({"error": "Aktie nicht gefunden"}), 404
    ALLOWED = {"sector", "notes", "ath_alert_enabled"}
    for key, val in body.items():
        if key in ALLOWED:
            stock[key] = val
    save_wl_stocks(depot_id, wl_id, stocks)
    return jsonify(stock)

@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks/<ticker>", methods=["DELETE"])
def wl_delete_stock(depot_id, wl_id, ticker):
    save_wl_stocks(depot_id, wl_id, [s for s in load_wl_stocks(depot_id, wl_id) if s["ticker"] != ticker.upper()])
    return jsonify({"ok": True})

@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks/<ticker>/refresh", methods=["POST"])
def wl_refresh_stock(depot_id, wl_id, ticker):
    depots  = load_depots(); depot = next((d for d in depots if d["id"] == depot_id), {"name": depot_id})
    wl_name = next((w["name"] for w in depot.get("watchlists", []) if w["id"] == wl_id), wl_id)
    stocks  = load_wl_stocks(depot_id, wl_id)
    idx     = next((i for i, s in enumerate(stocks) if s["ticker"] == ticker.upper()), None)
    if idx is None: return jsonify({"error": "Nicht gefunden"}), 404
    try:
        data    = fetch_stock_data(ticker); s = stocks[idx]
        old_ath = float(s.get("ath_eur") or 0)
        new_ath = max(data["ath_eur"], s.get("ath_eur", 0))
        u_urls, u_ment, u_conf = resolve_notification_settings(depot_id)
        new_blk = check_and_notify(s, data["current_eur"], new_ath,
                                   f"Beobachtung: {wl_name}", u_urls,
                                   mention=u_ment, confirm=u_conf)
        stocks[idx] = {**_make_stock(data, s), "last_notified_block": new_blk}
        if (s.get("ath_alert_enabled") and old_ath > 0 and new_ath > old_ath + 0.001
                and depot.get("notifications_enabled", True)):
            send_ath_alerts([{**stocks[idx], "_prev_ath": old_ath}],
                             f"Beobachtung: {wl_name}", u_urls, u_ment, depot_id=depot_id)
        save_wl_stocks(depot_id, wl_id, stocks); return jsonify(stocks[idx])
    except Exception as e: return jsonify({"error": str(e)}), 502

@app.route("/api/watchlist/<depot_id>/<wl_id>/stocks/<ticker>/move", methods=["POST"])
def wl_move_to_depot(depot_id, wl_id, ticker):
    wl_stocks    = load_wl_stocks(depot_id, wl_id)
    stock        = next((s for s in wl_stocks if s["ticker"] == ticker.upper()), None)
    if not stock: return jsonify({"error": "Nicht gefunden"}), 404
    depot_stocks = load_stocks(depot_id)
    if any(s["ticker"] == ticker.upper() for s in depot_stocks):
        return jsonify({"error": "Bereits im Depot"}), 409
    s = dict(stock); s["last_notified_block"] = initial_block(s["current_eur"], s["ath_eur"])
    depot_stocks.append(s); save_stocks(depot_id, depot_stocks)
    save_wl_stocks(depot_id, wl_id, [s for s in wl_stocks if s["ticker"] != ticker.upper()])
    return jsonify({"ok": True, "stock": s})

# ── Search ────────────────────────────────────────────────────────
@app.route("/api/search", methods=["GET"])
def search_companies():
    q = request.args.get("q", "").strip()
    if not q: return jsonify([])

    def yahoo(query):
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={urlquote(query)}&quotesCount=10&newsCount=0&listsCount=0"
        r   = requests.get(url, headers=YH, timeout=8); r.raise_for_status()
        return [{"name": it.get("longname") or it.get("shortname") or it.get("symbol",""),
                 "ticker": it.get("symbol",""), "exchange": it.get("exchDisp") or it.get("exchange",""),
                 "type": it.get("quoteType","")}
                for it in r.json().get("quotes", [])
                if it.get("quoteType","") in ("EQUITY","ETF","MUTUALFUND","INDEX","CRYPTOCURRENCY")
                and it.get("symbol")]

    def bff(term):
        bh = {"User-Agent":"Mozilla/5.0","Accept":"application/json",
              "Origin":"https://www.boerse-frankfurt.de","Referer":"https://www.boerse-frankfurt.de/"}
        r  = requests.get(f"https://api.boerse-frankfurt.de/v1/search/quick_search?searchTerms={term}&limit=6",
                          headers=bh, timeout=8)
        return r.json().get("data", [])

    # WKN: 6 alphanumerische Zeichen
    if re.match(r"^[A-Z0-9]{6}$", q.upper()):
        try:
            res = []
            for item in bff(q.upper()):
                isin = item.get("isin",""); sfx = f"  [WKN {item.get('wkn',q)}]"
                try:
                    yres = yahoo(isin)
                    if yres:
                        for y in yres: y.update({"name": y["name"]+sfx, "isin": isin})
                        res.extend(yres[:3]); continue
                except: pass
                res.append({"name": item.get("name","")+sfx, "ticker": isin,
                            "exchange": "Frankfurt", "type": "ETF", "isin": isin, "no_ticker": True})
            if res: return jsonify(res[:10])
        except Exception as e: log.warning(f"BFF WKN: {e}")

    # ISIN: 2 Buchstaben + 10 Zeichen
    if re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", q.upper()):
        isin = q.upper()
        bff_name, bff_wkn = None, None
        try:
            items = bff(isin)
            if items: bff_name = items[0].get("name",""); bff_wkn = items[0].get("wkn","")
        except Exception as e: log.warning(f"BFF ISIN: {e}")
        for qry in ([bff_name] if bff_name else []) + ([bff_wkn] if bff_wkn else []) + [isin]:
            try:
                yres = yahoo(qry)
                if yres:
                    for y in yres: y["isin"] = isin
                    return jsonify(yres[:10])
            except: pass
        if bff_name:
            sfx = f"  [WKN {bff_wkn}]" if bff_wkn else ""
            return jsonify([{"name": bff_name+sfx, "ticker": isin, "exchange": "Frankfurt",
                             "type": "ETF", "isin": isin, "no_ticker": True}])

    # Allgemeine Suche
    try:
        res = yahoo(q)
        if res: return jsonify(res[:10])
    except Exception as e: log.warning(f"Yahoo: {e}")
    return jsonify([])

# ── Settings & Notifications ──────────────────────────────────────
@app.route("/api/settings", methods=["GET"])
def get_settings():
    s = load_settings()
    s["next_refresh"]   = get_next_run_info()
    s["trading_config"] = s["trading"]  # Alias für Frontend-Kompatibilität
    return jsonify(s)

@app.route("/api/settings", methods=["POST"])
def update_settings():
    body = request.get_json(); s = load_settings()
    if "notifications_enabled" in body:
        s["notifications_enabled"] = bool(body["notifications_enabled"])
    if "verlauf_retention_days" in body:
        s["verlauf_retention_days"] = max(1, int(body["verlauf_retention_days"]))
    if "refresh_interval" in body:
        s["refresh_interval"] = int(body["refresh_interval"])
    if "timezone" in body:
        s["timezone"] = str(body["timezone"])
    if "trading" in body:
        t = body["trading"]
        if "days"         in t: s["trading"]["days"]         = [int(d) for d in t["days"]]
        if "start_hour"   in t: s["trading"]["start_hour"]   = int(t["start_hour"])
        if "start_minute" in t: s["trading"]["start_minute"] = int(t["start_minute"])
        if "end_hour"     in t: s["trading"]["end_hour"]      = int(t["end_hour"])
        if "end_minute"   in t: s["trading"]["end_minute"]    = int(t["end_minute"])
    if "digest_enabled" in body: s["digest_enabled"] = bool(body["digest_enabled"])
    if "digest_day"     in body: s["digest_day"]     = int(body["digest_day"])
    if "digest_time"    in body: s["digest_time"]    = str(body["digest_time"])
    save_settings(s); schedule_digest_job(); return jsonify(s)

@app.route("/api/notifications", methods=["GET"])
def get_notifications(): return jsonify(list(reversed(load_notifications())))

@app.route("/api/notifications/test", methods=["POST"])
def test_notification():
    body    = request.get_json(silent=True) or {}; urls = body.get("urls", [])
    mention = body.get("mention", "").strip()
    link    = f"\n\n{APP_URL}" if APP_URL else ""
    msg     = f"DepotRadar Testbenachrichtigung"
    txt     = f"Verbindung funktioniert!{link}"
    ok = send_apprise(msg, txt, urls, mention=mention)
    return jsonify({"ok": ok})

# ── User API ──────────────────────────────────────────────────────
@app.route("/api/users", methods=["GET"])
def api_get_users():
    users = load_users()
    return jsonify([{**{k: v for k, v in u.items() if k != "pin_hash"},
                     "has_pin": bool(u.get("pin_hash"))} for u in users])

@app.route("/api/users", methods=["POST"])
def api_create_user():
    body = request.get_json() or {}
    users = load_users()
    new_user = {
        "id":                    str(_uuid.uuid4())[:8],
        "name":                  body.get("name", "").strip(),
        "pin_hash":              hash_pin(body.get("pin")),
        "depots":                body.get("depots", []),
        "apprise_urls":          body.get("apprise_urls", []),
        "notification_mention":  body.get("notification_mention", ""),
        "notification_confirm":  bool(body.get("notification_confirm", False)),
    }
    users.append(new_user); save_users(users)
    return jsonify({**{k: v for k, v in new_user.items() if k != "pin_hash"},
                    "has_pin": bool(new_user.get("pin_hash"))}), 201

@app.route("/api/users/<user_id>", methods=["PATCH"])
def api_update_user(user_id):
    body  = request.get_json() or {}
    users = load_users()
    user  = next((u for u in users if u["id"] == user_id), None)
    if not user: return jsonify({"error": "Nicht gefunden"}), 404
    if "name"                 in body: user["name"]                = body["name"].strip()
    if "pin"                  in body: user["pin_hash"]            = hash_pin(body["pin"])
    if "depots"               in body: user["depots"]              = body["depots"]
    if "apprise_urls"         in body: user["apprise_urls"]        = body["apprise_urls"]
    if "notification_mention" in body: user["notification_mention"]= body["notification_mention"]
    if "notification_confirm" in body: user["notification_confirm"]= bool(body["notification_confirm"])
    save_users(users)
    return jsonify({**{k: v for k, v in user.items() if k != "pin_hash"},
                    "has_pin": bool(user.get("pin_hash"))})

@app.route("/api/users/<user_id>", methods=["DELETE"])
def api_delete_user(user_id):
    users = load_users()
    remaining = [u for u in users if u["id"] != user_id]
    if not remaining:
        return jsonify({"error": "Letzten Benutzer kann nicht löschen"}), 400
    save_users(remaining)
    return jsonify({"ok": True})

@app.route("/api/users/<user_id>/verify-pin", methods=["POST"])
def api_verify_pin(user_id):
    body  = request.get_json() or {}
    users = load_users()
    user  = next((u for u in users if u["id"] == user_id), None)
    if not user: return jsonify({"ok": False}), 404
    if not user.get("pin_hash"): return jsonify({"ok": True})
    return jsonify({"ok": hash_pin(str(body.get("pin", ""))) == user["pin_hash"]})

@app.route("/api/snapshots", methods=["GET"])
def api_snapshots():
    return jsonify(load_snapshots())

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": VERSION, "time": datetime.now().isoformat(), "next_refresh": get_next_run_info()})

if __name__ == "__main__":
    reset_pin_from_env(); delete_user_from_env(); migrate_if_needed(); start_scheduler()
    app.run(host="0.0.0.0", port=5000, debug=False)
