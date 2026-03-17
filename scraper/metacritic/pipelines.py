import json
import logging
from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


class DuplicateFilterPipeline:
    """
    Filtre les jeux déjà scrapés en se basant sur l'URL.
    Évite les doublons quand un jeu apparaît dans plusieurs genres.
    """

    def __init__(self):
        self.seen_urls = set()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        url = adapter.get("url")

        if url in self.seen_urls:
            spider.logger.debug(f"[DUPLICATE] Ignoré : {url}")
            raise DropItem(f"Doublon ignoré : {url}")

        self.seen_urls.add(url)
        return item


class YearFilterPipeline:
    """
    Double sécurité : vérifie que le jeu est bien sorti en 2024.
    Complète le filtre déjà présent dans le spider.
    """

    TARGET_YEAR = 2024

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        release_date = adapter.get("release_date", "NA")

        if release_date and release_date != "NA":
            try:
                year = int(release_date.strip()[-4:])
                if year != self.TARGET_YEAR:
                    raise DropItem(
                        f"[ANNÉE] {adapter.get('title')} ({year}) ignoré — hors {self.TARGET_YEAR}"
                    )
            except (ValueError, IndexError):
                pass  # Date mal formatée → on conserve l'item

        return item


class ItemLimitPipeline:
    """
    Arrête la collecte après MAX_ITEMS items valides.
    Dernière ligne de défense contre un dépassement de quota.
    """

    MAX_ITEMS = 300

    def __init__(self):
        self.count = 0

    def process_item(self, item, spider):
        if self.count >= self.MAX_ITEMS:
            raise DropItem(
                f"[LIMITE] Quota de {self.MAX_ITEMS} jeux atteint — item ignoré."
            )
        self.count += 1
        return item


class ValidationPipeline:
    """
    Vérifie que les champs essentiels sont présents.
    Rejette les items sans titre.
    """

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        title = adapter.get("title")
        if not title or title == "NA":
            raise DropItem(
                f"[VALIDATION] Item sans titre rejeté : {adapter.get('url')}"
            )

        return item


class JsonWriterPipeline:
    """
    Écrit les items validés dans raw_data.json de façon incrémentale.
    Permet de ne pas perdre les données en cas d'interruption.
    """

    def open_spider(self, spider):
        self.file = open("raw_data.json", "w", encoding="utf-8")
        self.file.write("[\n")
        self.first_item = True
        self.count = 0

    def close_spider(self, spider):
        self.file.write("\n]")
        self.file.close()
        spider.logger.info(f"[PIPELINE] {self.count} jeux écrits dans raw_data.json")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        line = json.dumps(dict(adapter), ensure_ascii=False, indent=2)

        if not self.first_item:
            self.file.write(",\n")
        self.first_item = False

        self.file.write(line)
        self.count += 1
        return item