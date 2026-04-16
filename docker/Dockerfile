# =============================================================================
# Dockerfile — API Flask + Celery Worker/Beat
# =============================================================================
FROM python:3.11-slim

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python Docker
COPY requirements_docker.txt .
RUN pip install --no-cache-dir -r requirements_docker.txt

COPY . .

# Créer les dossiers nécessaires
RUN mkdir -p data

EXPOSE 5000

CMD ["python", "api/app.py"]