"""
models.py — Modèles SQLAlchemy
"""

from api.app import db


class Game(db.Model):
    __tablename__ = "games"

    id                  = db.Column(db.Integer, primary_key=True)
    title               = db.Column(db.String(255), nullable=False)
    release_date        = db.Column(db.Date)
    release_year        = db.Column(db.SmallInteger)
    developer           = db.Column(db.String(255))
    platform            = db.Column(db.String(100), nullable=False)
    genre               = db.Column(db.String(100), nullable=False)
    metascore           = db.Column(db.Numeric(5, 1))
    score_category      = db.Column(db.String(20))
    critics_count       = db.Column(db.Integer)
    user_score          = db.Column(db.Numeric(4, 1))
    user_reviews_count  = db.Column(db.Integer)
    score_gap           = db.Column(db.Numeric(5, 1))
    url                 = db.Column(db.String(512), unique=True, nullable=False)
    scraped_at          = db.Column(db.DateTime)
    created_at          = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id":                 self.id,
            "title":              self.title,
            "release_date":       str(self.release_date) if self.release_date else None,
            "release_year":       self.release_year,
            "developer":          self.developer,
            "platform":           self.platform,
            "genre":              self.genre,
            "metascore":          float(self.metascore) if self.metascore else None,
            "score_category":     self.score_category,
            "critics_count":      self.critics_count,
            "user_score":         float(self.user_score) if self.user_score else None,
            "user_reviews_count": self.user_reviews_count,
            "score_gap":          float(self.score_gap) if self.score_gap else None,
            "url":                self.url,
            "scraped_at":         str(self.scraped_at) if self.scraped_at else None,
        }
