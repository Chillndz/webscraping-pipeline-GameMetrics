"""
routes.py — Endpoints REST de l'API GameMetrics
"""

from flask import Blueprint, jsonify, request
from api.models import Game
from api.app import db
from tasks.celery_worker import scrape_task
from sqlalchemy import func

api_bp = Blueprint("api", __name__)


# =============================================================================
# GET /api/data — Liste paginée des jeux avec filtres
# =============================================================================
@api_bp.route("/data", methods=["GET"])
def get_games():
    """
    Récupère les jeux avec pagination et filtres optionnels.
    ---
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: limit
        in: query
        type: integer
        default: 20
      - name: platform
        in: query
        type: string
      - name: genre
        in: query
        type: string
      - name: min_metascore
        in: query
        type: number
      - name: year
        in: query
        type: integer
    responses:
      200:
        description: Liste des jeux
    """
    page        = request.args.get("page", 1, type=int)
    limit       = min(request.args.get("limit", 20, type=int), 100)
    platform    = request.args.get("platform")
    genre       = request.args.get("genre")
    min_meta    = request.args.get("min_metascore", type=float)
    year        = request.args.get("year", type=int)
    search      = request.args.get("query", "")

    query = Game.query

    if platform:
        query = query.filter(Game.platform == platform)
    if genre:
        query = query.filter(Game.genre == genre)
    if min_meta:
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
        "total":    total,
        "page":     page,
        "limit":    limit,
        "pages":    games.pages,
        "data":     [g.to_dict() for g in games.items],
    })


# =============================================================================
# GET /api/data/<id> — Détail d'un jeu
# =============================================================================
@api_bp.route("/data/<int:game_id>", methods=["GET"])
def get_game(game_id):
    """
    Récupère un jeu par son ID.
    ---
    parameters:
      - name: game_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Détail du jeu
      404:
        description: Jeu non trouvé
    """
    game = Game.query.get_or_404(game_id)
    return jsonify(game.to_dict())


# =============================================================================
# GET /api/data/search — Recherche par titre
# =============================================================================
@api_bp.route("/data/search", methods=["GET"])
def search_games():
    """
    Recherche de jeux par titre.
    ---
    parameters:
      - name: query
        in: query
        type: string
        required: true
    responses:
      200:
        description: Résultats de recherche
    """
    query_str = request.args.get("query", "")
    if not query_str:
        return jsonify({"error": "Paramètre 'query' requis"}), 400

    games = Game.query.filter(
        Game.title.ilike(f"%{query_str}%")
    ).limit(50).all()

    return jsonify({
        "query":   query_str,
        "count":   len(games),
        "results": [g.to_dict() for g in games],
    })


# =============================================================================
# GET /api/stats — Statistiques globales
# =============================================================================
@api_bp.route("/stats", methods=["GET"])
def get_stats():
    """
    Statistiques globales de l'observatoire.
    ---
    responses:
      200:
        description: Statistiques
    """
    total        = Game.query.count()
    avg_meta     = db.session.query(func.avg(Game.metascore)).scalar()
    avg_user     = db.session.query(func.avg(Game.user_score)).scalar()
    platforms    = db.session.query(Game.platform, func.count()).group_by(Game.platform).all()
    genres       = db.session.query(Game.genre, func.count()).group_by(Game.genre).all()
    years        = db.session.query(Game.release_year, func.count()).group_by(Game.release_year).all()
    categories   = db.session.query(Game.score_category, func.count()).group_by(Game.score_category).all()

    return jsonify({
        "total_games":      total,
        "avg_metascore":    round(float(avg_meta), 1) if avg_meta else None,
        "avg_user_score":   round(float(avg_user), 2) if avg_user else None,
        "by_platform":      {p: c for p, c in platforms},
        "by_genre":         {g: c for g, c in genres},
        "by_year":          {str(y): c for y, c in years if y},
        "by_category":      {cat: c for cat, c in categories if cat},
    })


# =============================================================================
# POST /api/scrape — Lance le scraping (synchrone)
# =============================================================================
@api_bp.route("/scrape", methods=["POST"])
def scrape():
    """
    Lance le scraping Metacritic (synchrone).
    ---
    responses:
      200:
        description: Scraping lancé
    """
    result = scrape_task()
    return jsonify({"status": "done", "message": result})


# =============================================================================
# POST /api/scrape/async — Lance le scraping (asynchrone via Celery)
# =============================================================================
@api_bp.route("/scrape/async", methods=["POST"])
def scrape_async():
    """
    Lance le scraping en tâche asynchrone Celery.
    ---
    responses:
      202:
        description: Tâche soumise
    """
    task = scrape_task.delay()
    return jsonify({
        "status":  "submitted",
        "task_id": task.id,
        "message": "Scraping lancé en arrière-plan.",
    }), 202


# =============================================================================
# GET /api/scrape/status/<task_id> — Statut d'une tâche Celery
# =============================================================================
@api_bp.route("/scrape/status/<task_id>", methods=["GET"])
def scrape_status(task_id):
    """
    Vérifie le statut d'une tâche de scraping.
    ---
    parameters:
      - name: task_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Statut de la tâche
    """
    task = scrape_task.AsyncResult(task_id)
    return jsonify({
        "task_id": task_id,
        "status":  task.status,
        "result":  str(task.result) if task.ready() else None,
    })


# =============================================================================
# Gestion des erreurs
# =============================================================================
@api_bp.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Ressource non trouvée"}), 404


@api_bp.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Erreur serveur interne"}), 500