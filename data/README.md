# data/ – Persistente Daten

Alle Laufzeitdaten von DepotRadar liegen hier als einfache JSON-Dateien (Docker-Volume `./data:/data`). Bewusst keine Datenbank — passend zur Design-Philosophie des Projekts: kein Build-Step, kein ORM, leicht zu inspizieren und zu sichern. Alle Schreibzugriffe erfolgen atomar (Temp-Datei + Rename), sodass ein Absturz mitten im Schreiben keine korrupte Datei hinterlässt.

Die meisten Dateien werden beim ersten Start automatisch mit sinnvollen Defaults angelegt — für den Betrieb muss hier nichts manuell erstellt werden.

## Dateien

| Datei | Zweck | Struktur |
|---|---|---|
| `xetra_map.json` | Mapping von US-Tickern auf ihr bevorzugtes EUR-Listing (z. B. XETRA), self-expanding via OpenFIGI. Einzige Datei mit Seed-Daten im Repository. | `{TICKER: {ticker, name, exchange}}` |
| `depots.json` | Metadaten aller Depots | Liste von Depot-Objekten |
| `depot_<id>.json` | Bestand eines einzelnen Depots (eine Datei pro Depot) | Liste von Stock-Objekten |
| `depot_<id>_backup.json` | Automatisches Backup vor jedem Parqet-Sync | wie `depot_<id>.json` |
| `watchlists.json` | Metadaten aller Watchlists | Liste von Watchlist-Objekten |
| `wl_<id>.json` | Aktien einer einzelnen Watchlist | Liste von Stock-Objekten |
| `splits.json` | Erfasste Aktiensplits | Liste von Split-Einträgen |
| `settings.json` | Globale Einstellungen (Zeitzone, Handelstage/-zeiten, Refresh-Intervall) | Dict |
| `users.json` | Benutzerprofile (PIN-Hash, Depot-/Watchlist-Zuordnung) | Liste von User-Objekten |
| `snapshots.json` | Tägliche Portfolio-Gesamtwert-Punkte für den Verlaufschart | Liste von Snapshot-Einträgen |
| `notifications.json` | Benachrichtigungsverlauf | Liste von Log-Einträgen |
| `health.json` | Kumulative Statistiken für den System-Status | Dict |
| `eur_rates.json` | Gecachte EUR-Wechselkurse | `{Währung: Kurs}` |
| `realized_gains.json` | Realisierte Gewinne/Verluste aus Parqet-Verkäufen | Liste von Einträgen |
| `dividends.json` | Dividenden aus Parqet-Aktivitäten | Liste von Einträgen |

## Backup

Da alle Daten als reguläre JSON-Dateien vorliegen, genügt eine normale Dateisicherung des gesamten `data/`-Verzeichnisses (z. B. Snapshot oder `rsync`) für ein vollständiges Backup — kein Datenbank-Dump nötig.

## Hinweis für Mitwirkende

`data/` ist komplett in `.gitignore` ausgeschlossen, da hier ausschließlich Lauf­zeit- und Nutzerdaten liegen. `xetra_map.json` und diese README sind bewusste Ausnahmen und müssen mit `git add -f` versioniert werden.
