# Web-Image: nginx mit eingebackenem Frontend und eingebackener Konfiguration.
# Der Build-Kontext ist das Repo-Root (nicht ./nginx), weil frontend/ und nginx/nginx.conf gebraucht werden:
#   docker build -f nginx/Dockerfile -t depotradar-web .
FROM nginx:alpine

COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/ /usr/share/nginx/html/

EXPOSE 80
