"""
clean_data.py — Nettoyage et structuration des données Metacritic
ENSEA AS Data Science — Observatoire des jeux vidéo

Entrée  : data/raw_data.json  (chemin relatif à la RACINE du projet)
Sortie  : data/clean_data.csv

CORRECTION : chemins absolus résolus depuis la position du script,
             fonctionne qu'on lance depuis scraper/ ou depuis la racine.
"""

import json
import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime

# ── Chemins absolus — fonctionnent depuis n'importe quel répertoire ───────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))     # .../scraper/
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)                   # .../project/
DATA_DIR    = os.path.join(PROJECT_DIR, "data")

RAW_PATH   = os.path.join(DATA_DIR, "raw_data.json")
CLEAN_PATH = os.path.join(DATA_DIR, "clean_data.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [clean_data] %(levelname)s: %(message)s"
)
log = logging.getLogger(__name__)


def load_raw(path: str) -> pd.DataFrame:
    """Charge le fichier JSON brut."""
    log.info(f"Chargement de {path}...")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier introuvable : {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    log.info(f"  → {len(df)} lignes chargées, {len(df.columns)} colonnes")
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les doublons basés sur l'URL."""
    before = len(df)
    df = df.drop_duplicates(subset=["url"], keep="first")
    log.info(f"Doublons supprimés : {before - len(df)} (reste {len(df)})")
    return df


def standardize_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit les dates texte en format standard YYYY-MM-DD."""
    def parse_date(val):
        if not val or str(val).strip() in ("NA", "nan", "None", ""):
            return None
        val = str(val).strip()
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
    """Nettoie les champs texte."""
    text_cols = ["title", "developer", "platform", "genre"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: None if (x is None or str(x).strip() in ("NA", "", "nan", "None"))
                else str(x).strip()
            )
    return df


def validate_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Valide et nettoie les scores."""
    df["metascore"] = pd.to_numeric(df["metascore"], errors="coerce")
    df.loc[(df["metascore"] < 0) | (df["metascore"] > 100), "metascore"] = None

    df["user_score"] = pd.to_numeric(df["user_score"], errors="coerce")
    df.loc[(df["user_score"] < 0) | (df["user_score"] > 10), "user_score"] = None

    for col in ["critics_count", "user_reviews_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].apply(lambda x: None if (pd.isna(x) or x < 0) else int(x))

    return df


def add_computed_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les colonnes calculées."""
    df["release_year"] = pd.to_datetime(
        df["release_date"], errors="coerce"
    ).dt.year.astype("Int64")

    df["score_gap"] = df.apply(
        lambda row: round(row["metascore"] - (row["user_score"] * 10), 1)
        if pd.notna(row.get("metascore")) and pd.notna(row.get("user_score"))
        else None,
        axis=1,
    )

    def categorize(score):
        if pd.isna(score):
            return None
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Bon"
        elif score >= 50:
            return "Moyen"
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
    if df["release_year"].notna().any():
        print(f"Années couvertes   : {int(df['release_year'].min())} - {int(df['release_year'].max())}")
    if df["metascore"].notna().any():
        print(f"Metascore moyen    : {df['metascore'].mean():.1f}")
    if df["user_score"].notna().any():
        print(f"User score moyen   : {df['user_score'].mean():.2f}")
    missing = df.isnull().sum()
    print(f"\nValeurs manquantes :")
    for col, count in missing[missing > 0].items():
        print(f"  {col:<25} : {count:>4} ({count/len(df)*100:.1f}%)")
    print("="*60 + "\n")


def main():
    log.info("=== Démarrage du nettoyage des données ===")
    df = load_raw(RAW_PATH)
    df = remove_duplicates(df)
    df = standardize_dates(df)
    df = clean_text_fields(df)
    df = validate_scores(df)
    df = add_computed_columns(df)

    cols_order = [
        "title", "release_date", "release_year", "developer", "platform", "genre",
        "metascore", "score_category", "critics_count",
        "user_score", "user_reviews_count", "score_gap",
        "url", "scraped_at",
    ]
    df = df[[c for c in cols_order if c in df.columns]]

    print_summary(df)
    export_csv(df, CLEAN_PATH)
    log.info("=== Nettoyage terminé ===")


if __name__ == "__main__":
    main()
