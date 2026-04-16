"""
routes.py — Endpoints REST de l'API GameMetrics
"""

from flask import Blueprint, jsonify, request
from api.models import Game
from api.extensions import db
from sqlalchemy import func

api_bp = Blueprint("api", __name__)


@api_bp.route("/data", methods=["GET"])
def get_games():
    page     = request.args.get("page", 1, type=int)
    limit    = min(request.args.get("limit", 20, type=int), 100)
    platform = request.args.get("platform")
    genre    = request.args.get("genre")
    min_meta = request.args.get("min_metascore", type=float)
    year     = request.args.get("year", type=int)
    search   = request.args.get("query", "")

    query = Game.query
    if platform:
        query = query.filter(Game.platform == platform)
    if genre:
        query = query.filter(Game.genre == genre)
    if min_meta is not None:
        query = query.filter(Game.metascore >= min_meta)
    if year:
        query = query.filter(Game.release_year == year)
    if search:
        query = query.filter(Game.title.ilike(f"%{search}%"))

    total = query.count()
    games = query.order_by(Game.metascore.desc()).paginate(
        page=page, per_page=limit, error_out=False
    )

    return jsonify({
        "total": total,
        "page":  page,
        "limit": limit,
        "pages": games.pages,
        "data":  [g.to_dict() for g in games.items],
    })


@api_bp.route("/data/<int:game_id>", methods=["GET"])
def get_game(game_id):
    game = db.session.get(Game, game_id)
    if not game:
        return jsonify({"error": "Jeu non trouvé"}), 404
    return jsonify(game.to_dict())


@api_bp.route("/data/search", methods=["GET"])
def search_games():
    query_str = request.args.get("query", "")
    if not query_str:
        return jsonify({"error": "Paramètre 'query' requis"}), 400
    games = Game.query.filter(Game.title.ilike(f"%{query_str}%")).limit(50).all()
    return jsonify({"query": query_str, "count": len(games), "results": [g.to_dict() for g in games]})


@api_bp.route("/stats", methods=["GET"])
def get_stats():
    total      = Game.query.count()
    avg_meta   = db.session.query(func.avg(Game.metascore)).scalar()
    avg_user   = db.session.query(func.avg(Game.user_score)).scalar()
    platforms  = db.session.query(Game.platform, func.count()).group_by(Game.platform).all()
    genres     = db.session.query(Game.genre, func.count()).group_by(Game.genre).all()
    years      = db.session.query(Game.release_year, func.count()).group_by(Game.release_year).all()
    categories = db.session.query(Game.score_category, func.count()).group_by(Game.score_category).all()

    return jsonify({
        "total_games":    total,
        "avg_metascore":  round(float(avg_meta), 1) if avg_meta else None,
        "avg_user_score": round(float(avg_user), 2) if avg_user else None,
        "by_platform":    {p: c for p, c in platforms if p},
        "by_genre":       {g: c for g, c in genres if g},
        "by_year":        {str(y): c for y, c in years if y},
        "by_category":    {cat: c for cat, c in categories if cat},
    })


@api_bp.route("/genres", methods=["GET"])
def get_genres():
    genres = db.session.query(Game.genre, func.count(Game.id).label("count"))\
        .filter(Game.genre.isnot(None))\
        .group_by(Game.genre)\
        .order_by(func.count(Game.id).desc())\
        .all()
    return jsonify([{"genre": g, "count": c} for g, c in genres])


@api_bp.route("/platforms", methods=["GET"])
def get_platforms():
    platforms = db.session.query(Game.platform, func.count(Game.id).label("count"))\
        .filter(Game.platform.isnot(None))\
        .group_by(Game.platform)\
        .order_by(func.count(Game.id).desc())\
        .all()
    return jsonify([{"platform": p, "count": c} for p, c in platforms])


@api_bp.route("/scrape/async", methods=["POST"])
def scrape_async():
    try:
        from tasks.celery_worker import scrape_task
        task = scrape_task.delay()
        return jsonify({"status": "submitted", "task_id": task.id}), 202
    except Exception as e:
        return jsonify({"error": f"Celery non disponible : {str(e)}"}), 503


@api_bp.route("/scrape/status/<task_id>", methods=["GET"])
def scrape_status(task_id):
    try:
        from tasks.celery_worker import scrape_task
        task = scrape_task.AsyncResult(task_id)
        return jsonify({"task_id": task_id, "status": task.status, "result": str(task.result) if task.ready() else None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Ressource non trouvée"}), 404

@api_bp.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Erreur serveur interne", "detail": str(e)}), 500