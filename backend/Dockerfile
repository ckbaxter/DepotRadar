FROM python:3.15-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py xetra_seed.json ./

EXPOSE 5000

# Lebenszeichen über den schlanken Endpunkt /api/ping (seit v2.8.64): unhealthy, wenn das Backend
# nicht antwortet oder der Scheduler steht. Docker startet einen unhealthy Container nicht von
# selbst neu — der Status ist in `docker ps` sichtbar.
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/api/ping', timeout=4).status == 200 else 1)"]

CMD ["python", "app.py"]
