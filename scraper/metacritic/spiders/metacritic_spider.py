import scrapy
import time
from scrapy_playwright.page import PageMethod

BLOCKED_RESOURCES = {"image", "media", "font", "stylesheet"}


class MetacriticSpider(scrapy.Spider):
    """
    Observatoire de la popularité des jeux vidéo — ENSEA AS Data Science
    Jeux 2024-2026 — Maximum 2000 items
    Reprise automatique activée via JOBDIR dans settings.py
    """

    name = "metacritic"
    allowed_domains = ["metacritic.com"]

    MAX_ITEMS           = 2000
    TARGET_YEAR_MIN     = 2024
    TARGET_YEAR_MAX     = 2026
    MAX_PAGES_PER_GENRE = 10

    # Plateformes Metacritic (vérifiées sur le site)
    PLATFORMS = [
        "ps5", "xbox-series-x-s", "nintendo-switch-2", "switch", "pc",
        "mobile", "3ds", "dreamcast", "game-boy-advance", "gamecube",
        "meta-quest", "nintendo-64", "nintendo-ds", "ps-vita", "ps1",
        "ps2", "ps3", "ps4", "psp", "wii", "wii-u", "xbox", "xbox-360", "xbox-one",
    ]

    # Genres Metacritic (vérifiés sur le site)
    GENRES = [
        "action", "action-adventure", "action-puzzle", "action-rpg", "adventure",
        "application", "arcade", "beat-em-up", "board-card-game", "card-battle",
        "compilation", "edutainment", "exercise-fitness", "fighting",
        "first-person-shooter", "gambling", "general", "mmorpg", "open-world",
        "party-minigame", "pinball", "platformer", "puzzle", "racing",
        "real-time-strategy", "rhythm", "roguelike", "rpg", "sandbox", "shooter",
        "simulation", "sports", "strategy", "survival", "tactics",
        "third-person-shooter", "trivia-game-show", "turn-based-strategy",
        "virtual", "visual-novel",
    ]

    STEALTH_SCRIPT = """
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
        window.chrome = {runtime: {}};
    """

    start_urls = [
        "https://www.metacritic.com/browse/game/"
        "?releaseYearMin=2024&releaseYearMax=2026&sortBy=metaScore"
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items_scraped = 0

    # -------------------------------------------------------------------------
    # Helper : requête Playwright avec blocage ressources
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
    # ÉTAPE 1 : Génère toutes les combinaisons plateforme × genre
    # -------------------------------------------------------------------------
    def parse(self, response):
        total = len(self.PLATFORMS) * len(self.GENRES)
        self.logger.info(
            f"[START] {len(self.PLATFORMS)} plateformes × "
            f"{len(self.GENRES)} genres = {total} combinaisons"
        )
        for platform in self.PLATFORMS:
            for genre in self.GENRES:
                url = (
                    f"https://www.metacritic.com/browse/game/{platform}/{genre}/"
                    f"?releaseYearMin=2024&releaseYearMax=2026&sortBy=metaScore"
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
    # ÉTAPE 3 : Fiche d'un jeu → extraction
    # -------------------------------------------------------------------------
    def parse_game(self, response):

        def safe_get(selector, default="NA"):
            val = response.css(selector).get(default="").strip()
            return val if val else default

        title = safe_get("h1[data-testid='product-title'] span:last-child::text")
        if title == "NA":
            title = safe_get("h1::text")

        release_date = safe_get("div.c-gameDetails_ReleaseDate span:last-child::text")
        if release_date == "NA":
            for span in response.css("span::text").getall():
                s = span.strip()
                if len(s) > 4 and s[-4:].isdigit() and 2020 <= int(s[-4:]) <= 2030:
                    release_date = s
                    break

        dev_spans = response.css("li.hero-metadata__item span::text").getall()
        developer = dev_spans[1].strip() if len(dev_spans) >= 2 else (
            dev_spans[0].strip() if dev_spans else "NA"
        )

        platform = response.meta.get("platform", "NA")
        genre    = response.meta.get("genre", "NA")

        score_values = response.css("span[data-testid='global-score-value']::text").getall()
        metascore  = score_values[0].strip() if score_values else "NA"
        user_score = score_values[1].strip() if len(score_values) >= 2 else "NA"
        if user_score in ("tbd", "NA", ""):
            user_score = "NA"

        critics_count = user_reviews_count = "NA"
        for link in response.css("a[data-testid='global-score-review-count-link']"):
            href = link.attrib.get("href", "")
            text = " ".join(link.css("*::text").getall()).strip()
            if "critic-reviews" in href:
                critics_count = text
            elif "user-reviews" in href:
                user_reviews_count = text

        if release_date != "NA":
            try:
                year = int(release_date.strip()[-4:])
                if not (self.TARGET_YEAR_MIN <= year <= self.TARGET_YEAR_MAX):
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