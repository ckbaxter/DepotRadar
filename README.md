# DepotRadar

Ein selbst gehostetes Web-Tool zur Portfolio-Überwachung und ATH-Tracking von Aktien und ETFs in Euro.

Entwickelt für private Investoren die wissen wollen: Wie weit ist mein Portfolio gerade vom Allzeithoch entfernt — und welche Positionen lohnen sich zum Nachkauf?

![Version Backend](https://img.shields.io/badge/Backend-v2.7.7-blue)
![Version Frontend](https://img.shields.io/badge/Frontend-v2.9.6-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)
![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green)
![Entwickelt mit Claude](https://img.shields.io/badge/Entwickelt%20mit-Claude%20(Anthropic)-blueviolet)

-----

## Vorschau

![DepotRadar Vorschau](docs/Preview.jpeg)

*Alle dargestellten Aktien, Kurse, Einstandswerte und Kennzahlen sind frei erfunden und dienen ausschließlich zur Veranschaulichung der Benutzeroberfläche.*

> **Hinweis:** Aufgrund der schnellen Weiterentwicklung spiegelt dieses Bild nicht zwingend den neuesten Stand wider — einzelne UI-Details und Designänderungen können abweichen.

-----

## Features

- **Multi-User** — mehrere Benutzerprofile mit optionalem PIN (per Zahlenpad oder Tastatur eingebbar); jeder User sieht nur seine eigenen Depots und Watchlists
- **Multi-Depot** — mehrere Depots pro Benutzer, jedes unabhängig konfigurierbar
- **Watchlists** — Beobachtungslisten pro Depot, direkt in der Tab-Leiste neben den Depots
- **ATH-Discount** — farbcodierte Badges: grün (<20%), gelb (20–39%), orange (40–59%), rot (>60%) mit Multiplikator (1×/2×/3×)
- **Kompakte Übersichten** — ATH-, Portfolio- und Sektor-Übersicht sowie Portfolio-Verlauf in einer gemeinsam einklappbaren Ansicht, jede Sektion unabhängig auf-/zuklappbar
- **Portfolio-Gewichtung** — Balken und %-Wert pro Aktie zeigen die relative Gewichtung im Depot; sortierbar
- **Portfolio-Verlauf** — täglicher Snapshot des Gesamtwerts; interaktives Liniendiagramm mit Zeitraum-Filter (1W/1M/3M/6M/1J/Alles); Datenpunkte per Antippen/Hovern abrufbar (Datum + exakter Wert), lange Zeiträume werden automatisch reduziert; **Invested-Capital-Kurve** zeigt den kumulierten Einstandswert als gestrichelte Linie (nur bei Positionen mit bekanntem Einstandskurs)
- **Treemap-Ansicht** — alternative Darstellung des Depots als Flächenkarte; Kachelgröße = Positionswert, Farbe = ATH-Discount-Stufe; Toggle ⊞ Treemap / ☰ Tabelle in der Aktionsleiste (nur Bestand, ab 2 Positionen)
- **Kaufempfehlung** — pro Depot ein optionales Kaufbudget; bei Erreichen eines Discount-Blocks wird die empfohlene Stückzahl berechnet — in der App und in Benachrichtigungen
- **Nachkauf-Kandidaten** — filtert Aktien die günstig UND untergewichtet im Depot sind; Schwellenwert pro Depot einstellbar
- **Sektor-Tags** — automatische Sektor-Erkennung via Yahoo Finance; manuell anpassbar; Filter und Sektor-Übersicht in der Portfolio-Ansicht
- **Diversifikations-Lücke (⚖️)** — markiert Aktien aus Sektoren, die im Bestand unterrepräsentiert sind (<50% des Sektor-Durchschnitts); sichtbar am Sektor-Tag in Tabelle/Karten, in der Sektor-Übersicht und im ATH-Discount-Alarm; Watchlist-Aktien werden dabei immer gegen den echten Bestand bewertet
- **Performance-Badges** — 1T / 1M / 3M / 1J / 3J direkt unter dem Kurs
- **P&L** — Gewinn/Verlust in % und € wenn Einstandskurs bekannt
- **Kaufmarkierung (K)** — ATH-Level-Kacheln (−20%, −30% usw.) sind antippbar; ein Tippen setzt ein blaues K-Badge als persönliche Notiz auf welchem Level ein Kauf stattfand; mehrere Level gleichzeitig möglich, wird dauerhaft gespeichert
- **Aktiensplits** — über die UI verwaltbar; splitbereinigter Einstandskurs bei Parqet-Sync
- **Parqet-Integration** — OAuth-Sync von Einstandskurs und Stückzahl, pro Depot eigene Client ID; Backup vor jedem Sync mit Rückgängig-Funktion
- **ATH-Prüfung** — vergleicht gespeicherte ATH-Werte mit Yahoo Finance (inkl. Watchlist-Aktien); Korrekturen direkt in der App möglich
- **XETRA-Unterstützung** — automatischer Ticker-Vorschlag für deutsche Handelsplätze
- **Apprise-Benachrichtigungen** — Alarm bei neuem Discount-Block, inkl. Kaufempfehlung, Nachkauf-Kennzeichnung (🛒) und Kursstand-Timestamp; HTML-formatiert für E-Mail-Versand; optionaler Bestätigungsmodus (2× Refresh vor Alarm); Apprise-URLs pro Benutzer, Ein/Aus-Schalter pro Depot
- **ATH-Alarm pro Aktie** — eigene Benachrichtigung bei neuem Allzeithoch, individuell pro Aktie aktivierbar (🔔-Symbol neben dem ATH-Wert), auch für Watchlist-Aktien, Standard: deaktiviert
- **Wöchentliche Zusammenfassung** — optionaler Wochenbericht per Apprise mit ATH-Verteilung, Nachkauf-Kandidaten, Wochenperformance und Sektor-Übersicht; HTML-formatiert für E-Mail-Versand; pro Depot aktivierbar
- **System-Status** — Gesundheits-Dashboard im Footer; zeigt Scheduler-Status, Laufzeit, Refresh-Statistiken, Yahoo Finance-Erfolgsquote und Fehler-Log der letzten 20 Abfragefehler
- **Verlauf** — vollständiger Aktivitätsverlauf mit Filter nach Benutzer und Eintragstyp
- **Letzte Änderungen** — Changelog direkt in der App abrufbar (Footer-Link)
- **Einstellungen per UI** — Zeitzone, Handelstage, -zeiten und Wochenbericht direkt in der App konfigurierbar
- **Dark / Light Mode**
- **Eigenes App-Icon** — inkl. iOS-Homescreen-Unterstützung
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
│   ├── index.html
│   └── icons/
│       ├── favicon.svg
│       ├── favicon.ico
│       ├── favicon-16x16.png
│       ├── favicon-32x32.png
│       └── apple-touch-icon.png
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

DepotRadar setzt mindestens ein Benutzerprofil voraus und unterstützt zusätzlich mehrere Profile, wenn mehrere Personen die App gemeinsam nutzen.

### Einrichtung

Beim ersten Start wird das erste Benutzerprofil angelegt — ein PIN ist dabei optional.

### Funktionsweise

- Jeder Benutzer hat einen optionalen 4-stelligen PIN
- Gibt es nur einen Benutzer ohne PIN, loggt die App ihn beim Öffnen automatisch ein — ganz ohne Auswahl-Screen
- Sobald ein PIN gesetzt ist oder mehrere Benutzer existieren, erscheint die Benutzerauswahl
- Nach dem Login sieht man nur die eigenen Depots und Watchlists
- Benachrichtigungs-Einstellungen (Apprise-URLs, Mention, Bestätigungsmodus) werden ausschließlich pro Benutzer konfiguriert — es gibt keine separate Depot-Ebene dafür
- Ein/Aus-Schalter und Wochenbericht-Teilnahme bleiben pro Depot konfigurierbar (unabhängig vom Benutzer-Modell, da ein Benutzer mehrere Depots mit unterschiedlichem Bedarf haben kann)
- Neue Depots werden automatisch dem eingeloggten Benutzer zugeordnet
- Jeder Benutzer kann neue Benutzer anlegen; eigene Einstellungen und PIN kann jeder selbst verwalten

-----

## Einstellungen (UI)

Alle Einstellungen sind unter **⚙ Einstellungen** erreichbar:

| Einstellung                   | Beschreibung                                              |
|-------------------------------|-----------------------------------------------------------|
| Automatischer Refresh         | Intervall der Kursabfragen                                |
| Zeitzone                      | Für korrekte Handelszeiten-Berechnung                     |
| Handelstage                   | An welchen Tagen aktualisiert wird                        |
| Handelszeiten                 | Zwischen welchen Uhrzeiten aktualisiert wird              |
| Wöchentliche Zusammenfassung  | Wochentag und Uhrzeit (Ein/Aus läuft pro Depot, siehe unten) |
| Verlaufsbereinigung           | Aufbewahrungszeitraum für Benachrichtigungshistorie       |
| Aktiensplits                  | Splits hinzufügen und verwalten                           |

Benachrichtigungen selbst werden **nicht** global geschaltet: Apprise-URLs, Mention und Bestätigungsmodus liegen ausschließlich beim Benutzer (Benutzer-Icon oben rechts), Ein/Aus sowie Wochenbericht-Teilnahme bleiben pro Depot (Depot-Einstellungen → ⚙).

-----

## Kaufempfehlung

Pro Depot kann ein optionales **Kaufbudget** in EUR hinterlegt werden (Depot-Einstellungen → ⚙).

| Discount-Block | Multiplikator | Beispiel bei 200 € Budget |
|----------------|---------------|---------------------------|
| 20–39%         | 1×            | 200 €                     |
| 40–59%         | 2×            | 400 €                     |
| ≥60%           | 3×            | 600 €                     |

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

## Diversifikations-Lücke

Das ⚖️-Symbol markiert Aktien aus Sektoren, die im Bestand unterrepräsentiert sind — als Orientierung für eine ausgewogenere Streuung über die Sektoren.

**Berechnung:** Ø Positionen pro Sektor = Gesamtzahl Aktien im Bestand ÷ Anzahl genutzter Sektoren. Ein Sektor gilt als unterrepräsentiert, wenn er weniger als 50% dieses Durchschnitts erreicht (fester Schwellenwert). Aktien ohne zugewiesenen Sektor werden nicht mitgezählt.

**Sichtbar an drei Stellen:**

- Am Sektor-Tag in Tabelle und Karten
- Als Ø-Hinweis in der Sektor-Übersicht
- Im ATH-Discount-Alarm (zusätzlich zu 🛒, falls beides zutrifft) — nicht beim separaten Neues-ATH-Alarm

**Watchlist-Aktien** werden immer gegen den echten Bestand bewertet, nicht gegen die Watchlist selbst — so zeigt das Symbol direkt, welche Watchlist-Titel eine tatsächliche Lücke im Depot füllen würden.

-----

## Aktiensplits

Splits werden in `data/splits.json` gespeichert und über **⚙ Einstellungen → Aktiensplits** verwaltet.

**Split hinzufügen:**
1. Einstellungen öffnen → „+ Split hinzufügen"
2. Aktie aus dem eigenen Bestand suchen und auswählen
3. Datum und Faktor (z.B. `10` für 10:1) eingeben
4. Speichern

-----

## Parqet-Integration

DepotRadar verbindet sich mit [Parqet](https://parqet.com) um Einstandskurse und Stückzahlen zu importieren. **Jedes Depot benötigt eine eigene Parqet-Integration.**

### Einrichtung

1. [developer.parqet.com/console/integrations](https://developer.parqet.com/console/integrations) → **+ New Integration**
2. Scope: nur **read portfolio** ankreuzen
3. Redirect URI: `http://DEINE-APP-URL/api/parqet/callback`
4. Client ID kopieren → in DepotRadar: Depot-Einstellungen → Client ID eintragen → Verbinden

### Backup & Rückgängig

Vor jedem Sync wird automatisch ein Backup der Depot-Datei angelegt. Rückgängig über **↩ Rückgängig** in den Depot-Einstellungen.

-----

## Benachrichtigungen (Apprise)

- **Apprise-URLs, Mention, Bestätigungsmodus** — ausschließlich pro Benutzer (Benutzer-Icon oben rechts → Bearbeiten)
- **Ein/Aus, Wochenbericht-Teilnahme** — pro Depot (Depot-Einstellungen → ⚙)

Unterstützte Dienste (Auswahl):

| Dienst      | URL-Format                                    |
|-------------|-----------------------------------------------|
| Telegram    | `tgram://TOKEN/CHATID`                        |
| Gotify      | `gotify://host/token`                         |
| ntfy        | `ntfy://host/topic`                           |
| Discord     | `discord://WEBHOOK_ID/TOKEN`                  |
| E-Mail      | `mailto://user:pass@gmail.com` (HTML-Format)  |
| Apprise API | `http://apprise.host/notify/tag`              |

**Bestätigungsmodus:** Eine Aktie muss zwei aufeinanderfolgende Refreshes unter dem ATH-Level liegen bevor ein Alarm ausgelöst wird. Beim Umschalten des Depot-Toggles für Benachrichtigungen (ein/aus) werden offene Bestätigungen automatisch zurückgesetzt, damit kein veralteter Zustand fälschlich als „bestätigt" gewertet wird.

-----

## Kursabfragen

- **Quelle:** Yahoo Finance (kostenlos, kein API-Key nötig)
- **Historische Daten:** 10 Jahre für ATH-Berechnung
- **Währungen:** Automatische EUR-Umrechnung via [Frankfurter API](https://www.frankfurter.app)
- **GBp-Fix:** Londoner Aktien in Pence werden automatisch in GBP umgerechnet

-----

## Versionshistorie

| Version | Beschreibung                                                                    |
|---------|---------------------------------------------------------------------------------|
| 2.7.7 / 2.9.6 | Hilfe erweitert: neue Abschnitte für Portfolio-Verlauf/EK-Kurve, Treemap-Ansicht und System-Status; veralteter Hinweis zur Depot-Ebene in der Apprise-Sektion entfernt |
| 2.7.6 / 2.9.3–2.9.5 | Ausstehende Bestätigungen werden jetzt korrekt protokolliert wenn der Kurs sich vor dem zweiten Refresh erholt; Übersichten unter gemeinsamem aufklappbaren Oberpunkt zusammengefasst; aktive Filter als farbige Pills im Header sichtbar |
| 2.7.5 / 2.9.0–2.9.2 | Depot-übergreifender Yahoo-Cache beim automatischen Refresh spart redundante API-Calls wenn identische Ticker in mehreren Depots vorkommen; System-Status zeigt Cache-Statistik; Statusdot im Footer (grün/grau/rot) |
| 2.7.3–2.7.4 / 2.8.5–2.8.9 | Invested-Capital-Kurve im Verlaufschart (gestrichelte EK-Linie); Treemap-Ansicht (Toggle im Depot-Header); System-Status / Gesundheits-Dashboard (Footer-Link); zweizeiliger Footer auf Mobilgeräten; Code-Cleanup und Bugfixes (Y-Achsen-Skala, Treemap-Namen) |
| 2.7.2 / 2.8.3–2.8.4 | Diversifikations-Lücke (⚖️) — Aktien aus unterrepräsentierten Sektoren werden markiert (Tabelle, Sektor-Übersicht, ATH-Discount-Alarm); Watchlist-Bewertung immer gegen den echten Bestand; Zeitstempel der ältesten Kursabfrage in der Portfolio-Übersicht |
| 2.7.1 / 2.8.2 | Performance-Badges umgestellt auf 1T/1M/3M/1J/3J (vorher 1T/1W/1M/3M); Logo oben links als Seite-Neu-Laden-Button |
| 2.7.0 / 2.8.0 | Benutzerprofil ist jetzt Pflicht, Single-User-ohne-PIN loggt automatisch ein, Benachrichtigungseinstellungen nur noch pro Benutzer (keine doppelte Depot-Ebene mehr), Bugfixes (Depot-Speichern, Wochenbericht-Quelle) |
| 2.6.0 / 2.7.45 | ATH-Alarm pro Aktie (neues Allzeithoch), individuell aktivierbar |
| 2.5.x / 2.7.2x–2.7.4x | Interaktiver Portfolio-Verlauf-Chart (antippen/hovern für exakte Werte), kompakte einklappbare Übersichten, Ein/Aus-Schalter pro Depot für Benachrichtigungen, Tastatur-Unterstützung für PIN-Eingabe, App-Icon, In-App-Changelog, atomare Datei-Schreibvorgänge, HTML-Escaping gegen gespeicherten XSS |
| 2.4.x   | Multi-User mit PIN, Depot/User-Verwaltung via Umgebungsvariablen                |
| 2.3.x   | Portfolio-Gewichtung, Portfolio-Verlauf (Snapshots), Code-Qualität              |
| 2.2.x   | Sektor-Tags mit Auto-Fetch, Sektor-Übersicht, Sektor-Filter                     |
| 2.1.x   | Wöchentliche Zusammenfassung (Apprise + HTML-E-Mail), Verlaufsbereinigung       |
| 2.0.x   | Bestätigungsmodus, Kursstand in Benachrichtigungen, Verlauf-Verbesserungen      |
| 1.9.x   | Nachkauf-Kandidaten in Benachrichtigungen (🛒), Nachkauf-Schwelle pro Depot     |
| 1.8.0   | Parqet-Sync Backup mit Rückgängig-Funktion                                      |
| 1.7.x   | Aktiensplits über UI verwaltbar                                                  |
| 1.6.x   | Kaufempfehlung in Benachrichtigungen, App und Tabelle                           |
| 1.5.0   | Zeitzone und Handelszeiten über UI einstellbar                                  |
| 1.4.x   | Parqet Client ID pro Depot                                                       |
| 1.3.0   | Nachkauf-Kandidaten Filter                                                       |
| 1.2.0   | Parqet OAuth PKCE Integration                                                    |
| 1.1.0   | XETRA-Ticker-Unterstützung                                                       |
| 1.0.0   | Erstes Release                                                                   |

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
