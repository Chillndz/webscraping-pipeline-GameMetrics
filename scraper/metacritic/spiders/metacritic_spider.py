import scrapy
import time


class MetacriticSpider(scrapy.Spider):
    """
    Observatoire de la popularité des jeux vidéo — ENSEA AS Data Science

    Collecte les données de jeux vidéo depuis Metacritic :
    - Toutes les plateformes (PC, PS5, Xbox, Switch, etc.)
    - Tous les genres disponibles
    - Jeux sortis en 2024 uniquement
    - Maximum 300 jeux au total (limite éthique du projet)

    Respecte robots.txt et applique un délai entre les requêtes.
    User-Agent : ENSEA Educational Project
    """

    name = "metacritic"
    allowed_domains = ["metacritic.com"]

    # Plateformes ciblées pour l'observatoire multi-plateforme
    PLATFORMS = ["pc", "ps5", "xbox-series-x", "switch", "ps4", "xbox-one"]

    # ── Limites de scraping ───────────────────────────────────────────────────
    MAX_ITEMS = 300         
    TARGET_YEAR = 2024       
    MAX_PAGES_PER_GENRE = 2 

    start_urls = [
        "https://www.metacritic.com/browse/game/"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items_scraped = 0  

    custom_settings = {
        "DOWNLOAD_DELAY": 2,               
        "RANDOMIZE_DOWNLOAD_DELAY": True,  
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": "ENSEA Educational Project - Web Scraping Course",
        "CONCURRENT_REQUESTS": 1,          
        "LOG_LEVEL": "INFO",
        "FEEDS": {
            "raw_data.json": {
                "format": "json",
                "encoding": "utf8",
                "indent": 2,
                "overwrite": True,
            }
        },
    }

    # -------------------------------------------------------------------------
    # ÉTAPE 1 : Page d'accueil → récupérer tous les genres
    # -------------------------------------------------------------------------
    def parse(self, response):
        """
        Point d'entrée : extrait la liste des genres disponibles
        et génère une requête par genre x plateforme.
        """
        # Les genres sont listés dans la sidebar de navigation
        genres = response.css("ul.genres-list li a::attr(href)").getall()

        if not genres:
            # Fallback : liste de genres connus si la navigation change
            genres = [
                "action", "adventure", "rpg", "shooter", "strategy",
                "sports", "racing", "simulation", "puzzle", "fighting",
                "platformer", "horror"
            ]
            genre_slugs = genres
        else:
            # Extraire le slug depuis l'URL (ex: /browse/game/action/ → action)
            genre_slugs = [g.strip("/").split("/")[-1] for g in genres]

        self.logger.info(f"[GENRES] {len(genre_slugs)} genres trouvés : {genre_slugs}")

        for platform in self.PLATFORMS:
            for genre in genre_slugs:
                # Filtre côté URL : jeux de 2024 uniquement, triés par Metascore
                url = f"https://www.metacritic.com/browse/game/{platform}/{genre}/?releaseYearMin=2024&releaseYearMax=2024&sortBy=metaScore"
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_genre_page,
                    meta={"platform": platform, "genre": genre, "page": 1},
                    headers={"User-Agent": "ENSEA Educational Project - Web Scraping Course"}
                )

    # -------------------------------------------------------------------------
    # ÉTAPE 2 : Page de liste d'un genre → récupérer les liens de jeux
    # -------------------------------------------------------------------------
    def parse_genre_page(self, response):
        """
        Extrait les liens vers les fiches de jeux sur une page de liste.
        Gère la pagination automatiquement.
        """
        platform = response.meta["platform"]
        genre = response.meta["genre"]
        page = response.meta["page"]

        # Liens vers les fiches individuelles des jeux
        game_links = response.css("a.title::attr(href)").getall()

        # Fallback sélecteur alternatif
        if not game_links:
            game_links = response.css(
                "div.c-finderProductCard a::attr(href)"
            ).getall()

        self.logger.info(
            f"[PAGE] Plateforme={platform} | Genre={genre} | Page={page} | {len(game_links)} jeux"
        )

        for link in game_links:
            # ── Limite globale : arrêt dès que MAX_ITEMS est atteint ──────────
            if self.items_scraped >= self.MAX_ITEMS:
                self.logger.info(f"[LIMITE] {self.MAX_ITEMS} jeux atteints — arrêt du scraping.")
                return

            full_url = response.urljoin(link)
            yield scrapy.Request(
                url=full_url,
                callback=self.parse_game,
                meta={"platform": platform, "genre": genre},
                headers={"User-Agent": "ENSEA Educational Project - Web Scraping Course"}
            )

        # --- Pagination : max MAX_PAGES_PER_GENRE pages par genre/plateforme ---
        next_page = response.css("a.c-navigationPagination_item--next::attr(href)").get()
        if next_page and page < self.MAX_PAGES_PER_GENRE and self.items_scraped < self.MAX_ITEMS:
            yield scrapy.Request(
                url=response.urljoin(next_page),
                callback=self.parse_genre_page,
                meta={"platform": platform, "genre": genre, "page": page + 1},
                headers={"User-Agent": "ENSEA Educational Project - Web Scraping Course"}
            )

    # -------------------------------------------------------------------------
    # ÉTAPE 3 : Fiche d'un jeu → extraire toutes les données
    # -------------------------------------------------------------------------
    def parse_game(self, response):
        """
        Extrait toutes les données d'une fiche jeu Metacritic.
        Retourne un dictionnaire structuré prêt pour la BDD.
        """

        def safe_get(css_selector, default="NA"):
            """Extrait le texte d'un sélecteur CSS, retourne default si absent."""
            val = response.css(css_selector).get(default="").strip()
            return val if val else default

        def safe_get_all(css_selector):
            """Extrait une liste de textes depuis un sélecteur CSS."""
            vals = response.css(css_selector).getall()
            cleaned = [v.strip() for v in vals if v.strip()]
            return ", ".join(cleaned) if cleaned else "NA"

        # ----- Informations générales -----
        title = safe_get("h1.c-productHero_title span::text")
        if title == "NA":
            title = safe_get("h1::text")

        release_date = safe_get(
            "div.c-gameDetails_ReleaseDate span.g-outer-spacing-left-medium-fluid::text"
        )

        developer = safe_get(
            "div.c-gameDetails_Developer li.c-gameDetails_listItem span::text"
        )

        publisher = safe_get_all(
            "div.c-gameDetails_Distributor span.g-outer-spacing-left-medium-fluid::text"
        )

        # La plateforme vient de la meta (contexte de navigation)
        platform = response.meta.get("platform", "NA")

        # Rating PEGI / ESRB
        maturity_rating = safe_get(
            "div.c-gameDetails_RatingDescriptors span::text"
        )

        # Genre principal (depuis la meta de navigation)
        genre = response.meta.get("genre", "NA")

        # Tags de genre affichés sur la page du jeu
        genre_tags = safe_get_all(
            "div.c-gameDetails_Genre li.c-gameDetails_listItem span::text"
        )

        # ----- Scores -----
        # Metascore (presse)
        metascore = safe_get(
            "div.c-productScoreInfo_scoreNumber span::text"
        )
        if metascore == "NA":
            metascore = safe_get("div.metascore_w span::text")

        # Nombre de critiques presse
        critics_count = safe_get(
            "div.c-productScoreInfo_reviewsTotal span::text"
        )

        # Score utilisateurs
        user_score = safe_get(
            "div.c-productUserScoreInfo_scoreNumber span::text"
        )

        # Nombre d'avis utilisateurs
        user_reviews_count = safe_get(
            "div.c-productUserScoreInfo_reviewsTotal span::text"
        )

        # ----- Filtre année côté spider (double sécurité) -----
        # Si la date contient une année différente de TARGET_YEAR, on ignore
        if release_date != "NA":
            try:
                year = int(release_date.strip()[-4:])
                if year != self.TARGET_YEAR:
                    self.logger.debug(
                        f"[FILTRE ANNÉE] {title} ({year}) ignoré — hors 2024"
                    )
                    return
            except (ValueError, IndexError):
                pass  # Date mal formatée → on garde quand même l'item

        # ----- Construction de l'item -----
        item = {
            # Métadonnées
            "url": response.url,
            "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),

            # Infos générales
            "title": title,
            "release_date": release_date,
            "developer": developer,
            "publisher": publisher,
            "platform": platform,
            "maturity_rating": maturity_rating,

            # Genres
            "genre": genre,
            "genre_tags": genre_tags,

            # Scores
            "metascore": self._parse_score(metascore),
            "critics_count": self._parse_count(critics_count),
            "user_score": self._parse_score(user_score),
            "user_reviews_count": self._parse_count(user_reviews_count),
        }

        self.logger.debug(f"[GAME] {title} | {platform} | Metascore={metascore} | UserScore={user_score}")
        self.items_scraped += 1
        yield item

    # -------------------------------------------------------------------------
    # UTILITAIRES
    # -------------------------------------------------------------------------
    def _parse_score(self, value):
        """Convertit un score en float, retourne None si non disponible."""
        if value == "NA" or not value:
            return None
        try:
            return float(value.replace(",", "."))
        except (ValueError, AttributeError):
            return None

    def _parse_count(self, value):
        """Convertit un compteur en int, retourne None si non disponible."""
        if value == "NA" or not value:
            return None
        try:
            # Retire les textes comme "Based on X Ratings" → garde le nombre
            digits = "".join(filter(str.isdigit, value))
            return int(digits) if digits else None
        except (ValueError, AttributeError):
            return None