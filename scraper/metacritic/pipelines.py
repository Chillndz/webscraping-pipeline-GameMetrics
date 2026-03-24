import json
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class DuplicateFilterPipeline:
    """Filtre les doublons par URL."""

    def __init__(self):
        self.seen_urls = set()

    def process_item(self, item, spider):
        url = ItemAdapter(item).get("url")
        if url in self.seen_urls:
            raise DropItem(f"[DUPLICATE] {url}")
        self.seen_urls.add(url)
        return item


class YearFilterPipeline:
    """Double sécurité : garde uniquement les jeux de 2024."""

    TARGET_YEAR = 2024

    def process_item(self, item, spider):
        release_date = ItemAdapter(item).get("release_date", "NA")
        if release_date and release_date != "NA":
            try:
                year = int(release_date.strip()[-4:])
                if year != self.TARGET_YEAR:
                    raise DropItem(f"[ANNÉE] {ItemAdapter(item).get('title')} ({year})")
            except (ValueError, IndexError):
                pass
        return item


class ItemLimitPipeline:
    """Arrête la collecte après 300 items valides."""

    MAX_ITEMS = 300

    def __init__(self):
        self.count = 0

    def process_item(self, item, spider):
        if self.count >= self.MAX_ITEMS:
            raise DropItem(f"[LIMITE] Quota de {self.MAX_ITEMS} atteint.")
        self.count += 1
        return item


class ValidationPipeline:
    """Rejette les items sans titre ET sans metascore (données trop vides)."""

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        title    = adapter.get("title")
        meta     = adapter.get("metascore")

        if not title or title == "NA":
            raise DropItem(f"[VALIDATION] Sans titre : {adapter.get('url')}")

        if meta is None:
            spider.logger.warning(
                f"[WARNING] Metascore manquant pour {title} — item conservé quand même"
            )
        return item


class JsonWriterPipeline:
    """Écrit les items dans raw_data.json de façon incrémentale."""

    # Champs dans l'ordre voulu pour le JSON final
    FIELDS_ORDER = [
        "title", "release_date", "developer", "platform", "genre",
        "metascore", "critics_count", "user_score", "user_reviews_count",
        "url", "scraped_at",
    ]

    def open_spider(self, spider):
        self.file = open("../data/raw_data.json", "w", encoding="utf-8")
        self.file.write("[\n")
        self.first_item = True
        self.count = 0

    def close_spider(self, spider):
        self.file.write("\n]")
        self.file.close()
        spider.logger.info(f"[PIPELINE] {self.count} jeux écrits dans raw_data.json")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        # Réordonne les champs pour la lisibilité
        ordered = {field: adapter.get(field) for field in self.FIELDS_ORDER}
        line = json.dumps(ordered, ensure_ascii=False, indent=2)

        if not self.first_item:
            self.file.write(",\n")
        self.first_item = False
        self.file.write(line)
        self.count += 1
        return item