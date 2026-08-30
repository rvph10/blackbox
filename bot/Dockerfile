FROM python:3.12-slim

WORKDIR /app

# Police pour les cartes générées (Pillow), voir bot/cards.py.
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

# Volume monté ici en prod (mapping Discord ↔ Jellyfin, état du cycle).
RUN mkdir -p /data
VOLUME ["/data"]

CMD ["python", "main.py"]
