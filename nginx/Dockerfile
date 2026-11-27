# Web-Image: nginx mit eingebackenem Frontend und eingebackener Konfiguration.
# Der Build-Kontext ist das Repo-Root (nicht ./nginx), weil frontend/ und nginx/nginx.conf gebraucht werden:
#   docker build -f nginx/Dockerfile -t depotradar-web .
FROM nginx:alpine

COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/ /usr/share/nginx/html/

EXPOSE 80

# Lebenszeichen (seit Frontend v2.13.99): nginx liefert eine statische Datei aus. Prüft nur das
# Web-Image selbst, nicht das Backend (das hat einen eigenen Healthcheck).
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/changelog.json || exit 1
