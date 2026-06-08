# DepotRadar

Ein selbst gehostetes Web-Tool zur Portfolio-Überwachung und ATH-Tracking von Aktien und ETFs in Euro.

Entwickelt für private Investoren die wissen wollen: Wie weit ist mein Portfolio gerade vom Allzeithoch entfernt — und welche Positionen lohnen sich zum Nachkauf?

![Version Backend](https://img.shields.io/badge/Backend-v2.0.5-blue)
![Version Frontend](https://img.shields.io/badge/Frontend-v2.1.4-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green)
![Entwickelt mit Claude](https://img.shields.io/badge/Entwickelt%20mit-Claude%20(Anthropic)-blueviolet)

-----

## Vorschau

![ATH-Tracker Vorschau](docs/Preview.jpeg)

*Alle dargestellten Aktien, Kurse, Einstandswerte und Kennzahlen sind frei erfunden und dienen ausschließlich zur Veranschaulichung der Benutzeroberfläche.*

-----

## Features

- **Multi-Depot** — mehrere Depots pro Installation, jedes unabhängig konfigurierbar
- **Watchlists** — Beobachtungslisten pro Depot
- **ATH-Discount** — farbcodierte Badges: grün (<20%), gelb (20–39%), orange (40–59%), rot (>60%) mit Multiplikator (1×/2×/3×)
- **Kaufempfehlung** — pro Depot ein optionales Kaufbudget; bei Erreichen eines Discount-Blocks wird die empfohlene Stückzahl berechnet — in der App und in Benachrichtigungen
- **Nachkauf-Kandidaten** — filtert Aktien die günstig UND untergewichtet im Depot sind; Schwellenwert pro Depot einstellbar
- **Performance-Badges** — 1T / 1W / 1M / 3M direkt unter dem Kurs
- **P&L** — Gewinn/Verlust in % und € wenn Einstandskurs bekannt
- **Aktiensplits** — über die UI verwaltbar; splitbereinigter Einstandskurs bei Parqet-Sync
- **Parqet-Integration** — OAuth-Sync von Einstandskurs und Stückzahl, pro Depot eigene Client ID; Backup vor jedem Sync mit Rückgängig-Funktion
- **XETRA-Unterstützung** — automatischer Ticker-Vorschlag für deutsche Handelsplätze
- **Apprise-Benachrichtigungen** — Alarm bei neuem Discount-Block, inkl. Kaufempfehlung und Nachkauf-Kennzeichnung (🛒)
- **Einstellungen per UI** — Zeitzone, Handelstage, -zeiten und Benachrichtigungen direkt in der App konfigurierbar
- **Dark / Light Mode**
- **Mobile-optimiert** — Touch-freundlich für iPad und Smartphone

-----

## Voraussetzungen

- Docker & Docker Compose
- Internetzugang (Yahoo Finance API, Parqet OAuth)

-----

## Installation

```bash
git clone https://github.com/ckbaxter/DepotRadar.git
cd DepotRadar
docker compose up -d --build
```

Erreichbar unter: **<http://localhost:8080>**

-----

## Verzeichnisstruktur

```
DepotRadar/
├── backend/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── index.html
├── nginx/
│   └── nginx.conf
├── data/                     # Wird automatisch angelegt
│   ├── depots.json
│   ├── depot_*.json
│   ├── depot_*_backup.json   # Backup vor Parqet-Sync (automatisch)
│   ├── splits.json           # Aktiensplits (automatisch befüllt)
│   ├── settings.json
│   └── ath-tracker.yml       # Optional — siehe Konfiguration
└── docker-compose.yml
```

-----

## Konfiguration

### docker-compose.yml

```yaml
environment:
  - TZ=Europe/Berlin
  - APP_URL=http://depotradar.lan   # Eigene URL/IP — wichtig für Parqet OAuth
```

`APP_URL` muss auf die tatsächlich erreichbare Adresse zeigen.

### Einstellungen (UI)

Alle Einstellungen sind unter **⚙ Einstellungen** erreichbar:

|Einstellung          |Beschreibung                                |
|---------------------|--------------------------------------------|
|Automatischer Refresh|Intervall der Kursabfragen                  |
|Zeitzone             |Für korrekte Handelszeiten-Berechnung       |
|Handelstage          |An welchen Tagen aktualisiert wird          |
|Handelszeiten        |Zwischen welchen Uhrzeiten aktualisiert wird|
|Benachrichtigungen   |Global ein/aus                              |
|Aktiensplits         |Splits hinzufügen und verwalten             |

### Optionale Konfigurationsdatei

Wer Timezone und Handelszeiten per Datei statt per UI konfigurieren möchte, legt `data/ath-tracker.yml` an:

```yaml
timezone: Europe/Berlin
trading:
  days: [0, 1, 2, 3, 4]   # 0=Mo … 6=So
  start_hour: 8
  end_hour: 23
refresh_interval_seconds: 3600
```

UI-Einstellungen haben immer Vorrang.

-----

## Kaufempfehlung

Pro Depot kann ein optionales **Kaufbudget** in EUR hinterlegt werden (Depot-Einstellungen → ⚙).

Bei jeder Benachrichtigung wird berechnet wie viele ganze Aktien mit diesem Budget gekauft werden könnten:

|Discount-Block|Multiplikator|Beispiel bei 200 € Budget|
|--------------|-------------|-------------------------|
|20–39%        |1×           |200 €                    |
|40–59%        |2×           |400 €                    |
|≥60%          |3×           |600 €                    |

Es wird immer eine ganze Anzahl Aktien berechnet. Passt eine zusätzliche Aktie noch innerhalb von 20% über dem Budget, wird sie dazugezählt.

**Beispiel** — Budget 200 €, Aktie kostet 19 €, Abstand −20%:
→ **11 Stk. für ~209 €** (liegt innerhalb der 20% Toleranz über 200 €)

-----

## Nachkauf-Kandidaten

Der 🛒-Filter zeigt Aktien die gleichzeitig:

- ≥20% unter ATH sind
- In den unteren X% nach Positionswert liegen (Kurs × Stückzahl)

Der Schwellenwert (Standard 30%) ist **pro Depot** einstellbar — der Schieberegler erscheint beim Aktivieren des Filters und wird automatisch pro Depot gespeichert.

Nachkauf-Kandidaten werden in Benachrichtigungen mit 🛒 gekennzeichnet.

-----

## Aktiensplits

Splits werden in `data/splits.json` gespeichert und über **⚙ Einstellungen → Aktiensplits** verwaltet. Beim ersten Start werden bekannte Splits automatisch angelegt (NVIDIA, Broadcom, Booking Holdings).

**Split hinzufügen:**

1. Einstellungen öffnen → „+ Split hinzufügen”
1. Aktie aus dem eigenen Bestand suchen und auswählen
1. Datum und Faktor (z.B. `10` für 10:1) eingeben
1. Speichern

> **Hinweis:** Die Aktie muss sich bereits im Depot oder einer Watchlist befinden, da die Auswahl ausschließlich aus dem eigenen Bestand befüllt wird.

-----

## Parqet-Integration

ATH-Tracker verbindet sich mit [Parqet](https://parqet.com) um Einstandskurse und Stückzahlen zu importieren. **Jedes Depot benötigt eine eigene Parqet-Integration.**

### Einrichtung

1. [developer.parqet.com/console/integrations](https://developer.parqet.com/console/integrations) → **+ New Integration**
1. Name: beliebig (z.B. `ATH-Tracker`)
1. Scope: nur **read portfolio** ankreuzen
1. Redirect URI: `http://DEINE-APP-URL/api/parqet/callback`
1. **Create** → Client ID kopieren
1. In ATH-Tracker: Depot-Einstellungen → Client ID eintragen → Verbinden

### Backup & Rückgängig

Vor jedem Sync wird automatisch ein Backup der Depot-Datei angelegt. Falls ein Sync unerwünschte Änderungen verursacht, kann er über **↩ Rückgängig** in den Depot-Einstellungen (Parqet-Bereich) rückgängig gemacht werden.

-----

## Benachrichtigungen (Apprise)

Konfigurierbar pro Depot (⚙-Icon im Depot-Tab). Unterstützte Dienste (Auswahl):

|Dienst     |URL-Format                      |
|-----------|--------------------------------|
|Telegram   |`tgram://TOKEN/CHATID`          |
|Gotify     |`gotify://host/token`           |
|ntfy       |`ntfy://host/topic`             |
|Discord    |`discord://WEBHOOK_ID/TOKEN`    |
|Apprise API|`http://apprise.host/notify/tag`|

Benachrichtigungen enthalten Kurs, ATH, Abstand, Kaufempfehlung und — falls zutreffend — die Kennzeichnung als Nachkauf-Kandidat (🛒).

-----

## Kursabfragen

- **Quelle:** Yahoo Finance (kostenlos, kein API-Key nötig)
- **Historische Daten:** 10 Jahre für ATH-Berechnung
- **Währungen:** Automatische EUR-Umrechnung via [Frankfurter API](https://www.frankfurter.app)
- **GBp-Fix:** Londoner Aktien in Pence werden automatisch in GBP umgerechnet

-----

## Versionshistorie

|Version|Beschreibung                                                   |
|-------|---------------------------------------------------------------|
|1.9.1  |Nachkauf-Schwelle pro Depot                                    |
|1.9.0  |Nachkauf-Kandidaten in Benachrichtigungen (🛒), 3-Phasen-Refresh|
|1.8.0  |Parqet-Sync Backup mit Rückgängig-Funktion                     |
|1.7.1  |COMPANY_DB und ISIN_MAP entfernt, XETRA-Suche optimiert        |
|1.7.0  |Aktiensplits über UI verwaltbar, Depot-basierte ISIN-Auswahl   |
|1.6.x  |Kaufempfehlung in Benachrichtigungen, App und Tabelle          |
|1.5.0  |Zeitzone und Handelszeiten über UI einstellbar                 |
|1.4.x  |Parqet Client ID pro Depot, config/ und data/ zusammengeführt  |
|1.3.0  |Nachkauf-Kandidaten Filter                                     |
|1.2.0  |Parqet OAuth PKCE Integration                                  |
|1.1.0  |XETRA-Ticker-Unterstützung                                     |
|1.0.0  |Erstes Release                                                 |

-----

## Haftungsausschluss

Dieses Projekt dient ausschließlich dem persönlichen, nicht-kommerziellen Einsatz.

Die Kursdaten stammen von Yahoo Finance und unterliegen deren [Nutzungsbedingungen](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html). Die Nutzung erfolgt auf eigene Verantwortung.

**Keine Anlageberatung.** Alle angezeigten Informationen dienen ausschließlich zur persönlichen Orientierung und stellen keine Empfehlung zum Kauf oder Verkauf von Wertpapieren dar.

-----

## Lizenz

MIT

-----

## Entstehung

DepotRadar wurde vollständig in Zusammenarbeit mit **[Claude](https://claude.ai)** von Anthropic entwickelt — von der ersten Idee bis zur fertigen Anwendung, iterativ über viele Gespräche hinweg.
