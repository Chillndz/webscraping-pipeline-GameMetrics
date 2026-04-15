FROM python:3.11-slim

WORKDIR /app

# Dépendances système pour Playwright et psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer le navigateur Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Copier le code
COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p data scraper/.scrapy_jobs

EXPOSE 5000

CMD ["python", "api/app.py"]
