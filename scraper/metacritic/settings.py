BOT_NAME = "metacritic"
SPIDER_MODULES = ["metacritic.spiders"]
NEWSPIDER_MODULE = "metacritic.spiders"

# ── Éthique ───────────────────────────────────────────────────────────────────
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# ── Reprise automatique ───────────────────────────────────────────────────────
# Scrapy sauvegarde l'état ici à chaque Ctrl+C
# Relancer avec la même commande reprend automatiquement
# Pour repartir de ZÉRO : supprimer .scrapy_jobs/metacritic/ et data/raw_data.json
JOBDIR = ".scrapy_jobs/metacritic"

# ── Playwright ────────────────────────────────────────────────────────────────
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"

PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 60000,
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--window-size=1920,1080",
    ],
}
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        ),
        "java_script_enabled": True,
    }
}

# ── Middlewares ───────────────────────────────────────────────────────────────
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 429]

# ── Pipelines ─────────────────────────────────────────────────────────────────
ITEM_PIPELINES = {
    "metacritic.pipelines.DuplicateFilterPipeline": 100,
    "metacritic.pipelines.YearFilterPipeline":      150,
    "metacritic.pipelines.ItemLimitPipeline":       200,
    "metacritic.pipelines.ValidationPipeline":      250,
    "metacritic.pipelines.JsonWriterPipeline":      300,
}

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

# ── Misc ──────────────────────────────────────────────────────────────────────
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"