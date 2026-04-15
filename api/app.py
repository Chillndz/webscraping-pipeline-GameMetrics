"""
app.py — Point d'entrée de l'API Flask
Observatoire des jeux vidéo — ENSEA AS Data Science
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger
from prometheus_flask_exporter import PrometheusMetrics
from dotenv import load_dotenv
import os

load_dotenv()

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    # ── Configuration base de données ─────────────────────────────────────────
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://gamemetrics:gamemetrics@db:5432/gamemetrics"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_SORT_KEYS"] = False

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)

    # Swagger / OpenAPI (bonus niveau Or)
    Swagger(app, template={
        "info": {
            "title": "GameMetrics API",
            "description": "Observatoire de la popularité des jeux vidéo 2024-2026",
            "version": "1.0.0",
        }
    })

    # Prometheus metrics — expose /metrics pour Grafana
    PrometheusMetrics(app)

    # ── Routes ────────────────────────────────────────────────────────────────
    from api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")


