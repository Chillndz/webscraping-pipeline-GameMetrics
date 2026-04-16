"""
celery_worker.py — Tâches asynchrones et planifiées
Celery + Redis + Celery Beat
"""

import os
import subprocess
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# ── Initialisation Celery ─────────────────────────────────────────────────────
celery = Celery(
    "gamemetrics",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Important : inclure le module des tâches
    include=["tasks.celery_worker"],
)

# ── Celery Beat : planification automatique ───────────────────────────────────
celery.conf.beat_schedule = {
    # Scraping automatique tous les dimanches à 2h du matin
    "weekly-scraping": {
        "task": "tasks.celery_worker.scrape_task",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
        "options": {"queue": "scraping"},
    },
    # Nettoyage des données tous les dimanches à 3h
    "weekly-cleaning": {
        "task": "tasks.celery_worker.clean_task",
        "schedule": crontab(hour=3, minute=0, day_of_week="sunday"),
        "options": {"queue": "cleaning"},
    },
}


# =============================================================================
# TÂCHE 1 : Scraping Metacritic
# =============================================================================
@celery.task(
    name="tasks.celery_worker.scrape_task",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def scrape_task(self):
    """
    Lance le spider Scrapy via subprocess.
    Utilise JOBDIR pour la reprise automatique.
    """
    try:
        self.update_state(state="STARTED", meta={"step": "Lancement du spider"})

        result = subprocess.run(
            ["scrapy", "crawl", "metacritic"],
            cwd="/app/scraper",
            capture_output=True,
            text=True,
            timeout=7200,  # 2h max
        )

        if result.returncode != 0:
            raise Exception(f"Spider échoué : {result.stderr[-500:]}")

        return f"Scraping terminé. Stdout: {result.stdout[-200:]}"

    except subprocess.TimeoutExpired:
        raise self.retry(exc=Exception("Timeout du scraping"), countdown=300)
    except Exception as exc:
        raise self.retry(exc=exc)


# =============================================================================
# TÂCHE 2 : Nettoyage des données
# =============================================================================
@celery.task(
    name="tasks.celery_worker.clean_task",
    bind=True,
    max_retries=2,
)
def clean_task(self):
    """Lance clean_data.py pour nettoyer raw_data.json → clean_data.csv"""
    try:
        self.update_state(state="STARTED", meta={"step": "Nettoyage des données"})

        result = subprocess.run(
            ["python", "clean_data.py"],
            cwd="/app/scraper",
            capture_output=True,
            text=True,
            timeout=600,
        )

        if result.returncode != 0:
            raise Exception(f"Nettoyage échoué : {result.stderr[-500:]}")

        return "Nettoyage terminé."

    except Exception as exc:
        raise self.retry(exc=exc)


# =============================================================================
# TÂCHE 3 : Import CSV → PostgreSQL
# =============================================================================
@celery.task(name="tasks.celery_worker.import_task", bind=True)
def import_task(self):
    """Importe clean_data.csv dans PostgreSQL."""
    import pandas as pd
    from sqlalchemy import create_engine

    try:
        self.update_state(state="STARTED", meta={"step": "Import en base"})

        engine = create_engine(
            os.getenv("DATABASE_URL", "postgresql://gamemetrics:gamemetrics_secret@db:5432/gamemetrics")
        )

        df = pd.read_csv("/app/data/clean_data.csv")

        df.to_sql(
            "games",
            engine,
            if_exists="append",
            index=False,
            method="multi",
        )

        return f"{len(df)} jeux importés en base."

    except Exception as exc:
        raise self.retry(exc=exc)
