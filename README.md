# 🎮 GameMetrics — Observatoire de la Popularité des Jeux Vidéo

![Badge Niveau Or](https://img.shields.io/badge/Niveau-Or%20🥇-gold)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Scrapy](https://img.shields.io/badge/Scrapy-2.11-green)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

> Projet de fin de module Web Scraping — ENSEA AS Data Science  
> Enseignant : Dr N'golo Konate

---

## 👥 Membres et Rôles

| Membre | Rôle |
|--------|------|
| [Ndzana Boup Achille Emmanuel] | Data Engineer (Scraping + Nettoyage) |
| [Lago Choeurtis] | Backend / DevOps (API + Docker + Celery + Monitoring) |

---

## 📋 Description du Projet

GameMetrics est un **pipeline complet de production** qui collecte, nettoie, stocke et expose des données sur la popularité des jeux vidéo entre **2024 et 2026** depuis Metacritic.

### Thème
> *Observatoire de la popularité des jeux vidéo basé sur notes critiques et avis utilisateurs*

### Visualisations Power BI
- Tendances : genres populaires 2024-2026
- Comparaison notes critiques vs notes utilisateurs
- Tableau interactif avec filtres par genre, plateforme, score

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE GAMEMETRICS                     │
│                                                             │
│  Metacritic ──► Scrapy+Playwright ──► raw_data.json         │
│                                           │                 │
│                                    clean_data.py            │
│                                           │                 │
│                                    clean_data.csv           │
│                                           │                 │
│                                    PostgreSQL               │
│                                           │                 │
│                                     Flask API               │
│                                    /api/data                │
│                                    /api/stats               │
│                                    /api/scrape              │
│                                           │                 │
│                              Celery + Redis (async)         │
│                              Celery Beat (planifié)         │
│                                           │                 │
│                           Prometheus + Grafana              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technologies Utilisées

| Composant | Technologie |
|-----------|-------------|
| Scraping | Scrapy 2.11 + Playwright (JS rendering) |
| Nettoyage | pandas 2.2 |
| Base de données | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 |
| API REST | Flask 3.0 + Flasgger (Swagger) |
| Tâches async | Celery 5.3 + Redis 7 |
| Planification | Celery Beat |
| Monitoring | Prometheus + Grafana |
| Conteneurisation | Docker + Docker Compose |
| Tests | pytest |
| Dashboard | Power BI Desktop |

---

## 📁 Structure du Projet

```
GameMetrics/
├── scraper/
│   ├── scrapy.cfg
│   ├── clean_data.py          ← Nettoyage pandas
│   └── metacritic/
│       ├── settings.py        ← Config Scrapy + reprise auto
│       ├── pipelines.py       ← Filtres + écriture JSON
│       ├── items.py
│       └── spiders/
│           └── metacritic_spider.py
├── api/
│   ├── app.py                 ← Flask application factory
│   ├── models.py              ← Modèles SQLAlchemy
│   └── routes.py              ← Endpoints REST
├── database/
│   └── init.sql               ← Schéma PostgreSQL + vues
├── tasks/
│   └── celery_worker.py       ← Tâches async + Beat schedule
├── monitoring/
│   └── prometheus.yml
├── docker/
│   └── Dockerfile
├── tests/
│   └── test_clean_data.py     ← Tests pytest
├── data/                      ← raw_data.json + clean_data.csv
├── docker-compose.yml
├── requirements.txt
├── .env                       ← Variables d'environnement
└── .gitignore
```

---

## 🚀 Instructions d'Installation

### Prérequis
- Python 3.11+
- Docker Desktop
- Git

### 1. Cloner le repository
```bash
git clone https://github.com/[votre-groupe]/webscraping-pipeline-GameMetrics.git
cd webscraping-pipeline-GameMetrics
```

### 2. Créer l'environnement virtuel
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configurer les variables d'environnement
```bash
cp .env.example .env
# Éditer .env avec vos valeurs
```

---

## 🕷️ Lancement du Scraping

```bash
cd scraper
scrapy crawl metacritic
```

**Reprise après pause** : relancer la même commande — Scrapy reprend automatiquement grâce au `JOBDIR`.

**Repartir de zéro** :
```bash
rm -rf scraper/.scrapy_jobs/metacritic/
rm data/raw_data.json
```

---

## 🧹 Nettoyage des Données

```bash
python scraper/clean_data.py
```

Produit `data/clean_data.csv` avec :
- Dates standardisées (YYYY-MM-DD)
- Scores validés (metascore 0-100, user_score 0-10)
- Colonnes calculées : `release_year`, `score_gap`, `score_category`

---

## 🐳 Lancement Docker

```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f api

# Arrêter
docker-compose down
```

### Services disponibles

| Service | URL |
|---------|-----|
| API REST | http://localhost:5000/api/data |
| Documentation Swagger | http://localhost:5000/apidocs |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| PostgreSQL | localhost:5432 |

---

## 📡 Endpoints API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/data` | Liste paginée avec filtres |
| GET | `/api/data/<id>` | Détail d'un jeu |
| GET | `/api/data/search?query=...` | Recherche par titre |
| GET | `/api/stats` | Statistiques globales |
| POST | `/api/scrape` | Lance le scraping (sync) |
| POST | `/api/scrape/async` | Lance le scraping (async) |
| GET | `/api/scrape/status/<id>` | Statut d'une tâche |

### Exemple de requête
```bash
# Jeux PS5 avec metascore > 80, page 1
curl "http://localhost:5000/api/data?platform=ps5&min_metascore=80&page=1&limit=10"
```

---

## 🧪 Tests

```bash
pytest tests/ -v
```

Couverture des tests :
- `remove_duplicates` — suppression des doublons
- `standardize_dates` — standardisation des dates
- `validate_scores` — validation des plages de scores
- `clean_text_fields` — nettoyage des champs texte
- `add_computed_columns` — colonnes calculées

---

## 📊 Dashboard Power BI

Connexion : PostgreSQL → `localhost:5432` → base `gamemetrics`

Visualisations :
1. **Barres** : genres populaires (nombre de jeux + score moyen)
2. **Scatter plot** : Metascore vs User Score par genre
3. **Tableau filtrable** : tous les jeux avec slicers genre/plateforme/score

---

## ⚖️ Charte Éthique

- ✅ `robots.txt` respecté
- ✅ Délai de 3s entre chaque requête
- ✅ User-Agent identifiable : Chrome 123 (navigateur standard)
- ✅ Volume limité à 2000 items
- ✅ Aucune donnée personnelle collectée
- ✅ Site validé auprès de l'enseignant

---

## 📬 Contact

**Enseignant :** Dr N'golo Konate — konatengolo@ufhb.edu.ci