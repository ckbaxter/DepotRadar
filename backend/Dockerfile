FROM python:3.15-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py xetra_seed.json ./

EXPOSE 5000

CMD ["python", "app.py"]
