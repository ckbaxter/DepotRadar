# data/ – Übersicht der persistenten Dateien

Alle Laufzeitdaten von DepotRadar liegen als JSON-Dateien in diesem Verzeichnis (Docker-Volume `./data:/data`). Zugriff ausschließlich über `_load_json`/`_save_json` (atomares Schreiben via Temp-Datei + `os.replace`), in der Regel gekapselt in eigenen `load_X()`/`save_X()`-Funktionen in `app.py`.

| Datei | Zweck | Struktur | Schreibt | Liest |
|---|---|---|---|---|
| `xetra_map.json` | US-Ticker → bevorzugtes EUR-Listing (XETRA/Amsterdam etc.), self-expanding via OpenFIGI | `{TICKER: {ticker, name, exchange}}` | `save_xetra_map()` | `load_xetra_map()` |
| `depots.json` | Depot-Metadaten aller User | `[{id, name, …}]` | `save_depots()` | `load_depots()` |
| `depot_<id>.json` | Bestand eines Depots (dynamischer Dateiname, ein File pro Depot) | Liste von Stock-Objekten | `save_stocks()` | `load_stocks()` |
| `depot_<id>_backup.json` | Automatisches Backup vor jedem Parqet-Sync | wie `depot_<id>.json` | Dateikopie in `parqet_sync()` (kein JSON-Load/Save) | Undo-Route (`/api/depots/<id>/parqet/undo`) |
| `watchlists.json` | Watchlist-Metadaten (eigenständig seit v2.8.0, nicht mehr Teil eines Depots) | `[{id, name, notifications_enabled}]` | `save_watchlists()` | `load_watchlists()` |
| `wl_<id>.json` | Aktien einer Watchlist (dynamischer Dateiname) | Liste von Stock-Objekten | `save_wl_stocks()` | `load_wl_stocks()` |
| `splits.json` | Erfasste Aktiensplits | `[{isin, name, date, ratio}]`, `ratio` auch < 1 für Reverse Splits | `save_splits()` | `load_splits()` |
| `settings.json` | Globale Einstellungen (Zeitzone, Handelstage/-zeiten, Refresh-Intervall, Verlaufsbereinigung) | Dict | `save_settings()` — **zusätzlich 2 Stellen mit direktem `_save_json`** (Migrations-Marker) | `load_settings()` (merged Defaults) — **zusätzlich 2 Stellen mit direktem `_load_json`** (roher Dict ohne Default-Merge, für Migrations-Checks) |
| `users.json` | Benutzerprofile (PIN-Hash, Depot-/Watchlist-Zuordnung, Digest-Einstellungen) | Liste von User-Objekten | `save_users()` | `load_users()` |
| `snapshots.json` | Tägliche Portfolio-Gesamtwert-Punkte für den Verlaufschart | `[{date, depots: {<id>: {name, value, cost}}}]` | `save_snapshots()` | `load_snapshots()` |
| `notifications.json` | Verlauf/Benachrichtigungshistorie | Liste von Log-Einträgen | `save_notifications()` | `load_notifications()` |
| `health.json` | Kumulative Health-Zähler (Refreshes, Yahoo-Calls, Fehler, Cache-Hits) | Dict | `save_health()` | `load_health()` |
| `eur_rates.json` | Gecachte EUR-Wechselkurse (Frankfurter API) | `{currency: rate}` | `save_eur_rates()` | `load_eur_rates()` |
| `realized_gains.json` | Realisierte Gewinne/Verluste aus Parqet-Sell-Aktivitäten | Liste von Einträgen, je mit `depot_id` | `save_realized_gains()` | `load_realized_gains()` |
| `dividends.json` | Dividenden aus Parqet-Aktivitäten | Liste von Einträgen, je mit `depot_id` | `save_dividends()` | `load_dividends()` |

## Bekannte Ausnahmen

- **`settings.json`**: `load_settings()`/`save_settings()` decken den normalen Zugriff ab. Drei Stellen im Code umgehen das bewusst und lesen/schreiben den rohen Dict direkt (`_load_json`/`_save_json`) — u. a. für Migrations-Marker-Checks, wo der Default-Merge von `load_settings()` störend wäre. Nicht weiter vereinheitlicht (siehe `PROJECT_CONTEXT.md`).
- **`depot_<id>_backup.json`**: kein `_load_json`/`_save_json`-Zugriff, sondern eine reine Dateikopie vor dem Parqet-Sync — konzeptionell kein „Datenmodell", sondern ein Snapshot-Backup.

## Warum JSON statt Datenbank?

Bewusste Design-Entscheidung für die aktuelle Größenordnung (Homelab, überschaubare Anzahl User/Depots/Positionen) — kein ORM, keine zusätzliche Infrastruktur, einfach zu inspizieren und zu sichern (LXC-Snapshot reicht). Bekannte Schwachstelle: jede Schreibung lädt/schreibt die komplette Datei neu (siehe `CURRENT_STATE.md` → Technische Schulden). Bei aktueller Nutzung kein spürbares Problem; falls doch relevant, wäre Write-Debouncing/Batching der naheliegendere erste Schritt vor einem vollständigen DB-Wechsel.
