"""
clean_data.py — Nettoyage et structuration des données Metacritic
ENSEA AS Data Science — Observatoire des jeux vidéo

Entrée  : data/raw_data.json
Sortie  : data/clean_data.csv

Étapes :
  1. Chargement du JSON brut
  2. Suppression des doublons
  3. Standardisation des dates
  4. Nettoyage des valeurs manquantes
  5. Validation des types et plages
  6. Export CSV
"""

import json
import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────────────────
RAW_PATH   = "../data/raw_data.json"
CLEAN_PATH = "../data/clean_data.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [clean_data] %(levelname)s: %(message)s"
)
log = logging.getLogger(__name__)


def load_raw(path: str) -> pd.DataFrame:
    """Charge le fichier JSON brut."""
    log.info(f"Chargement de {path}...")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    log.info(f"  → {len(df)} lignes chargées, {len(df.columns)} colonnes")
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les doublons basés sur l'URL."""
    before = len(df)
    df = df.drop_duplicates(subset=["url"], keep="first")
    after = len(df)
    log.info(f"Doublons supprimés : {before - after} (reste {after})")
    return df


def standardize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit les dates texte en format standard YYYY-MM-DD.
    Ex: 'Oct 23, 2024' → '2024-10-23'
        'Jan 2024'     → '2024-01-01'
    """
    def parse_date(val):
        if not val or val == "NA":
            return None
        val = str(val).strip()
        # Formats connus sur Metacritic
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%b %Y", "%B %Y", "%Y-%m-%d", "%Y"):
            try:
                return datetime.strptime(val, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    df["release_date"] = df["release_date"].apply(parse_date)
    missing = df["release_date"].isna().sum()
    log.info(f"Dates standardisées — {missing} dates non parsées → None")
    return df


def clean_text_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie les champs texte : strip, NA → None, capitalisation."""
    text_cols = ["title", "developer", "platform", "genre"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: None if (x is None or str(x).strip() in ("NA", "", "nan"))
                else str(x).strip()
            )
    missing = {col: df[col].isna().sum() for col in text_cols if col in df.columns}
    log.info(f"Champs texte nettoyés — valeurs manquantes : {missing}")
    return df


def validate_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Valide et nettoie les scores :
    - metascore    : float entre 0 et 100
    - user_score   : float entre 0 et 10
    - critics_count / user_reviews_count : int >= 0
    """
    # Metascore
    df["metascore"] = pd.to_numeric(df["metascore"], errors="coerce")
    invalid_meta = ((df["metascore"] < 0) | (df["metascore"] > 100)).sum()
    df.loc[(df["metascore"] < 0) | (df["metascore"] > 100), "metascore"] = None
    log.info(f"Metascores invalides → None : {invalid_meta}")

    # User score
    df["user_score"] = pd.to_numeric(df["user_score"], errors="coerce")
    invalid_user = ((df["user_score"] < 0) | (df["user_score"] > 10)).sum()
    df.loc[(df["user_score"] < 0) | (df["user_score"] > 10), "user_score"] = None
    log.info(f"User scores invalides → None : {invalid_user}")

    # Compteurs
    for col in ["critics_count", "user_reviews_count"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].apply(lambda x: None if (pd.isna(x) or x < 0) else int(x))

    return df


def add_computed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute des colonnes calculées utiles pour l'analyse :
    - release_year  : année extraite de release_date
    - score_gap     : différence metascore - (user_score * 10)
    - score_category : catégorie du metascore (Faible / Moyen / Bon / Excellent)
    """
    # Année de sortie
    df["release_year"] = pd.to_datetime(
        df["release_date"], errors="coerce"
    ).dt.year.astype("Int64")

    # Écart presse vs utilisateurs (ramené sur 100)
    df["score_gap"] = df.apply(
        lambda row: round(row["metascore"] - (row["user_score"] * 10), 1)
        if pd.notna(row["metascore"]) and pd.notna(row["user_score"])
        else None,
        axis=1,
    )

    # Catégorie du Metascore
    def categorize(score):
        if pd.isna(score):
            return None
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Bon"
        elif score >= 50:
            return "Moyen"
        else:
            return "Faible"

    df["score_category"] = df["metascore"].apply(categorize)

    log.info("Colonnes calculées ajoutées : release_year, score_gap, score_category")
    return df


def export_csv(df: pd.DataFrame, path: str) -> None:
    """Exporte le DataFrame nettoyé en CSV."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    log.info(f"Export CSV : {path} ({len(df)} lignes)")


def print_summary(df: pd.DataFrame) -> None:
    """Affiche un résumé des données nettoyées."""
    print("\n" + "="*60)
    print("RÉSUMÉ DES DONNÉES NETTOYÉES")
    print("="*60)
    print(f"Total jeux         : {len(df)}")
    print(f"Plateformes        : {df['platform'].nunique()} uniques")
    print(f"Genres             : {df['genre'].nunique()} uniques")
    print(f"Années couvertes   : {df['release_year'].min()} - {df['release_year'].max()}")
    print(f"\nMetascore moyen    : {df['metascore'].mean():.1f}")
    print(f"User score moyen   : {df['user_score'].mean():.2f}")
    print(f"\nValeurs manquantes :")
    missing = df.isnull().sum()
    for col, count in missing[missing > 0].items():
        pct = count / len(df) * 100
        print(f"  {col:<25} : {count:>4} ({pct:.1f}%)")
    print("\nTop 5 plateformes :")
    print(df["platform"].value_counts().head(5).to_string())
    print("\nTop 5 genres :")
    print(df["genre"].value_counts().head(5).to_string())
    print("="*60 + "\n")


def main():
    log.info("=== Démarrage du nettoyage des données ===")

    # 1. Chargement
    df = load_raw(RAW_PATH)

    # 2. Doublons
    df = remove_duplicates(df)

    # 3. Dates
    df = standardize_dates(df)

    # 4. Champs texte
    df = clean_text_fields(df)

    # 5. Scores
    df = validate_scores(df)

    # 6. Colonnes calculées
    df = add_computed_columns(df)

    # 7. Ordre des colonnes final
    cols_order = [
        "title", "release_date", "release_year", "developer", "platform", "genre",
        "metascore", "score_category", "critics_count",
        "user_score", "user_reviews_count", "score_gap",
        "url", "scraped_at",
    ]
    df = df[[c for c in cols_order if c in df.columns]]

    # 8. Résumé
    print_summary(df)

    # 9. Export
    export_csv(df, CLEAN_PATH)

    log.info("=== Nettoyage terminé ===")


if __name__ == "__main__":
    main()