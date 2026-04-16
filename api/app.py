"""
app.py — Point d'entrée de l'API Flask
"""

from flask import Flask
from flasgger import Swagger
from dotenv import load_dotenv
from api.extensions import db, metrics
import os

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://gamemetrics:gamemetrics_secret@db:5432/gamemetrics"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_SORT_KEYS"] = False
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

    db.init_app(app)
    metrics.init_app(app)

    Swagger(app, template={
        "info": {
            "title": "GameMetrics API",
            "description": "Observatoire de la popularité des jeux vidéo — ENSEA",
            "version": "1.0.0",
        }
    })

    from api.routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    @app.route("/health")
    def health():
        return {"status": "ok", "service": "GameMetrics API"}, 200

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true"
    )