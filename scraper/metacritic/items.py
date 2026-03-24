import scrapy


class GameItem(scrapy.Item):
    """
    Champs retenus pour l'observatoire des jeux vidéo 2024.
    Nettoyé : suppression de publisher, maturity_rating, genre_tags
    car absents ou non pertinents sur Metacritic.
    """
    # Métadonnées scraping
    url          = scrapy.Field()
    scraped_at   = scrapy.Field()

    # Informations générales
    title        = scrapy.Field()
    release_date = scrapy.Field()
    developer    = scrapy.Field()
    platform     = scrapy.Field()

    # Genre
    genre        = scrapy.Field()

    # Scores
    metascore         = scrapy.Field()   # Note presse (0-100)
    critics_count     = scrapy.Field()   # Nombre de critiques presse
    user_score        = scrapy.Field()   # Note utilisateurs (0-10)
    user_reviews_count = scrapy.Field()  # Nombre d'avis utilisateurs