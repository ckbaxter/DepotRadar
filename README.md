# DepotRadar

Ein selbst gehostetes Web-Tool zur Portfolio-Überwachung und ATH-Tracking von Aktien und ETFs in Euro.

Entwickelt für private Investoren die wissen wollen: Wie weit ist mein Portfolio gerade vom Allzeithoch entfernt — und welche Positionen lohnen sich zum Nachkauf?

![Version Backend](https://img.shields.io/badge/Backend-v2.8.50-blue)
![Version Frontend](https://img.shields.io/badge/Frontend-v2.13.84-blue)
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

- **Multi-User** — mehrere Benutzerprofile mit optionalem PIN (per Zahlenpad oder Tastatur eingebbar); jeder User sieht nur seine eigenen Depots und Watchlists; Admin-Rechte (Verlauf aller Benutzer, Benutzer anlegen/löschen) per `ADMIN_USERS`-Umgebungsvariable
- **Multi-Depot** — mehrere Depots pro Benutzer, jedes unabhängig konfigurierbar
- **Watchlists** — eigenständige Beobachtungslisten, direkt in der Tab-Leiste neben den Depots; können mehreren Benutzern zugeordnet werden (analog zu Depots), nicht an ein bestimmtes Depot gebunden
- **ATH-Discount** — farbcodierte Badges: grün (<20%), gelb (20–39%), orange (40–59%), rot (>60%) mit Multiplikator (1×/2×/3×)
- **Kompakte Übersichten** — ATH-, Portfolio- und Sektor-Übersicht sowie Portfolio-Verlauf in einer gemeinsam einklappbaren Ansicht, jede Sektion unabhängig auf-/zuklappbar
- **Portfolio-Gewichtung** — Balken und %-Wert pro Aktie zeigen die relative Gewichtung im Depot; sortierbar
- **Portfolio-Verlauf** — täglicher Snapshot des Gesamtwerts; interaktives Liniendiagramm mit Zeitraum-Filter (1W/1M/3M/6M/1J/Alles); Datenpunkte per Antippen/Hovern abrufbar (Datum + exakter Wert), lange Zeiträume werden automatisch reduziert; **Invested-Capital-Kurve** zeigt den kumulierten Einstandswert als gestrichelte Linie (nur bei Positionen mit bekanntem Einstandskurs); **ETF-Vergleichslinien** (MSCI World, S&P 500, DAX) über Chips ein-/ausblendbar — sobald mindestens eine aktiv ist, wechselt der Chart automatisch auf %-Veränderung seit Periodenbeginn statt absolutem €-Wert
- **Ansicht-Dropdown (Tabelle / Karten / Treemap / Kompakt)** — ein Dropdown in der Aktionsleiste schaltet zwischen vier Darstellungen um; die Wahl wird geräteunabhängig gemerkt (`localStorage`). Ohne bisherige Auswahl startet Mobile mit Karten, Desktop mit Tabelle
- **Kartenraster** — vollwertige Kartenansicht mit identischen Feldern wie die Tabelle; auf Mobilgeräten einspaltig gestapelt, auf Desktop als mehrspaltiges Grid
- **Treemap-Ansicht** — alternative Darstellung des Depots als Flächenkarte; Kachelgröße = Positionswert, Farbe = ATH-Discount-Stufe (nur Bestand, ab 2 Positionen, nicht für Watchlists)
- **Kompaktansicht** — eine Zeile pro Aktie mit nur Ticker, Kurs, Tagesperformance und ATH-Discount-Farbe; Schalter „Nur Auffällige" blendet Positionen ohne ausgelösten Discount-Alarm, neues Allzeithoch, Diversifikations-Lücke oder Nachkauf-Kandidat aus. Antippen einer Zeile öffnet das gleiche Aktien-Detail-Modal wie in den anderen Ansichten; auch für Watchlists verfügbar
- **Werkzeuge einklappbar** — Aktionsleiste und Sortierung lassen sich über einen Handle ein-/ausklappen (Standard: ausgeklappt), gilt für alle vier Ansichten gemeinsam; eingeklappt zeigt der Handle kompakt die aktive Ansicht und Sortierung an
- **Zeilenfarben** — Discount-Stufen werden als schmaler linker Farb-Akzent an Zeile bzw. Karte dargestellt; zusätzlich dezentes Zebra-Muster in der Depot-Tabelle für bessere Lesbarkeit
- **52-Wochen-Hoch/-Tief-Badge** — `52W-H`/`52W-T` neben den Performance-Badges, wenn der Kurs innerhalb 3% des 52-Wochen-Hochs bzw. -Tiefs liegt
- **SMA50/SMA200-Trendindikator** — Badge `▲/▼ SMA50 ±x%` (Abstand des Kurses zum 50-Tage-Durchschnitt) neben den Performance-Badges; bei einer Kreuzung SMA50↔SMA200 in den letzten 30 Tagen zusätzlich ein antippbares Badge `Golden Cross`/`Death Cross` mit Erklärung als Popover (funktioniert auch auf Touch-Geräten). Im Aktien-Detail-Modal gibt es SMA50-/SMA200-Overlays im Kursverlauf-Chart (per Chip schaltbar, Auswahl wird gemerkt) samt Cross-Markern sowie Kacheln für SMA50, SMA200 und Trend. Reiner Trendhinweis, keine Anlageempfehlung
- **Trendwechsel-Benachrichtigungen (Golden/Death Cross)** — pro Benutzer eine Einstellung (Benutzer bearbeiten → Zusammenfassungen → 🔀 Trendwechsel) für Tageszusammenfassung (Depot + gebündelte Watchlist-Zusammenfassung), optionalen Push („sobald bestätigt") und eine Zusatzzeile im Discount-Alarm. Bestätigung nach 1/2/3 Handelstagen (Standard 2), jeder Cross wird nur einmal gemeldet; Meldefenster N…N+5 Handelstage, damit ältere Crosses nach einem Update keine Meldungswelle auslösen. Trendwechsel zählen nicht als „Alarm(e)"; Verlauf-Typ `cross`
- **Aktien-Detail-Modal** — Klick auf den Aktiennamen (Tabelle, Karte oder Treemap-Kachel) öffnet ein Modal mit Sektor, ATH-Abstand/-Datum, 52-Wochen-Bereich, P&L, Performance-Badges, einem **Kursverlauf-Chart** (Zeiträume wie im Portfolio-Verlauf, Originalwährung, EK-Linie bei EUR-Aktien mit Einstandskurs) sowie einer kurzen Unternehmensbeschreibung (Wikipedia); zeigt zusätzlich 🛒 Nachkauf-Kandidat und/oder ⚖️ Sektor unterrepräsentiert als eigene Status-Zeile, sofern zutreffend (seit v2.13.42)
- **Kaufempfehlung** — pro Depot ein optionales Kaufbudget; bei Erreichen eines Discount-Blocks wird die empfohlene Stückzahl berechnet — in der App und in Benachrichtigungen
- **Nachkauf-Kandidaten** — filtert Aktien die günstig UND untergewichtet im Depot sind; Schwellenwert pro Depot einstellbar
- **Sektor-Tags** — automatische Sektor-Erkennung via Yahoo Finance; manuell anpassbar; Filter und Sektor-Übersicht in der Portfolio-Ansicht
- **Diversifikations-Lücke (⚖️)** — markiert Aktien aus Sektoren, die unterrepräsentiert sind (<50% des Sektor-Durchschnitts); sichtbar am Sektor-Tag in Tabelle/Karten, in der Sektor-Übersicht und im ATH-Discount-Alarm des Bestands; für Watchlists ist die Anzeige selbstreferenziell (Basis = die Watchlist selbst) und nicht Teil von Watchlist-Benachrichtigungen
- **Performance-Badges** — 1T / 1M / 3M / 1J / 3J direkt unter dem Kurs
- **P&L** — Gewinn/Verlust in % und € wenn Einstandskurs bekannt
- **Originalwährungsanzeige** — bei Fremdwährungsaktien (USD, GBP etc.) wird der Kurs in der Originalwährung klein und grau unter dem EUR-Kurs angezeigt, in Tabelle und Mobile-Card; EUR-Aktien bleiben unverändert
- **Kaufmarkierung (K)** — ATH-Level-Kacheln (−20%, −30% usw.) sind antippbar; ein Tippen setzt ein blaues K-Badge als persönliche Notiz auf welchem Level ein Kauf stattfand; mehrere Level gleichzeitig möglich, wird dauerhaft gespeichert
- **Aktiensplits** — über die UI verwaltbar; splitbereinigter Einstandskurs bei Parqet-Sync
- **Manuelle Positionserfassung** — Anzahl und Einstandskurs müssen nicht zwingend von Parqet stammen: optional direkt beim Hinzufügen einer Aktie im Bestand erfassbar, nachträglich änderbar über das „Aktie bearbeiten"-Modal (✎-Button, dort auch der Handelsplatz-Wechsel als Aufklapper). Ein P-Badge am Aktiennamen zeigt, ob die aktuellen Werte tatsächlich von Parqet stammen — manuell erfasste oder geänderte Werte tragen kein P. In Parqet-verbundenen Depots überschreibt der nächste Sync manuell geänderte Werte wieder (Modal warnt davor)
- **Parqet-Integration** — OAuth-Sync von Einstandskurs und Stückzahl, pro Depot eigene Client ID; Backup bei Sync mit tatsächlicher Änderung mit Rückgängig-Funktion; bei Parqet komplett verkaufte Positionen werden erkannt und erst nach Bestätigung (einzeln oder gesammelt über „Alle entfernen") aus dem ATH-Tracker gelöscht. **Automatischer Sync** (pro Depot in den Depot-Einstellungen konfigurierbar): Toggle + Intervall (Std.) + Zeitraum von/bis, läuft Mo–Fr zur vollen Stunde. Komplett entfernte Positionen lösen dabei obligatorisch einen Bestätigungs-Hinweis aus (Badge in der Kopfzeile, öffnet automatisch beim nächsten Besuch) sowie optional eine Apprise-Push
- **Erträge (Dividenden & realisierte Gewinne/Verluste)** — werden beim Parqet-Sync automatisch miterfasst (Datenquelle ausschließlich Parqet, keine manuelle Buchung); beide werden netto nach Steuer/Gebühr ausgewiesen. „💰 Erträge gesamt"-Kachel in der Portfolio-Übersicht öffnet ein Modal mit Typ-Filter (Alle/Dividenden/Verkäufe) und Aktien-Suche, die die Summen live umrechnet; zeigt auch bereits komplett verkaufte und aus dem Bestand entfernte Positionen. Kann die automatische Namensauflösung für eine ISIN ausnahmsweise keinen Treffer finden, lässt sich der Name direkt in der Zeile manuell nachtragen. Zusätzlich eine Monatsübersicht als Balkenchart (Jan–Dez, Jahres-Umschalter ‹ ›) mit Jahressumme unter den Balken — Dividenden grün, realisierte Gewinne/Verluste blau, Verluste in Rot unter der Nulllinie; reagiert auf denselben Typ-Filter und dieselbe Suche wie die Liste darunter
- **Rebalancing** — „⚖️ Rebalancing"-Kachel in der Portfolio-Übersicht zeigt Kauf-/Verkaufsempfehlungen, um alle Positionen im Bestand gleich zu gewichten (Ziel = 100% ÷ Anzahl Positionen); rein automatisch berechnet, keine manuelle Zielvorgabe pro Aktie nötig. Zweiter Modus verteilt ein optional hinterlegtes Kaufbudget proportional auf die unterrepräsentierten Positionen. Nicht für Watchlists verfügbar
- **ATH-Prüfung** — vergleicht gespeicherte ATH-Werte mit Yahoo Finance, verfügbar im Bestand und in jeder Watchlist; Korrekturen direkt in der App möglich
- **XETRA-Unterstützung** — bei der Aktiensuche wird automatisch das passende XETRA-Listing vorgeschlagen; bekannte Aktien sofort aus lokalem Cache (`xetra_map.json`), unbekannte dynamisch via OpenFIGI und dann gecacht. Seit v2.8.16–18 zusätzlich ein Hinweis, wenn Yahoo an sein Antwortlimit stößt und die Suche eventuell eingegrenzt werden sollte (Ticker/ISIN statt Firmenname)
- **Apprise-Benachrichtigungen** — Alarm bei neuem Discount-Block, inkl. Kaufempfehlung, Nachkauf-Kennzeichnung (🛒) und Kursstand-Timestamp; HTML-formatiert für E-Mail-Versand; optionaler Bestätigungsmodus (2× Refresh vor Alarm); Apprise-URLs pro Benutzer, Ein/Aus-Schalter pro Depot
- **ATH-Alarm pro Aktie** — eigene Benachrichtigung bei neuem Allzeithoch, individuell pro Aktie aktivierbar (🔔-Symbol neben dem ATH-Wert), auch für Watchlist-Aktien, Standard: deaktiviert
- **Wöchentliche Zusammenfassung** — optionaler Wochenbericht per Apprise mit Portfolio-Wochenperformance (Gesamtwert ggü. Vorwoche, seit v2.8.33), ATH-Verteilung, Nachkauf-Kandidaten, bestem/schlechtestem Einzelperformer und Sektor-Übersicht; HTML-formatiert für E-Mail-Versand; pro Depot aktivierbar
- **Tägliche Depot-Zusammenfassung** — optional pro Depot aktivierbar, läuft nur Montag–Freitag; fasst zusammen, welche Discount- und ATH-Alarme heute für dieses Depot gesendet wurden (auch als Meldung wenn keine Alarme vorlagen); nutzt dieselben Apprise-URLs wie normale Alarme
- **Watchlist-Zusammenfassung, gebündelt** — ein einziger Schalter im Benutzerprofil fasst alle Discount-/ATH-Alarme über sämtliche eigenen Watchlists in einer Nachricht zusammen (statt pro Watchlist einzeln), zur gleichen Uhrzeit wie die tägliche Depot-Zusammenfassung
- **Zeitplanung pro Benutzer** — Wochentag/Uhrzeit des Wochenberichts sowie die Uhrzeit der täglichen Zusammenfassung werden im eigenen Benutzerprofil eingestellt — jeder Benutzer im Haushalt kann so einen eigenen Zeitpunkt wählen
- **Hinweis-Center (seit 2.8.47 / 2.13.81)** — macht fehlgeschlagene Automatisierungen in der Oberfläche sichtbar: ⚠️-Badge mit Anzahl in der Kopfzeile (rot = Fehler, orange = Warnung, blau = „Aktion nötig“), Banner unter der Kopfzeile für handlungsrelevante Fehler (abgelaufener Zugang eines Benachrichtigungskanals, abgelaufene Parqet-Verbindung) und eine Liste mit Ursache, Beginn und Schaltflächen (Profil öffnen, Test senden, Neu verbinden, Jetzt prüfen). Erfasst werden Versandfehler je Apprise-URL (Auth-Fehler sofort; vorübergehende Fehler werden nach 5 und 10 Min. automatisch wiederholt und erst danach als Warnung gemeldet), fehlgeschlagene bzw. überfällige Tages-/Wochenzusammenfassungen und Parqet-Syncs, Datenquellen-Ausfälle, Refresh-Stillstand, gestoppter Scheduler sowie Parqet-Bestätigungen (komplett verkaufte Positionen). Hinweise lösen sich automatisch auf, sobald der nächste Versand/Lauf klappt; behobene bleiben 24 Std. sichtbar; „nicht gelaufen“ lässt sich zusätzlich mit „Gesehen“ ausblenden. Im Benutzerprofil zeigt jede URL ihren letzten Versandstatus. Persistenz in `data/issues.json` (URLs nur als Hash, nie im Klartext). API: `GET /api/issues?user_id=…`, `POST /api/issues/<id>/dismiss`
- **System-Status** — Gesundheits-Dashboard im Footer; zeigt Scheduler-Status, Laufzeit, Refresh-Statistiken, Yahoo Finance-Erfolgsquote, Yahoo-Cache-Trefferquote und Fehler-Log der letzten 20 Abfragefehler; „✕ Leeren"-Button setzt das Fehler-Log zurück. **Ausfall-Erkennung (seit 2.8.39):** fällt Yahoo Finance oder Parqet in 3 automatischen Refresh-Zyklen in Folge überwiegend aus (Frankfurter API/OpenFIGI nach 6), bekommen die Admins (`ADMIN_USERS`) einmalig einen Push und bei Wiederkehr eine Entwarnung mit Ausfalldauer; ein Wächter meldet, wenn in der Handelszeit länger als das Doppelte des Refresh-Intervalls kein Refresh mehr lief. Schwellen sind Konstanten in `app.py` (`_OUTAGE_SOURCES`, `_STALL_*`), der Zustand liegt nur im Speicher
- **Verlauf** — Aktivitätsverlauf mit Filter nach Eintragstyp, gruppiert nach Tages-Trennern (Heute/Gestern/Datum); Admins sehen die Ereignisse aller Benutzer und können zusätzlich nach Benutzer filtern, alle anderen sehen nur eigene Einträge und Systemereignisse
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
docker compose pull
docker compose up -d
```

Erreichbar unter: **<http://localhost:8080>**

### Aktualisieren

```bash
cd DepotRadar
git pull
docker compose pull
docker compose up -d
```

Deine Daten liegen im Ordner `data/` und bleiben bei Updates erhalten.

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
│   ├── changelog.json         # Änderungsverlauf + aktuelle Frontend- und Backend-Version (nginx cached die Datei nie)
│   └── icons/
│       ├── favicon.svg
│       ├── favicon.ico
│       ├── favicon-16x16.png
│       ├── favicon-32x32.png
│       └── apple-touch-icon.png
├── nginx/
│   └── nginx.conf
├── data/
│   ├── README.md              # Übersicht aller Dateien: Zweck, Struktur, Schreiber/Leser
│   ├── xetra_map.json         # XETRA-Ticker-Mapping (im Repo, selbst-erweiternd via OpenFIGI)
│   ├── depots.json            # Wird beim ersten Start automatisch angelegt
│   ├── depot_*.json
│   ├── depot_*_backup.json    # Backup vor Parqet-Sync (automatisch)
│   ├── watchlists.json        # Watchlist-Metadaten (eigenständig, nicht Teil von depots.json)
│   ├── wl_*.json              # Watchlist-Aktien (je Watchlist eine Datei)
│   ├── splits.json            # Aktiensplits (automatisch befüllt)
│   ├── settings.json
│   ├── users.json             # Benutzerprofile (wird beim ersten Start angelegt)
│   ├── snapshots.json         # Tägliche Portfolio-Snapshots
│   ├── notifications.json     # Verlauf / Benachrichtigungshistorie
│   ├── health.json            # Gesundheits-Statistiken (persistiert für System-Status)
│   ├── issues.json            # Hinweis-Center: Kanal-Status, Job-Register, Hinweis-Verlauf
│   ├── eur_rates.json         # Gecachte EUR-Wechselkurse
│   ├── realized_gains.json    # Realisierte Gewinne/Verluste aus Parqet-Sell-Aktivitäten
│   └── dividends.json         # Dividenden aus Parqet-Aktivitäten
└── docker-compose.yml
```

-----

## Konfiguration

### docker-compose.yml

```yaml
environment:
  - TZ=Europe/Berlin
  - APP_URL=http://depotradar.lan   # Eigene URL/IP — wichtig für Parqet OAuth
  - OPENFIGI_API_KEY=               # Optional — siehe unten
  - ADMIN_USERS=                    # Optional — Admin-Benutzer, siehe Administration
```

`APP_URL` muss auf die tatsächlich erreichbare Adresse zeigen.

### XETRA-Ticker-Suche (OpenFIGI)

Beim Hinzufügen einer Aktie schlägt DepotRadar automatisch das passende XETRA-Listing vor (z.B. AMZN → AMZ.DE). Bekannte Aktien werden sofort aus `data/xetra_map.json` geladen. Für unbekannte Aktien fragt das Backend die kostenlose [OpenFIGI API](https://www.openfigi.com) von Bloomberg ab und speichert das Ergebnis automatisch im lokalen Cache.

**Ohne API-Key:** 25 Anfragen/Minute — für den normalen Betrieb ausreichend, da jede Aktie nur einmal abgefragt und dann gecacht wird.

**Mit API-Key:** 250 Anfragen/Minute. Kostenlosen Key unter [openfigi.com](https://www.openfigi.com/api) registrieren und in `docker-compose.yml` eintragen:

```yaml
environment:
  - OPENFIGI_API_KEY=dein-key-hier
```

### Administration via Umgebungsvariablen

Die Administration läuft über Umgebungsvariablen in `docker-compose.yml`. `ADMIN_USERS` ist dabei eine **dauerhafte** Variable (bleibt gesetzt), `RESET_PIN_USER` und `DELETE_USER` sind **One-Shot**-Variablen: nach dem Ausführen wieder entfernen und neu starten.

#### Admins festlegen (`ADMIN_USERS`)

```yaml
environment:
  - ADMIN_USERS=Joe            # mehrere kommasepariert: Joe,Sina
```

Die genannten Benutzer (Match über den Benutzernamen) erhalten Admin-Rechte:

- **Verlauf**: Admins sehen die Ereignisse aller Benutzer inkl. Benutzer-Filter; alle anderen sehen nur ihre eigenen Einträge plus Systemereignisse
- **Benutzer anlegen**: nur durch Admins möglich (Ausnahme: der allererste Benutzer bei der Ersteinrichtung)
- **Benutzer löschen**: Admins können Benutzer direkt über die Benutzerverwaltung löschen (🗑) — mit Bestätigungsdialog, der vorab auflistet, welche exklusiv zugeordneten Depots/Watchlists mitgelöscht würden; Selbstlöschung und das Löschen des letzten Benutzers sind blockiert (dafür `DELETE_USER` nutzen)

Ist die Variable **nicht gesetzt**, gibt es keine Admins: jeder sieht im Verlauf nur eigene Einträge, und Benutzer können weder angelegt noch über die UI gelöscht werden (das Backend loggt beim Start einen entsprechenden Hinweis).

**Hinweise:** Wird ein Admin-Benutzer umbenannt, muss die Variable nachgezogen werden, sonst verliert er die Admin-Rechte. Und ehrlich eingeordnet: DepotRadar hat keine Sessions/Tokens — die Admin-Trennung ist Komfort und Aufgeräumtheit im Haushalts-Einsatz, keine harte Zugriffskontrolle gegen technisch versierte Mitbenutzer im selben Netz.

#### PIN eines Benutzers zurücksetzen

```yaml
environment:
  - RESET_PIN_USER=Joe
```

Beim nächsten Start wird der PIN des Benutzers `Joe` gelöscht — er kann sich danach ohne PIN einloggen und einen neuen setzen. **Variable anschließend entfernen und neu starten.**

#### Benutzer löschen

```yaml
environment:
  - DELETE_USER=Sina
```

Beim nächsten Start wird der Benutzer `Sina` aus `users.json` entfernt. Depots **und Watchlists**, die **ausschließlich** diesem Benutzer gehörten, werden vollständig gelöscht (inkl. Aktien-Dateien). Depots/Watchlists, die mehreren Benutzern zugeordnet waren, bleiben erhalten. **Variable anschließend entfernen und neu starten.**

Alternativ können Admins Benutzer direkt über die UI löschen (siehe `ADMIN_USERS`). Die Env-Variable bleibt relevant für Selbstlöschung und für den Fall, dass kein Admin erreichbar ist.

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
- Nach dem Login sieht man ausschließlich die eigenen (zugeordneten) Depots und Watchlists — ohne Zuordnung zeigt die App eine leere Ansicht mit Hinweis zum Anlegen. Nicht zugeordnete Depots sind für niemanden sichtbar; zuordnen lassen sie sich über die Auswahl beim Anlegen eines neuen Benutzers (erscheint nur, solange unzugeordnete Depots existieren) oder direkt in der `users.json`
- Benachrichtigungs-Einstellungen (Apprise-URLs, Mention, Bestätigungsmodus) werden ausschließlich pro Benutzer konfiguriert — es gibt keine separate Depot-Ebene dafür
- Wochentag/Uhrzeit des Wochenberichts sowie die Uhrzeit der täglichen Depot-Zusammenfassung liegen ebenfalls auf dem Benutzer (Standard: Sonntag 20:00 bzw. 21:00) — jeder Benutzer kann so einen eigenen Zeitpunkt wählen
- Ein/Aus-Schalter sowie Wochenbericht-/Tageszusammenfassung-Teilnahme bleiben pro Depot konfigurierbar (unabhängig vom Benutzer-Modell, da ein Benutzer mehrere Depots mit unterschiedlichem Bedarf haben kann)
- Das Benutzer-Bearbeiten-Formular ist in aufklappbare Sektionen gegliedert (👤 Profil, 🔔 Benachrichtigungen, 🕘 Zusammenfassungen)
- Neue Depots werden automatisch dem eingeloggten Benutzer zugeordnet; die Depot-Zuordnungsauswahl beim Neu-Anlegen eines Benutzers erscheint nur, solange es unzugeordnete Depots gibt
- Watchlists sind eigenständig und werden — genau wie Depots — direkt Benutzern zugeordnet (neue Watchlists automatisch dem eingeloggten Benutzer, mehrere Benutzer pro Watchlist möglich); sie sind nicht an ein bestimmtes Depot gebunden
- Neue Benutzer anlegen und bestehende löschen können nur Admins (siehe `ADMIN_USERS` unter Administration); eigene Einstellungen und PIN kann jeder selbst verwalten

-----

## Einstellungen (UI)

Alle Einstellungen sind unter **⚙ Einstellungen** erreichbar:

| Einstellung                   | Beschreibung                                              |
|-------------------------------|-----------------------------------------------------------|
| Automatischer Refresh         | Intervall der Kursabfragen                                |
| Zeitzone                      | Für korrekte Handelszeiten-Berechnung                     |
| Handelstage                   | An welchen Tagen aktualisiert wird                        |
| Handelszeiten                 | Zwischen welchen Uhrzeiten aktualisiert wird              |
| Verlaufsbereinigung           | Aufbewahrungszeitraum für Benachrichtigungshistorie       |
| Aktiensplits                  | Splits hinzufügen und verwalten                           |

Benachrichtigungen selbst werden **nicht** global geschaltet: Apprise-URLs, Mention und Bestätigungsmodus liegen ausschließlich beim Benutzer (Benutzer-Icon oben rechts). Dort werden auch Wochentag/Uhrzeit des Wochenberichts, die Uhrzeit der täglichen Depot-Zusammenfassung sowie der Schalter für die gebündelte Watchlist-Zusammenfassung eingestellt (pro Benutzer, Standard So 20:00 bzw. 21:00, Watchlist-Zusammenfassung Standard aus). Ein/Aus sowie Wochenbericht-/Tageszusammenfassung-Teilnahme bleiben pro Depot (Depot-Einstellungen → ⚙).

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

Der Schwellenwert (Standard 30%) ist **pro Depot** einstellbar. In Watchlists wird der Filter seit v2.13.14 gar nicht mehr angeboten: er setzt Einstandskurs und Stückzahl voraus, die Watchlist-Aktien nicht haben.

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
- Im ATH-Discount-Alarm des Bestands (zusätzlich zu 🛒, falls beides zutrifft) — nicht beim separaten Neues-ATH-Alarm

**Watchlists:** Da Watchlists keinem Depot zugeordnet sind, gibt es dort keine automatische Vergleichsbasis — die Anzeige in einer Watchlist bewertet gegen die Watchlist selbst statt gegen ein Depot. In Watchlist-Benachrichtigungen (Apprise) erscheint ⚖️ nicht.

-----

## Rebalancing

Die „⚖️ Rebalancing"-Kachel in der Portfolio-Übersicht zeigt, wie viele Positionen von einer **Gleichgewichtung** abweichen — jede Position im Bestand soll rechnerisch gleich viel wert sein.

**Berechnung:** Ziel-Gewicht pro Position = 100% ÷ Anzahl Positionen mit bekanntem Kurs und Bestand (dieselbe Basis wie die Portfolio-Gewichtung). Verschiebt sich automatisch, wenn Positionen hinzukommen oder wegfallen — keine manuelle Zielvorgabe pro Aktie nötig. Nur Abweichungen ab 2 %-Punkten werden angezeigt, der Rest gilt als „im Rahmen der Toleranz".

**Zwei Ansichten im Modal:**

- **Anzeige** — jede abweichende Position mit IST-/Ziel-Balken, Kauf- oder Verkaufsempfehlung (Stückzahl + ≈-Betrag). Die Berechnung berücksichtigt, dass die Transaktion selbst den Depot-Gesamtwert verschiebt, damit die Zielquote danach exakt stimmt
- **Mit Kaufbudget** — ein in den Depot-Einstellungen hinterlegtes Kaufbudget wird proportional zum jeweils benötigten Kaufbetrag auf die unterrepräsentierten Positionen verteilt (nur Käufe; Verkaufsempfehlungen bleiben unverändert). Reicht der zugeteilte Anteil einer Position nicht für ein ganzes Stück, wird das mit einem Hinweis angezeigt statt die Position kommentarlos wegzulassen

Verkaufsempfehlungen sind reine Anzeige — es wird keine Stückzahl automatisch reduziert, das bleibt wie bisher dem „Aktie bearbeiten"-Modal oder dem nächsten Parqet-Sync vorbehalten.

**Watchlists:** nicht verfügbar (kein Einstandskurs/Stückzahl).

-----

## Aktiensplits

Splits werden in `data/splits.json` gespeichert und über **⚙ Einstellungen → Aktiensplits** verwaltet. Die Liste gruppiert nach Aktie — Antippen einer Zeile klappt die einzelnen Splits auf.

**Split hinzufügen (mit Vorschlägen):**
1. Einstellungen öffnen → „+ Split hinzufügen"
2. Aktie aus dem eigenen Bestand suchen und auswählen
3. Historische Splits werden automatisch von Yahoo Finance geladen und als Vorschläge angezeigt — einzeln an-/abwählbar, Datum und Faktor vor dem Übernehmen korrigierbar; bereits erfasste Splits sind als vorhanden markiert
4. „Ausgewählte übernehmen" — oder alternativ Datum und Faktor manuell eintragen und speichern

**Reverse Splits** (Aktienzusammenlegungen) werden unterstützt: Faktor < 1 eingeben, z.B. `0,1667` für eine 1:6-Zusammenlegung. Die Anzeige erfolgt entsprechend als `1:6`.

Bei XETRA-Zweitlistings werden die Vorschläge automatisch über das Original-Listing abgefragt (z.B. NVDA statt des .DE-Tickers), da Yahoo Split-Daten dort zuverlässiger liefert.

-----

## Parqet-Integration

DepotRadar verbindet sich mit [Parqet](https://parqet.com) um Einstandskurse und Stückzahlen zu importieren. **Jedes Depot benötigt eine eigene Parqet-Integration.**

### Einrichtung

1. [developer.parqet.com/console/integrations](https://developer.parqet.com/console/integrations) → **+ New Integration**
2. Scope: nur **read portfolio** ankreuzen
3. Redirect URI: `http://DEINE-APP-URL/api/parqet/callback`
4. Client ID kopieren → in DepotRadar: Depot-Einstellungen → Client ID eintragen → Verbinden

### Portfolio-Auswahl

Hat der verbundene Parqet-Account mehrere Portfolios, wird nach dem Verbinden eines ausgewählt. Der Name des gewählten Portfolios steht danach dauerhaft im Status; über **Portfolio wechseln** lässt sich die Auswahl jederzeit nachträglich ändern (Bestätigungsdialog weist darauf hin, dass der nächste Sync dann gegen das neu gewählte Portfolio abgleicht).

### Token-Erneuerung

Der Access Token ist bei Parqet nur kurzlebig (ca. 1 Stunde) und wird beim nächsten Sync automatisch im Hintergrund erneuert, sobald er abgelaufen ist — unbemerkt, ohne Verzögerung oder Meldung. Der zugehörige Refresh Token ist laut offizieller Parqet-Auskunft Single-Use (bei jeder Erneuerung wird ein neuer ausgestellt) und läuft nur bei **60 Tagen Inaktivität** ab — bei regelmäßiger Nutzung hält die Verbindung damit unbegrenzt. Schlägt die Erneuerung dennoch fehl, erscheint im Status „🔒 Token abgelaufen" mit der Option **Neu verbinden**.

### Backup & Rückgängig

Ein Backup der Depot-Datei wird nur angelegt, wenn ein Sync tatsächlich etwas ändert (Aktualisierungen oder neue Positionen) — bei einem Lauf ohne Änderungen bleibt ein bestehendes Backup unangetastet. Rückgängig über **↩ Rückgängig** in den Depot-Einstellungen.

### Automatischer Sync

Pro Depot in den Depot-Einstellungen (Parqet-Sektion) konfigurierbar: Toggle „Automatischer Sync", Intervall in Stunden sowie ein Zeitraum von/bis. Läuft Montag bis Freitag, immer zur vollen Stunde innerhalb des gewählten Zeitraums, im gewählten Intervall-Raster ab der Start-Stunde (z.B. Start 6 Uhr, Intervall 4h → 6/10/14/18/22 Uhr). Werden dabei komplett bei Parqet verkaufte Positionen erkannt, verschwindet der Bestätigungs-Hinweis nicht ungesehen: er wird gespeichert und erscheint als Badge in der Kopfzeile (antippbar) sowie automatisch als Modal beim nächsten Besuch der Ansicht — zusätzlich geht dafür obligatorisch eine Apprise-Push-Benachrichtigung raus, sofern Apprise-URLs konfiguriert sind.

-----

## Benachrichtigungen (Apprise)

- **Apprise-URLs, Mention, Bestätigungsmodus, Zeitplan (Wochenbericht-Tag/-Uhrzeit, Uhrzeit der täglichen Zusammenfassung)** — ausschließlich pro Benutzer (Benutzer-Icon oben rechts → Bearbeiten, gegliedert in die Sektionen 👤 Profil / 🔔 Benachrichtigungen / 🕘 Zusammenfassungen)
- **Ein/Aus, Wochenbericht-/Tageszusammenfassung-Teilnahme** — pro Depot (Depot-Einstellungen → ⚙); Watchlists haben einen eigenen Ein/Aus-Schalter, nehmen aber grundsätzlich nicht an der Tages-/Wochenzusammenfassung teil (bleiben reine Einzel-Alarme)
- Die tägliche Depot-Zusammenfassung läuft grundsätzlich nur Montag–Freitag

Erlaubte Dienste (seit v2.8.40 bewusst eingeschränkt — Apprise kann sonst per `json://`, `form://` oder `http(s)://` beliebige Requests aus dem Container senden):

| Dienst      | URL-Format                                    |
|-------------|-----------------------------------------------|
| ntfy        | `ntfy://host/topic` bzw. `ntfys://host/topic` (HTTPS) |
| Discord     | `discord://WEBHOOK_ID/TOKEN`                  |
| E-Mail      | `mailtos://user:pass@gmail.com` (HTML-Format) |

Gespeicherte URLs enthalten Zugangsdaten und werden im Benutzer-Formular nur **maskiert** angezeigt (z. B. `discord://•••/•••`); zum Ändern die URL entfernen und neu hinzufügen. Jede URL lässt sich einzeln testen. Änderungen an der URL-Liste gelten erst nach **Speichern**: neue URLs sind bis dahin als „Noch nicht gespeichert“ markiert, entfernte durchgestrichen (mit „Rückgängig“), und der Speichern-Button zeigt die Anzahl offener Änderungen. Bereits gespeicherte URLs anderer Dienste (z. B. Telegram, Gotify) werden nicht mehr bedient und im Formular als „nicht erlaubt" markiert.

**Bestätigungsmodus:** Eine Aktie muss zwei aufeinanderfolgende Refreshes unter dem ATH-Level liegen bevor ein Alarm ausgelöst wird. Beim Umschalten des Depot-Toggles für Benachrichtigungen (ein/aus) werden offene Bestätigungen automatisch zurückgesetzt, damit kein veralteter Zustand fälschlich als „bestätigt" gewertet wird.

-----

## Kursabfragen

- **Quelle:** Yahoo Finance (kostenlos, kein API-Key nötig)
- **Historische Daten:** 10 Jahre für ATH-Berechnung
- **Währungen:** Automatische EUR-Umrechnung via [Frankfurter API](https://www.frankfurter.app)
- **GBp-Fix:** Londoner Aktien in Pence werden automatisch in GBP umgerechnet
- **XETRA-Lookup:** [OpenFIGI API](https://www.openfigi.com) (Bloomberg) für dynamische XETRA-Ticker-Zuordnung; kostenlos, optionaler API-Key für höheres Rate-Limit

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
