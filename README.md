# 🎮 GameMetrics — Observatoire des Jeux Vidéo
**ENSEA AS Data Science — Projet Web Scraping Pipeline**

---

## 🗂️ Structure du projet

```
webscraping-pipeline-GameMetrics/
├── .env                          ← Variables d'environnement (ne pas committer)
├── docker-compose.yml
├── import_to_db.py               ← Script d'import données → PostgreSQL
├── requirements.txt              ← Dépendances Python locales
├── requirements_docker.txt       ← Dépendances Python Docker
│
├── api/
│   ├── __init__.py
│   ├── app.py                    ← Flask + Swagger + Prometheus
│   ├── models.py                 ← SQLAlchemy Game model
│   └── routes.py                 ← 8 endpoints REST
│
├── tasks/
│   ├── __init__.py
│   └── celery_worker.py          ← 3 tâches Celery + Beat schedule
│
├── scraper/
│   ├── scrapy.cfg
│   ├── clean_data.py             ← Nettoyage pandas raw_data.json → clean_data.csv
│   └── metacritic/
│       ├── items.py
│       ├── settings.py
│       ├── pipelines.py
│       └── spiders/
│           └── metacritic_spider.py
│
├── database/
│   └── init.sql                  ← Schéma PostgreSQL + 3 vues
│
├── docker/
│   └── Dockerfile
│
├── monitoring/
│   ├── prometheus.yml            ← Config Prometheus (minuscule !)
│   └── grafana/
│       ├── provisioning/
│       │   ├── datasources/datasources.yml   ← PostgreSQL + Prometheus
│       │   └── dashboards/dashboards.yml
│       └── dashboards/
│           └── gamemetrics.json  ← Dashboard complet 16 panels
│
└── data/
    ├── raw_data.json             ← Données brutes scraper
    └── clean_data.csv            ← Données nettoyées
```

---

##  Étapes de lancement

### ÉTAPE 0 — Prérequis
- Docker Desktop installé et démarré (baleine verte dans la barre des tâches)
- Python 3.10+ avec environnement virtuel activé

### ÉTAPE 1 — Préparer l'environnement Python (une seule fois)

```powershell
cd C:\Users\User\webscraping-pipeline-GameMetrics

# Créer et activer l'environnement virtuel
python -m venv venv
venv\Scripts\activate

# Installer les dépendances locales
pip install -r requirements.txt
```

### ÉTAPE 2 — Lancer l'infrastructure Docker

```powershell
# Depuis la racine du projet
docker-compose up -d --build
```

Attendre 30 secondes que PostgreSQL démarre, puis vérifier :

```powershell
docker-compose ps
```

Les 7 services doivent être `running` :
```
gamemetrics_db              ✅ running (healthy)
gamemetrics_redis           ✅ running (healthy)
gamemetrics_api             ✅ running
gamemetrics_celery_worker   ✅ running
gamemetrics_celery_beat     ✅ running
gamemetrics_prometheus      ✅ running
gamemetrics_grafana         ✅ running
```

### ÉTAPE 3 — Nettoyer les données

```powershell
# Depuis la racine du projet (pas depuis scraper/)
python scraper/clean_data.py
```

Résultat attendu : création de `data/clean_data.csv`

### ÉTAPE 4 — Importer les données dans PostgreSQL

```powershell
python import_to_db.py
```

Résultat attendu :
```
[OK] Connexion PostgreSQL établie (localhost:5432).
[INFO] 250 lignes — nettoyage en cours...
[OK] Import terminé — 250 jeux en base.
```

### ÉTAPE 5 — Accéder aux services

| Service | URL | Identifiants |
|---|---|---|
| **API REST** | http://localhost:5000/api/data | — |
| **Swagger** | http://localhost:5000/apidocs | — |
| **Santé** | http://localhost:5000/health | — |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | — |

---

## 🔄 Commandes quotidiennes

### Démarrer le projet après extinction du PC

```powershell
cd C:\Users\User\webscraping-pipeline-GameMetrics
venv\Scripts\activate
docker-compose up -d
# Attendre 30 secondes
# Ouvrir http://localhost:3000
```

### Arrêter proprement

```powershell
docker-compose down
```

### Voir les logs d'un service

```powershell
docker logs gamemetrics_api --tail 50
docker logs gamemetrics_grafana --tail 50
```

### Relancer un seul service

```powershell
docker-compose restart api
docker-compose restart grafana
```

### Vérifier les données en base

```powershell
docker exec gamemetrics_db psql -U gamemetrics -d gamemetrics -c "SELECT COUNT(*) FROM games;"
docker exec gamemetrics_db psql -U gamemetrics -d gamemetrics -c "SELECT title, platform, metascore FROM games ORDER BY metascore DESC LIMIT 5;"
```

### Lancer le scraping (local, hors Docker)

```powershell
venv\Scripts\activate
cd scraper
scrapy crawl metacritic
```

---

## 🧪 Tests API rapides

```powershell
# Stats globales
curl http://localhost:5000/api/stats

# Liste des jeux (page 1)
curl http://localhost:5000/api/data

# Filtrer par plateforme
curl "http://localhost:5000/api/data?platform=pc&min_metascore=85"

# Recherche par titre
curl "http://localhost:5000/api/data/search?query=wukong"

# Genres disponibles
curl http://localhost:5000/api/genres
```

---

## 📊 Dashboard Grafana

Le dashboard **🎮 GameMetrics — Observatoire des Jeux Vidéo** s'ouvre automatiquement.
Il contient 16 panels organisés en 6 sections :

1. **Vue Globale** — 6 KPI cards (total jeux, Metascore moyen, User Score moyen, plateformes, genres, jeux excellents)
2. **Genres & Plateformes** — Bar chart horizontal + Donut chart
3. **Analyse des Scores** — Comparaison Metascore vs User Score par genre + distribution des catégories
4. **Tendances Temporelles** — Courbe jeux par année et genre (Top 5)
5. **Top Jeux** — Tableau Top 50 avec couleurs conditionnelles
6. **Presse vs Utilisateurs** — Écart moyen par genre + pie chart catégories

3 filtres dynamiques : **Plateforme**, **Genre**, **Année**
