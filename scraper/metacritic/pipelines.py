import json
import os
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem

RAW_DATA_PATH = "../data/raw_data.json"


class DuplicateFilterPipeline:
    """Dédoublonnage par URL — charge les URLs existantes au démarrage."""

    def __init__(self):
        self.seen_urls = set()

    def open_spider(self, spider):
        if os.path.exists(RAW_DATA_PATH):
            try:
                with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                self.seen_urls = {item["url"] for item in existing if "url" in item}
                spider.logger.info(
                    f"[REPRISE] {len(self.seen_urls)} URLs déjà scrapées — ignorées."
                )
            except Exception as e:
                spider.logger.warning(f"[REPRISE] Lecture raw_data.json impossible : {e}")

    def process_item(self, item, spider):
        url = ItemAdapter(item).get("url")
        if url in self.seen_urls:
            raise DropItem(f"[DUPLICATE] {url}")
        self.seen_urls.add(url)
        return item


class YearFilterPipeline:
    """Double sécurité : garde uniquement les jeux de 2024 à 2026."""

    TARGET_YEAR_MIN = 2024
    TARGET_YEAR_MAX = 2026

    def process_item(self, item, spider):
        release_date = ItemAdapter(item).get("release_date", "NA")
        if release_date and release_date != "NA":
            try:
                year = int(release_date.strip()[-4:])
                if not (self.TARGET_YEAR_MIN <= year <= self.TARGET_YEAR_MAX):
                    raise DropItem(
                        f"[ANNÉE] {ItemAdapter(item).get('title')} ({year}) "
                        f"hors {self.TARGET_YEAR_MIN}-{self.TARGET_YEAR_MAX}"
                    )
            except (ValueError, IndexError):
                pass
        return item


class ItemLimitPipeline:
    """Arrête après MAX_ITEMS — compte les items déjà collectés au démarrage."""

    MAX_ITEMS = 2000

    def __init__(self):
        self.count = 0

    def open_spider(self, spider):
        if os.path.exists(RAW_DATA_PATH):
            try:
                with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                self.count = len(existing)
                spider.logger.info(
                    f"[REPRISE] {self.count} items existants — "
                    f"quota restant : {self.MAX_ITEMS - self.count}"
                )
            except Exception:
                pass

    def process_item(self, item, spider):
        if self.count >= self.MAX_ITEMS:
            raise DropItem(f"[LIMITE] Quota de {self.MAX_ITEMS} atteint.")
        self.count += 1
        return item


class ValidationPipeline:
    """Rejette les items sans titre."""

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        title = adapter.get("title")
        if not title or title == "NA":
            raise DropItem(f"[VALIDATION] Sans titre : {adapter.get('url')}")
        if adapter.get("metascore") is None:
            spider.logger.warning(
                f"[WARNING] Metascore manquant pour {title} — conservé quand même"
            )
        return item


class JsonWriterPipeline:
    """
    Écrit dans raw_data.json en mode APPEND.
    Au démarrage : charge les données existantes.
    À la fermeture : fusionne ancien + nouveau et réécrit.
    """

    FIELDS_ORDER = [
        "title", "release_date", "developer", "platform", "genre",
        "metascore", "critics_count", "user_score", "user_reviews_count",
        "url", "scraped_at",
    ]

    def open_spider(self, spider):
        self.existing_items = []
        if os.path.exists(RAW_DATA_PATH):
            try:
                with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
                    self.existing_items = json.load(f)
                spider.logger.info(
                    f"[REPRISE] {len(self.existing_items)} items existants chargés."
                )
            except Exception:
                self.existing_items = []
        self.new_items = []

    def close_spider(self, spider):
        all_items = self.existing_items + self.new_items
        os.makedirs(os.path.dirname(RAW_DATA_PATH), exist_ok=True)
        with open(RAW_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)
        spider.logger.info(
            f"[PIPELINE] {len(self.new_items)} nouveaux jeux ajoutés — "
            f"Total : {len(all_items)} dans raw_data.json"
        )

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        ordered = {field: adapter.get(field) for field in self.FIELDS_ORDER}
        self.new_items.append(ordered)
        return item