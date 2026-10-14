# DepotRadar — Aufgaben-Runner für die wiederkehrenden Befehle (Prüfen, Versionen, Deploy, Release).
# Es gibt keinen Build-Step und keine Tests; dieses Makefile fasst nur Befehlsketten zusammen.
#
# Überschreibbare Variablen (z. B. `make logs SERVICE=nginx`):
#   SERVICE  Compose-Service, dessen Logs `logs` zeigt          (Standard: backend)
#   COMPOSE  Compose-Aufruf                                     (Standard: docker compose)
#   PYTHON   Python-Interpreter                                 (Standard: python3)
#   BRANCH   Branch, den `cleanup` löscht                       (ohne Standard)
#   CONFIRM  `yes` überspringt die Rückfrage von `release`      (Standard: leer)
#
# Versionen werden nie hier gepflegt, sondern in frontend/changelog.json (siehe scripts/sync-version.py).

SHELL := /bin/bash
.DEFAULT_GOAL := help

SERVICE   ?= backend
COMPOSE   ?= docker compose
# Entwickler-Override: baut beide Images aus dem Klon statt sie von ghcr.io zu laden
BUILD_FILES := -f docker-compose.yml -f docker-compose.build.yml
PYTHON    ?= python3
CHANGELOG := frontend/changelog.json

.PHONY: help check check-py check-js check-version sync version deploy logs release release-tag release-backend release-frontend cleanup

help: ## Diese Übersicht anzeigen
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  make %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

check: check-py check-js check-version ## Alle Prüfungen (Python, JavaScript, Versionen)
	@echo "✓ Alle Prüfungen bestanden"

check-py: ## Python prüfen: ast.parse + pyflakes auf backend/app.py
	@$(PYTHON) -c "import ast; ast.parse(open('backend/app.py', encoding='utf-8').read())"
	@$(PYTHON) -m pyflakes --version >/dev/null 2>&1 || { echo "✗ pyflakes fehlt: $(PYTHON) -m pip install pyflakes (ggf. mit --break-system-packages oder in einem venv)"; exit 1; }
	@$(PYTHON) -m pyflakes backend/app.py
	@echo "✓ Python"

check-js: ## JavaScript prüfen: node --check auf dem Script-Block der frontend/index.html
	@command -v node >/dev/null 2>&1 || { echo "✗ node fehlt"; exit 1; }
	@D=$$(mktemp -d "$${TMPDIR:-/tmp}/depotradar-js.XXXXXX") && trap 'rm -rf "$$D"' EXIT && \
	awk '/<script>/{f=1; next} /<\/script>/{f=0} f' frontend/index.html > "$$D/script.js" && \
	{ [ -s "$$D/script.js" ] || { echo "✗ Kein <script>-Block in frontend/index.html gefunden"; exit 1; }; } && \
	node --check "$$D/script.js" && echo "✓ JavaScript"

check-version: ## Versionen prüfen (changelog.json ↔ app.py ↔ README-Badges), ändert nichts
	@$(PYTHON) scripts/sync-version.py --check

sync: ## Versionen aus changelog.json nach app.py und README übertragen (davor und danach Check)
	-@$(PYTHON) scripts/sync-version.py --check
	@$(PYTHON) scripts/sync-version.py
	@$(PYTHON) scripts/sync-version.py --check

version: ## Backend- und Frontend-Version aus frontend/changelog.json anzeigen
	@$(PYTHON) -c "import json; d = json.load(open('$(CHANGELOG)', encoding='utf-8')); print('Backend  v' + d['backend_version']); print('Frontend v' + d['frontend_version'])"

deploy: ## Backend- und Web-Image lokal neu bauen und die Container neu erstellen (auf dem Server)
	$(COMPOSE) $(BUILD_FILES) build --no-cache
	$(COMPOSE) $(BUILD_FILES) up -d --force-recreate

logs: ## Backend-Logs verfolgen (letzte 100 Zeilen, Abbruch mit Strg+C)
	$(COMPOSE) logs -f --tail=100 $(SERVICE)

release: ## (nur Hinweis) Es gibt zwei Images: make release-backend oder make release-frontend
	@echo "✗ Bitte make release-backend (Backend-Image) oder make release-frontend (Web-Image) verwenden"; exit 1

release-backend: PART := backend
release-backend: IMAGE_NAME := Backend-Image
release-backend: release-tag ## Tag backend-v<Version> setzen und pushen (baut das Backend-Image)

release-frontend: PART := frontend
release-frontend: IMAGE_NAME := Web-Image
release-frontend: release-tag ## Tag frontend-v<Version> setzen und pushen (baut das Web-Image)

# Gemeinsame Rezeptur der beiden Release-Targets (PART = backend|frontend kommt vom aufrufenden Target)
release-tag: check-version
	@set -e; \
	V=$$($(PYTHON) -c "import json; print(json.load(open('$(CHANGELOG)', encoding='utf-8'))['$(PART)_version'])") || { echo "✗ $(PART)_version aus $(CHANGELOG) nicht lesbar"; exit 1; }; \
	TAG="$(PART)-v$$V"; \
	[ "$$(git rev-parse --abbrev-ref HEAD)" = "main" ] || { echo "✗ Nicht auf main (git checkout main && git pull)"; exit 1; }; \
	git diff --quiet HEAD -- backend/app.py README.md $(CHANGELOG) || { echo "✗ Lokale Änderungen an app.py, README.md oder changelog.json (die Versionsprüfung liest diese Dateien)"; exit 1; }; \
	REMOTE_MAIN=$$(git ls-remote origin refs/heads/main) || { echo "✗ origin nicht erreichbar (git ls-remote origin schlug fehl)"; exit 1; }; \
	REMOTE_MAIN=$$(printf '%s' "$$REMOTE_MAIN" | cut -f1); \
	[ "$$(git rev-parse HEAD)" = "$$REMOTE_MAIN" ] || { echo "✗ main weicht von origin/main ab (git pull bzw. git push)"; exit 1; }; \
	if git rev-parse -q --verify "refs/tags/$$TAG" >/dev/null; then echo "✗ Tag $$TAG existiert lokal bereits (anderer Stand als origin? git tag -d $$TAG)"; exit 1; fi; \
	REMOTE_TAG=$$(git ls-remote --tags origin "refs/tags/$$TAG") || { echo "✗ origin nicht erreichbar (git ls-remote --tags origin schlug fehl)"; exit 1; }; \
	[ -z "$$REMOTE_TAG" ] || { echo "✗ Tag $$TAG existiert bereits auf origin"; exit 1; }; \
	$(PYTHON) scripts/sync-version.py --check --tag "$$TAG" || { echo "✗ Versionsprüfung für $$TAG fehlgeschlagen"; exit 1; }; \
	echo "Release: $$TAG auf $$(git rev-parse --short HEAD)"; \
	if [ "$(CONFIRM)" != "yes" ]; then \
		printf 'Tag setzen und pushen (startet den Build des $(IMAGE_NAME)s)? [j/N] '; \
		read -r A || A=""; \
		case "$$A" in j|J|y|Y) ;; *) echo "Abgebrochen."; exit 1;; esac; \
	fi; \
	git tag "$$TAG" || { echo "✗ git tag fehlgeschlagen"; exit 1; }; \
	git push origin "$$TAG" || { echo "✗ Push von $$TAG fehlgeschlagen (lokalen Tag entfernen mit: git tag -d $$TAG)"; exit 1; }; \
	echo "✓ $$TAG gepusht – das $(IMAGE_NAME) wird in GitHub Actions gebaut"

cleanup: ## Nach dem Merge: main aktualisieren, Branch löschen (make cleanup BRANCH=feature/xyz)
	@[ -n "$(BRANCH)" ] || { echo "✗ BRANCH fehlt, z. B.: make cleanup BRANCH=feature/makefile"; exit 1; }
	@[ "$(BRANCH)" != "main" ] || { echo "✗ main wird nicht gelöscht"; exit 1; }
	git checkout main
	git pull
	git branch -d "$(BRANCH)"
