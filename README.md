# ATH-Tracker

> Developed with the assistance of [Claude](https://claude.ai) (Anthropic)

A self-hosted web application to track your stocks and ETFs relative to their **All-Time High (ATH)**.
Automatically fetches current prices and ATH values, converts everything to **Euro**, and sends
**Apprise notifications** when configurable discount levels are reached.

---

> Eine selbst gehostete Web-Applikation zur Verfolgung von Aktien und ETFs relativ zu ihrem
> **Allzeithoch (ATH)**. Kurs- und ATH-Daten werden automatisch abgerufen, in **Euro** umgerechnet
> und bei konfigurierbaren Rabattstufen werden **Apprise-Benachrichtigungen** versendet.

---

## Screenshot

![ATH-Tracker Screenshot](docs/screenshot.png)

---

## Features / Funktionen

| | EN | DE |
|---|---|---|
| 📈 | Automatic price & ATH data from Yahoo Finance | Automatische Kurs- & ATH-Daten von Yahoo Finance |
| 💶 | All values in Euro (auto currency conversion) | Alle Werte in Euro (automatische Währungsumrechnung) |
| 🏦 | Multiple depots per user | Mehrere Depots pro Nutzer |
| 🔍 | Watchlists per depot (potential buys) | Beobachtungslisten pro Depot (potenzielle Käufe) |
| ➡️ | Move stock from watchlist to depot | Aktie von Beobachtungsliste ins Depot verschieben |
| 🔔 | Apprise notifications per depot at 10% discount blocks (≥20%) | Apprise-Benachrichtigungen pro Depot bei 10%-Blöcken (ab 20%) |
| 🏷️ | Notifications show Bestand vs. Beobachtung clearly | Benachrichtigungen zeigen Bestand vs. Beobachtung |
| 🕐 | Configurable trading window (Mon–Fri, 08:00–23:00) | Konfigurierbares Handelsfenster (Mo–Fr, 08–23 Uhr) |
| 🔍 | Search by company name, ticker, ISIN or WKN | Suche nach Name, Ticker, ISIN oder WKN |
| 📊 | Sortable table with discount level overview | Sortierbare Tabelle mit Rabattstufenübersicht |
| 📱 | Responsive design for desktop, tablet & mobile | Responsives Design für Desktop, Tablet & Smartphone |
| 🐳 | Docker Compose deployment with Traefik support | Docker Compose Deployment mit Traefik-Unterstützung |

---

## Stack

- **Backend:** Python, Flask, APScheduler, Apprise, PyYAML
- **Frontend:** Vanilla HTML/CSS/JS (no framework)
- **Reverse Proxy:** NGINX
- **Data:** Yahoo Finance, Frankfurter API (EUR conversion), Börse Frankfurt (WKN lookup)

---

## Quick Start

### Prerequisites / Voraussetzungen
- Docker & Docker Compose

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourname/ath-tracker.git
cd ath-tracker

# 2. Create config from example
cp config/ath-tracker.yml.example config/ath-tracker.yml

# 3. Edit config if needed (trading hours, interval, timezone)
nano config/ath-tracker.yml

# 4. Start
docker compose up -d --build
```

**App is available at:** http://\<your-server-ip\>:8080

> **Erreichbar unter:** http://\<server-ip\>:8080

---

## Multi-Depot & Watchlists

### Depots
Each person gets their own depot. Depots are created via the **+** button in the depot tab bar.
Per depot you can configure individual Apprise notification URLs (tap the ⚙ icon on the depot tab).

> Jede Person bekommt ein eigenes Depot. Depots werden über den **+** Button in der Depot-Tab-Leiste angelegt.
> Pro Depot können individuelle Apprise-URLs konfiguriert werden (⚙-Icon im Depot-Tab antippen).

### Watchlists / Beobachtungslisten
Each depot can have multiple watchlists for tracking potential buys.

```
[ Christoph ⚙ ] [ Sandra ⚙ ] [ + ]        ← Depot tabs
[ Bestand | 🔍 Tech | 🔍 ETFs | + ]        ← View tabs per depot
```

- Add a watchlist via **+** in the view tab bar
- Stocks in watchlists show a **→ Depot** button to move them to the main holdings
- Notifications clearly show whether an alert comes from **Bestand** or **Beobachtung**

> Jedes Depot kann mehrere Beobachtungslisten haben. Aktien können per **→ Depot** Button
> in den Bestand verschoben werden. Benachrichtigungen zeigen klar ob es sich um
> Bestand oder Beobachtung handelt.

---

## Configuration / Konfiguration

All trading-window settings are managed in **`config/ath-tracker.yml`**:

```yaml
timezone: "Europe/Berlin"

trading:
  days: [0, 1, 2, 3, 4]   # 0=Mon ... 4=Fri
  start_hour: 8            # First refresh of day at 08:00
  end_hour: 23             # No refreshes at or after 23:00

refresh_interval_seconds: 3600   # Default: every hour
```

The **refresh interval** can also be changed in the web UI under Settings.

---

## Apprise Notifications / Benachrichtigungen

Configure Apprise URLs **per depot** via the ⚙ icon on the depot tab.
All watchlists of a depot share the same URLs as the depot.

| Service | URL format |
|---|---|
| Telegram | `tgram://BOTTOKEN/CHATID` |
| Gotify | `gotify://hostname/token` |
| Apprise API | `http://apprise:8000/notify/MYKEY` |
| E-Mail | `mailto://user:pass@gmail.com` |

**Notification logic / Benachrichtigungslogik:**
- Notification when a new 10% block (≥20%) is first reached downward
- No repeated notifications within the same block
- If price recovers and drops again: new notification
- Baseline = discount at time of adding the stock
- Notification title clearly shows `[Bestand: Depot]` or `[Beobachtung: Watchlist (Depot)]`

---

## Project Structure / Projektstruktur

```
ath-tracker/
├── backend/
│   ├── app.py              # Flask API + scheduler + Yahoo Finance + Apprise
│   ├── Dockerfile
│   └── requirements.txt
├── config/
│   ├── ath-tracker.yml             # Your config (not in git)
│   └── ath-tracker.yml.example     # Template (in git)
├── data/                   # Runtime data — not in git
│   ├── depots.json                 # Depot & watchlist metadata
│   ├── depot_{id}.json             # Holdings per depot
│   ├── wl_{depot_id}_{wl_id}.json  # Stocks per watchlist
│   ├── settings.json
│   └── notifications.json
├── frontend/
│   └── index.html          # Single-page app
├── nginx/
│   └── nginx.conf
└── docker-compose.yml
```

---

## Data Sources / Datenquellen

- **[Yahoo Finance](https://finance.yahoo.com)** — prices & ATH history (non-commercial use only)
- **[Frankfurter API](https://www.frankfurter.app)** — EUR exchange rates
- **[Börse Frankfurt API](https://www.boerse-frankfurt.de)** — WKN to ISIN lookup

---

## Disclaimer

This project is for **personal, non-commercial use only**.
Yahoo Finance data is subject to their [Terms of Service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html).
Nothing in this application constitutes financial advice.

---

*Dieses Projekt ist ausschließlich für den **persönlichen, nicht-kommerziellen Einsatz** bestimmt.
Keine Anlageberatung.*

---

## License

MIT
