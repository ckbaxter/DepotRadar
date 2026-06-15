# DepotRadar

Ein selbst gehostetes Web-Tool zur Portfolio-Überwachung und ATH-Tracking von Aktien und ETFs in Euro.

Entwickelt für private Investoren die wissen wollen: Wie weit ist mein Portfolio gerade vom Allzeithoch entfernt — und welche Positionen lohnen sich zum Nachkauf?

![Version Backend](https://img.shields.io/badge/Backend-v2.4.7-blue)
![Version Frontend](https://img.shields.io/badge/Frontend-v2.7.16-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green)
![Entwickelt mit Claude](https://img.shields.io/badge/Entwickelt%20mit-Claude%20(Anthropic)-blueviolet)

-----

## Vorschau

![DepotRadar Vorschau](docs/Preview.jpeg)

*Alle dargestellten Aktien, Kurse, Einstandswerte und Kennzahlen sind frei erfunden und dienen ausschließlich zur Veranschaulichung der Benutzeroberfläche.*

-----

## Features

- **Multi-User** — mehrere Benutzerprofile mit optionalem PIN; jeder User sieht nur seine eigenen Depots und Watchlists
- **Multi-Depot** — mehrere Depots pro Benutzer, jedes unabhängig konfigurierbar
- **Watchlists** — Beobachtungslisten pro Depot, direkt in der Tab-Leiste neben den Depots
- **ATH-Discount** — farbcodierte Badges: grün (<20%), gelb (20–39%), orange (40–59%), rot (>60%) mit Multiplikator (1×/2×/3×)
- **Portfolio-Gewichtung** — Balken und %-Wert pro Aktie zeigen die relative Gewichtung im Depot; sortierbar
- **Portfolio-Verlauf** — täglicher Snapshot des Gesamtwerts; Liniendiagramm mit Zeitraum-Filter (1W/1M/3M/6M/1J/Alles)
- **Kaufempfehlung** — pro Depot ein optionales Kaufbudget; bei Erreichen eines Discount-Blocks wird die empfohlene Stückzahl berechnet — in der App und in Benachrichtigungen
- **Nachkauf-Kandidaten** — filtert Aktien die günstig UND untergewichtet im Depot sind; Schwellenwert pro Depot einstellbar
- **Sektor-Tags** — automatische Sektor-Erkennung via Yahoo Finance; manuell anpassbar; Filter und Sektor-Übersicht in der Portfolio-Ansicht
- **Performance-Badges** — 1T / 1W / 1M / 3M direkt unter dem Kurs
- **P&L** — Gewinn/Verlust in % und € wenn Einstandskurs bekannt
- **Aktiensplits** — über die UI verwaltbar; splitbereinigter Einstandskurs bei Parqet-Sync
- **Parqet-Integration** — OAuth-Sync von Einstandskurs und Stückzahl, pro Depot eigene Client ID; Backup vor jedem Sync mit Rückgängig-Funktion
- **ATH-Prüfung** — vergleicht gespeicherte ATH-Werte mit Yahoo Finance (inkl. Watchlist-Aktien); Korrekturen direkt in der App möglich
- **XETRA-Unterstützung** — automatischer Ticker-Vorschlag für deutsche Handelsplätze
- **Apprise-Benachrichtigungen** — Alarm bei neuem Discount-Block, inkl. Kaufempfehlung, Nachkauf-Kennzeichnung (🛒) und Kursstand-Timestamp; optionaler Bestätigungsmodus (2× Refresh vor Alarm); Konfiguration pro Benutzer
- **Wöchentliche Zusammenfassung** — optionaler Wochenbericht per Apprise mit ATH-Verteilung, Nachkauf-Kandidaten, Wochenperformance und Sektor-Übersicht; HTML-formatiert für E-Mail-Versand; pro Depot aktivierbar
- **Verlauf** — vollständiger Aktivitätsverlauf mit Filter nach Benutzer und Eintragstyp
- **Einstellungen per UI** — Zeitzone, Handelstage, -zeiten, Benachrichtigungen und Wochenbericht direkt in der App konfigurierbar
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
├── data/                      # Wird automatisch angelegt
│   ├── depots.json
│   ├── depot_*.json
│   ├── depot_*_backup.json    # Backup vor Parqet-Sync (automatisch)
│   ├── depot_*_wl_*.json      # Watchlist-Aktien
│   ├── splits.json            # Aktiensplits (automatisch befüllt)
│   ├── settings.json
│   ├── users.json             # Benutzerprofile (wird beim ersten Start angelegt)
│   ├── snapshots.json         # Tägliche Portfolio-Snapshots
│   └── notifications.json     # Verlauf / Benachrichtigungshistorie
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

### Administration via Umgebungsvariablen

Bestimmte Verwaltungsaufgaben werden über temporäre Umgebungsvariablen in `docker-compose.yml` erledigt, um kein Rollenkonzept in der UI zu benötigen. Nach dem Ausführen die Variable wieder entfernen und neu starten.

#### PIN eines Benutzers zurücksetzen

```yaml
environment:
  - RESET_PIN_USER=Christoph
```

Beim nächsten Start wird der PIN des Benutzers `Christoph` gelöscht — er kann sich danach ohne PIN einloggen und einen neuen setzen. **Variable anschließend entfernen und neu starten.**

#### Benutzer löschen

```yaml
environment:
  - DELETE_USER=Fiona
```

Beim nächsten Start wird der Benutzer `Fiona` aus `users.json` entfernt. Depots die **ausschließlich** diesem Benutzer gehörten werden vollständig gelöscht (inkl. Aktien- und Watchlist-Dateien). Depots die mehreren Benutzern zugeordnet waren bleiben erhalten. **Variable anschließend entfernen und neu starten.**

```bash
# Nach Setzen der Variable:
docker compose up -d --force-recreate backend
# Nach erfolgter Aktion Variable entfernen, dann erneut:
docker compose up -d --force-recreate backend
```

-----

## Multi-User

DepotRadar unterstützt mehrere Benutzerprofile — ideal wenn mehrere Personen die App gemeinsam nutzen.

### Einrichtung

Beim ersten Start erscheint ein Setup-Screen mit zwei Optionen:

- **Ohne Benutzer starten** — App verhält sich wie eine Einzelbenutzer-Anwendung, kein Login erforderlich
- **Benutzer anlegen** — Wizard zum Anlegen des ersten Benutzerprofils

### Funktionsweise

- Jeder Benutzer hat einen optionalen 4-stelligen PIN
- Nach dem Login sieht man nur die eigenen Depots und Watchlists
- Benachrichtigungs-Einstellungen (Apprise-URLs, Mention, Bestätigungsmodus) werden pro Benutzer konfiguriert
- Die Wöchentliche Zusammenfassung bleibt pro Depot konfigurierbar
- Neue Depots werden automatisch dem eingeloggten Benutzer zugeordnet
- Jeder Benutzer kann neue Benutzer anlegen; eigene Einstellungen und PIN kann jeder selbst verwalten

### Rollback

Multi-User kann jederzeit deaktiviert werden indem `data/users.json` gelöscht wird — alle Depots und Daten bleiben unberührt.

-----

## Einstellungen (UI)

Alle Einstellungen sind unter **⚙ Einstellungen** erreichbar:

|Einstellung                 |Beschreibung                                       |
|----------------------------|---------------------------------------------------|
|Automatischer Refresh       |Intervall der Kursabfragen                         |
|Zeitzone                    |Für korrekte Handelszeiten-Berechnung              |
|Handelstage                 |An welchen Tagen aktualisiert wird                 |
|Handelszeiten               |Zwischen welchen Uhrzeiten aktualisiert wird       |
|Benachrichtigungen          |Global ein/aus                                     |
|Wöchentliche Zusammenfassung|Wochentag, Uhrzeit und globaler Ein/Aus-Schalter   |
|Verlaufsbereinigung         |Aufbewahrungszeitraum für Benachrichtigungshistorie|
|Aktiensplits                |Splits hinzufügen und verwalten                    |

-----

## Kaufempfehlung

Pro Depot kann ein optionales **Kaufbudget** in EUR hinterlegt werden (Depot-Einstellungen → ⚙).

|Discount-Block|Multiplikator|Beispiel bei 200 € Budget|
|--------------|-------------|-------------------------|
|20–39%        |1×           |200 €                    |
|40–59%        |2×           |400 €                    |
|≥60%          |3×           |600 €                    |

**Beispiel** — Budget 200 €, Aktie kostet 19 €, Abstand −20%:
→ **11 Stk. für ~209 €** (liegt innerhalb der 20% Toleranz über 200 €)

-----

## Nachkauf-Kandidaten

Der 🛒-Filter zeigt Aktien die gleichzeitig:

- ≥20% unter ATH sind
- In den unteren X% nach Positionswert liegen (Kurs × Stückzahl)

Der Schwellenwert (Standard 30%) ist **pro Depot** einstellbar.

-----

## Sektor-Tags

Jede Aktie kann einem Sektor zugeordnet werden. 16 vordefinierte Sektoren stehen zur Auswahl; eigene Bezeichnungen sind per Freitext möglich.

**Automatische Erkennung:** Beim ersten Kurs-Refresh wird der Sektor automatisch via Yahoo Finance abgefragt. Manuell gesetzte Sektoren werden nie überschrieben.

-----

## Aktiensplits

Splits werden in `data/splits.json` gespeichert und über **⚙ Einstellungen → Aktiensplits** verwaltet.

**Split hinzufügen:**

1. Einstellungen öffnen → „+ Split hinzufügen”
1. Aktie aus dem eigenen Bestand suchen und auswählen
1. Datum und Faktor (z.B. `10` für 10:1) eingeben
1. Speichern

-----

## Parqet-Integration

DepotRadar verbindet sich mit [Parqet](https://parqet.com) um Einstandskurse und Stückzahlen zu importieren. **Jedes Depot benötigt eine eigene Parqet-Integration.**

### Einrichtung

1. [developer.parqet.com/console/integrations](https://developer.parqet.com/console/integrations) → **+ New Integration**
1. Scope: nur **read portfolio** ankreuzen
1. Redirect URI: `http://DEINE-APP-URL/api/parqet/callback`
1. Client ID kopieren → in DepotRadar: Depot-Einstellungen → Client ID eintragen → Verbinden

### Backup & Rückgängig

Vor jedem Sync wird automatisch ein Backup der Depot-Datei angelegt. Rückgängig über **↩ Rückgängig** in den Depot-Einstellungen.

-----

## Benachrichtigungen (Apprise)

Konfigurierbar pro Benutzer (Benutzer-Icon oben rechts → Bearbeiten). Unterstützte Dienste (Auswahl):

|Dienst     |URL-Format                                  |
|-----------|--------------------------------------------|
|Telegram   |`tgram://TOKEN/CHATID`                      |
|Gotify     |`gotify://host/token`                       |
|ntfy       |`ntfy://host/topic`                         |
|Discord    |`discord://WEBHOOK_ID/TOKEN`                |
|E-Mail     |`mailto://user:pass@gmail.com` (HTML-Format)|
|Apprise API|`http://apprise.host/notify/tag`            |

**Bestätigungsmodus** (pro Benutzer aktivierbar): Eine Aktie muss zwei aufeinanderfolgende Refreshes unter dem ATH-Level liegen bevor ein Alarm ausgelöst wird.

-----

## Kursabfragen

- **Quelle:** Yahoo Finance (kostenlos, kein API-Key nötig)
- **Historische Daten:** 10 Jahre für ATH-Berechnung
- **Währungen:** Automatische EUR-Umrechnung via [Frankfurter API](https://www.frankfurter.app)
- **GBp-Fix:** Londoner Aktien in Pence werden automatisch in GBP umgerechnet

-----

## Versionshistorie

|Version|Beschreibung                                                              |
|-------|--------------------------------------------------------------------------|
|2.4.x  |Multi-User mit PIN, Depot/User-Verwaltung via Umgebungsvariablen          |
|2.3.x  |Portfolio-Gewichtung, Portfolio-Verlauf (Snapshots), Code-Qualität        |
|2.2.x  |Sektor-Tags mit Auto-Fetch, Sektor-Übersicht, Sektor-Filter               |
|2.1.x  |Wöchentliche Zusammenfassung (Apprise + HTML-E-Mail), Verlaufsbereinigung |
|2.0.x  |Bestätigungsmodus, Kursstand in Benachrichtigungen, Verlauf-Verbesserungen|
|1.9.x  |Nachkauf-Kandidaten in Benachrichtigungen (🛒), Nachkauf-Schwelle pro Depot|
|1.8.0  |Parqet-Sync Backup mit Rückgängig-Funktion                                |
|1.7.x  |Aktiensplits über UI verwaltbar                                           |
|1.6.x  |Kaufempfehlung in Benachrichtigungen, App und Tabelle                     |
|1.5.0  |Zeitzone und Handelszeiten über UI einstellbar                            |
|1.4.x  |Parqet Client ID pro Depot                                                |
|1.3.0  |Nachkauf-Kandidaten Filter                                                |
|1.2.0  |Parqet OAuth PKCE Integration                                             |
|1.1.0  |XETRA-Ticker-Unterstützung                                                |
|1.0.0  |Erstes Release                                                            |

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