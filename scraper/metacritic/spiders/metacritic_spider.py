import scrapy
import time
import re
from scrapy_playwright.page import PageMethod


BLOCKED_RESOURCES = {"image", "media", "font", "stylesheet"}


class MetacriticSpider(scrapy.Spider):
    """
    Observatoire de la popularité des jeux vidéo — ENSEA AS Data Science
    Jeux 2024 uniquement — Maximum 2000 items
    Plateformes et genres lus dynamiquement depuis les filtres Metacritic
    """

    name = "metacritic"
    allowed_domains = ["metacritic.com"]

    MAX_ITEMS = 2000
    TARGET_YEAR = 2024
    MAX_PAGES_PER_GENRE = 3

    STEALTH_SCRIPT = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        window.chrome = {runtime: {}};
    """

    # Page de départ : browse général avec filtres visibles
    start_urls = ["https://www.metacritic.com/browse/game/?releaseYearMin=2024&releaseYearMax=2024&sortBy=metaScore"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items_scraped = 0

    # -------------------------------------------------------------------------
    # Helper : requête Playwright
    # -------------------------------------------------------------------------
    def playwright_request(self, url, callback, meta=None):
        _meta = {
            "playwright": True,
            "playwright_include_page": False,
            "playwright_context": "default",
            "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
            "playwright_page_methods": [
                PageMethod("add_init_script", self.STEALTH_SCRIPT),
                PageMethod("route", "**/*", self._block_resources),
                PageMethod("wait_for_load_state", "domcontentloaded"),
            ],
        }
        if meta:
            _meta.update(meta)
        return scrapy.Request(
            url=url,
            callback=callback,
            meta=_meta,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            errback=self.errback_handler,
        )

    async def _block_resources(self, route, request):
        if request.resource_type in BLOCKED_RESOURCES:
            await route.abort()
        else:
            await route.continue_()

    def errback_handler(self, failure):
        self.logger.error(f"[ERREUR] {failure.request.url} — {repr(failure.value)[:150]}")

    # -------------------------------------------------------------------------
    # ÉTAPE 1 : Page de browse → lire plateformes ET genres dynamiquement
    # -------------------------------------------------------------------------
    def parse(self, response):
        """
        Lit les plateformes et genres directement depuis les filtres
        latéraux de Metacritic (labels dans div[data-slot='wrapper']).
        Structure HTML vérifiée :
          <h4>Platforms</h4>
          <div data-slot="wrapper"><label for="Mobile">Mobile</label>
          <div data-slot="wrapper"><label for="PC">PC</label>
          ...
          <h4>Genres</h4>
          <div data-slot="wrapper"><label for="Action">Action</label>
          ...
        """
        # Trouver toutes les sections de filtre (Platforms, Genres, etc.)
        sections = response.css("div.border-t.border-gray-400")

        platforms = []
        genres = []
        current_section = None

        for section in sections:
            # Identifier la section par le titre <h4>
            header = section.css("h4::text").get(default="").strip()

            if "Platform" in header:
                current_section = "platforms"
                labels = section.css("div[data-slot='wrapper'] label::text").getall()
                platforms = [l.strip() for l in labels if l.strip()]

            elif "Genre" in header:
                current_section = "genres"
                labels = section.css("div[data-slot='wrapper'] label::text").getall()
                genres = [l.strip() for l in labels if l.strip()]

        # Fallbacks si la lecture dynamique échoue
        if not platforms:
            platforms = ["pc", "ps5", "ps4", "xbox-series-x", "xbox-one",
                        "switch", "mobile", "ios", "android"]
            self.logger.warning("[PARSE] Plateformes non trouvées — utilisation du fallback")
        if not genres:
            genres = ["action", "adventure", "rpg", "shooter", "strategy",
                     "sports", "racing", "simulation", "puzzle", "fighting",
                     "platformer", "horror"]
            self.logger.warning("[PARSE] Genres non trouvés — utilisation du fallback")

        # Convertir les labels en slugs URL (ex: "Xbox Series X" → "xbox-series-x")
        platform_slugs = [self._to_slug(p) for p in platforms]
        genre_slugs    = [self._to_slug(g) for g in genres]

        self.logger.info(f"[PLATEFORMES] {len(platform_slugs)} : {platform_slugs}")
        self.logger.info(f"[GENRES] {len(genre_slugs)} : {genre_slugs}")

        for platform in platform_slugs:
            for genre in genre_slugs:
                url = (
                    f"https://www.metacritic.com/browse/game/{platform}/{genre}/"
                    f"?releaseYearMin=2024&releaseYearMax=2024&sortBy=metaScore"
                )
                yield self.playwright_request(
                    url=url,
                    callback=self.parse_genre_page,
                    meta={"platform": platform, "genre": genre, "page": 1},
                )

    # -------------------------------------------------------------------------
    # ÉTAPE 2 : Page de liste → liens de jeux
    # -------------------------------------------------------------------------
    def parse_genre_page(self, response):
        platform = response.meta["platform"]
        genre    = response.meta["genre"]
        page     = response.meta["page"]

        game_links = list(dict.fromkeys(
            l for l in response.css(
                "div[data-testid='filter-results'] a::attr(href)"
            ).getall()
            if l.startswith("/game/")
        ))

        self.logger.info(
            f"[PAGE] {platform} | {genre} | page {page} | {len(game_links)} jeux"
        )

        for link in game_links:
            if self.items_scraped >= self.MAX_ITEMS:
                self.logger.info(f"[LIMITE] {self.MAX_ITEMS} atteints — arrêt.")
                return
            yield self.playwright_request(
                url=response.urljoin(link),
                callback=self.parse_game,
                meta={"platform": platform, "genre": genre},
            )

        next_page = response.css("a[aria-label='Next page']::attr(href)").get()
        if next_page and page < self.MAX_PAGES_PER_GENRE and self.items_scraped < self.MAX_ITEMS:
            yield self.playwright_request(
                url=response.urljoin(next_page),
                callback=self.parse_genre_page,
                meta={"platform": platform, "genre": genre, "page": page + 1},
            )

    # -------------------------------------------------------------------------
    # ÉTAPE 3 : Fiche d'un jeu → extraction avec sélecteurs vérifiés
    # -------------------------------------------------------------------------
    def parse_game(self, response):

        def safe_get(selector, default="NA"):
            val = response.css(selector).get(default="").strip()
            return val if val else default

        # Titre
        title = safe_get("h1[data-testid='product-title'] span:last-child::text")
        if title == "NA":
            title = safe_get("h1::text")

        # Date de sortie
        release_date = safe_get(
            "div.c-gameDetails_ReleaseDate span:last-child::text"
        )
        if release_date == "NA":
            for span in response.css("span::text").getall():
                s = span.strip()
                if len(s) > 4 and s[-4:].isdigit() and 2020 <= int(s[-4:]) <= 2027:
                    release_date = s
                    break

        # Développeur — vérifié image 1 : 2ème li.hero-metadata__item
        dev_spans = response.css("li.hero-metadata__item span::text").getall()
        developer = dev_spans[1].strip() if len(dev_spans) >= 2 else (
            dev_spans[0].strip() if dev_spans else "NA"
        )

        platform = response.meta.get("platform", "NA")
        genre    = response.meta.get("genre", "NA")

        # Scores — vérifié : 1er = metascore, 2ème = user score
        score_values = response.css(
            "span[data-testid='global-score-value']::text"
        ).getall()
        metascore  = score_values[0].strip() if len(score_values) >= 1 else "NA"
        user_score = score_values[1].strip() if len(score_values) >= 2 else "NA"
        if user_score in ("tbd", "NA", ""):
            user_score = "NA"

        # Nombre de critiques / avis — vérifié images 3 & 4
        critics_count      = "NA"
        user_reviews_count = "NA"
        for link in response.css("a[data-testid='global-score-review-count-link']"):
            href = link.attrib.get("href", "")
            text = " ".join(link.css("*::text").getall()).strip()
            if "critic-reviews" in href:
                critics_count = text
            elif "user-reviews" in href:
                user_reviews_count = text

        # Filtre année
        if release_date != "NA":
            try:
                year = int(release_date.strip()[-4:])
                if year != self.TARGET_YEAR:
                    self.logger.debug(f"[FILTRE ANNÉE] {title} ({year}) ignoré")
                    return
            except (ValueError, IndexError):
                pass

        item = {
            "url":                response.url,
            "scraped_at":         time.strftime("%Y-%m-%dT%H:%M:%S"),
            "title":              title,
            "release_date":       release_date,
            "developer":          developer,
            "platform":           platform,
            "genre":              genre,
            "metascore":          self._parse_score(metascore),
            "critics_count":      self._parse_count(critics_count),
            "user_score":         self._parse_score(user_score),
            "user_reviews_count": self._parse_count(user_reviews_count),
        }

        self.logger.info(
            f"[GAME ✓] {title} | {platform} | {genre} | "
            f"Metascore={metascore} | User={user_score} | Dev={developer}"
        )
        self.items_scraped += 1
        yield item

    # -------------------------------------------------------------------------
    # UTILITAIRES
    # -------------------------------------------------------------------------
    def _to_slug(self, label):
        """Convertit un label Metacritic en slug URL.
        Ex: 'Xbox Series X' → 'xbox-series-x'
            'PlayStation 5' → 'playstation-5'
            'Action'        → 'action'
        """
        slug = label.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)   # Retire les caractères spéciaux
        slug = re.sub(r'\s+', '-', slug)             # Espaces → tirets
        slug = re.sub(r'-+', '-', slug)              # Tirets multiples → 1 seul
        return slug.strip('-')

    def _parse_score(self, value):
        if not value or value == "NA":
            return None
        try:
            return float(value.replace(",", "."))
        except (ValueError, AttributeError):
            return None

    def _parse_count(self, value):
        if not value or value == "NA":
            return None
        try:
            digits = "".join(filter(str.isdigit, value))
            return int(digits) if digits else None
        except (ValueError, AttributeError):
            return None