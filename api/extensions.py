"""
extensions.py — Instances partagées Flask
"""

from flask_sqlalchemy import SQLAlchemy
from prometheus_flask_exporter import PrometheusMetrics

db = SQLAlchemy()
metrics = PrometheusMetrics.for_app_factory()