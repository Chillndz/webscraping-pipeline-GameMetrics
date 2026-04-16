"""
import_to_db.py — Import rapide de clean_data.csv → PostgreSQL
À lancer depuis la RACINE du projet : python import_to_db.py

CORRECTION : lit DATABASE_URL si disponible (Docker), sinon construit
             la connexion depuis les variables individuelles avec host=localhost.
"""

import json, os, sys
from datetime import datetime
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

# ── Connexion : DATABASE_URL prioritaire (Docker), sinon localhost (local) ─────
DATABASE_URL = os.getenv("DATABASE_URL", "")

if DATABASE_URL and "@db:" in DATABASE_URL:
    # On est dans Docker — mais import_to_db se lance depuis l'hôte,
    # donc on remplace le service Docker "db" par "localhost"
    DATABASE_URL = DATABASE_URL.replace("@db:", "@localhost:")

if DATABASE_URL:
    # Extraire les paramètres depuis l'URL
    import urllib.parse as up
    r = up.urlparse(DATABASE_URL)
    DB_CONFIG = {
        "host":             r.hostname or "localhost",
        "port":             r.port or 5432,
        "dbname":           r.path.lstrip("/"),
        "user":             r.username,
        "password":         r.password,
        "connect_timeout":  10,
    }
else:
    DB_CONFIG = {
        "host":             "localhost",
        "port":             5432,
        "dbname":           os.getenv("POSTGRES_DB",       "gamemetrics"),
        "user":             os.getenv("POSTGRES_USER",     "gamemetrics"),
        "password":         os.getenv("POSTGRES_PASSWORD", "gamemetrics_secret"),
        "connect_timeout":  10,
    }

# ── Chemins absolus ────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_PATH    = os.path.join(PROJECT_DIR, "data", "raw_data.json")
CLEAN_PATH  = os.path.join(PROJECT_DIR, "data", "clean_data.csv")


def load_data() -> pd.DataFrame:
    if os.path.exists(CLEAN_PATH):
        print(f"[INFO] Chargement {CLEAN_PATH}...")
        return pd.read_csv(CLEAN_PATH)
    print(f"[INFO] Chargement {RAW_PATH}...")
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data)


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    print(f"[INFO] {len(df)} lignes — nettoyage en cours...")
    df = df.replace("NA", pd.NA)

    df["release_date"] = pd.to_datetime(
        df["release_date"], errors="coerce", format="mixed"
    ).dt.strftime("%Y-%m-%d")

    df["release_year"] = pd.to_datetime(
        df["release_date"], errors="coerce"
    ).dt.year.astype("Int64")

    df["metascore"]          = pd.to_numeric(df.get("metascore"),          errors="coerce")
    df["user_score"]         = pd.to_numeric(df.get("user_score"),         errors="coerce")
    df["critics_count"]      = pd.to_numeric(df.get("critics_count"),      errors="coerce")
    df["user_reviews_count"] = pd.to_numeric(df.get("user_reviews_count"), errors="coerce")

    df["score_gap"] = (df["metascore"] - df["user_score"] * 10).round(1)

    df["score_category"] = pd.cut(
        df["metascore"],
        bins=[-1, 49.9, 74.9, 89.9, 100],
        labels=["Faible", "Moyen", "Bon", "Excellent"],
    ).astype(str).replace("nan", None)

    before = len(df)
    df = df.drop_duplicates(subset=["url"], keep="first")
    print(f"[INFO] {before - len(df)} doublons supprimés — reste {len(df)}")
    return df


def insert(df: pd.DataFrame):
    conn = psycopg2.connect(**DB_CONFIG)
    cur  = conn.cursor()

    COLS = [
        "title", "release_date", "release_year", "developer",
        "platform", "genre", "metascore", "score_category",
        "critics_count", "user_score", "user_reviews_count",
        "score_gap", "url", "scraped_at",
    ]

    def clean_val(v):
        try:
            if pd.isna(v):
                return None
        except Exception:
            pass
        return v if str(v) not in ("nan", "None", "NA") else None

    def parse_scraped_at(v):
        try:
            return datetime.strptime(str(v)[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None

    rows = [
        (
            clean_val(row.get("title")),
            clean_val(row.get("release_date")),
            clean_val(row.get("release_year")),
            clean_val(row.get("developer")),
            clean_val(row.get("platform")),
            clean_val(row.get("genre")),
            clean_val(row.get("metascore")),
            clean_val(row.get("score_category")),
            clean_val(row.get("critics_count")),
            clean_val(row.get("user_score")),
            clean_val(row.get("user_reviews_count")),
            clean_val(row.get("score_gap")),
            clean_val(row.get("url")),
            parse_scraped_at(row.get("scraped_at")),
        )
        for row in df.to_dict("records")
    ]

    print(f"[INFO] Insertion de {len(rows)} lignes...")

    execute_values(
        cur,
        f"""
        INSERT INTO games ({', '.join(COLS)})
        VALUES %s
        ON CONFLICT (url) DO NOTHING;
        """,
        rows,
        page_size=500,
    )

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM games;")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    print(f"[OK] Import terminé — {total} jeux en base.")


def main():
    print("=" * 50)
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        print(f"[OK] Connexion PostgreSQL établie ({DB_CONFIG['host']}:{DB_CONFIG['port']}).")
    except Exception as e:
        print(f"[ERREUR] Connexion échouée : {e}")
        print("→ Vérifiez que Docker tourne : docker-compose ps")
        print(f"→ Config utilisée : {DB_CONFIG['host']}:{DB_CONFIG['port']} / {DB_CONFIG['dbname']}")
        sys.exit(1)

    df = load_data()
    df = prepare(df)
    insert(df)
    print("=" * 50)


if __name__ == "__main__":
    main()
