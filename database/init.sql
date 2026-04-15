-- =============================================================================
-- init.sql — Schéma PostgreSQL pour l'observatoire des jeux vidéo
-- ENSEA AS Data Science
-- =============================================================================

-- Extension pour générer des UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- TABLE PRINCIPALE : games
-- =============================================================================
CREATE TABLE IF NOT EXISTS games (
    id                  SERIAL PRIMARY KEY,
    title               VARCHAR(255)    NOT NULL,
    release_date        DATE,
    release_year        SMALLINT,
    developer           VARCHAR(255),
    platform            VARCHAR(100)    NOT NULL,
    genre               VARCHAR(100)    NOT NULL,

    -- Scores presse
    metascore           NUMERIC(5, 1),
    score_category      VARCHAR(20),         -- Faible / Moyen / Bon / Excellent
    critics_count       INTEGER,

    -- Scores utilisateurs
    user_score          NUMERIC(4, 1),
    user_reviews_count  INTEGER,

    -- Analyse
    score_gap           NUMERIC(5, 1),       -- metascore - (user_score * 10)

    -- Métadonnées
    url                 VARCHAR(512)    UNIQUE NOT NULL,
    scraped_at          TIMESTAMP       DEFAULT NOW(),
    created_at          TIMESTAMP       DEFAULT NOW()
);

-- =============================================================================
-- INDEX pour accélérer les requêtes fréquentes
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_games_platform     ON games(platform);
CREATE INDEX IF NOT EXISTS idx_games_genre        ON games(genre);
CREATE INDEX IF NOT EXISTS idx_games_release_year ON games(release_year);
CREATE INDEX IF NOT EXISTS idx_games_metascore    ON games(metascore DESC);
CREATE INDEX IF NOT EXISTS idx_games_user_score   ON games(user_score DESC);
CREATE INDEX IF NOT EXISTS idx_games_platform_genre ON games(platform, genre);

-- =============================================================================
-- VUES pour le dashboard Power BI
-- =============================================================================

-- Vue 1 : Genres populaires (nombre de jeux + score moyen)
CREATE OR REPLACE VIEW v_genres_popularity AS
SELECT
    genre,
    COUNT(*)                            AS total_games,
    ROUND(AVG(metascore), 1)           AS avg_metascore,
    ROUND(AVG(user_score), 2)          AS avg_user_score,
    ROUND(AVG(score_gap), 1)           AS avg_score_gap
FROM games
WHERE metascore IS NOT NULL
GROUP BY genre
ORDER BY total_games DESC;

-- Vue 2 : Comparaison presse vs utilisateurs par genre
CREATE OR REPLACE VIEW v_press_vs_users AS
SELECT
    genre,
    platform,
    release_year,
    ROUND(AVG(metascore), 1)           AS avg_metascore,
    ROUND(AVG(user_score * 10), 1)     AS avg_user_score_100,
    ROUND(AVG(score_gap), 1)           AS avg_gap,
    COUNT(*)                            AS games_count
FROM games
WHERE metascore IS NOT NULL AND user_score IS NOT NULL
GROUP BY genre, platform, release_year
ORDER BY genre, platform;

-- Vue 3 : Top jeux par plateforme
CREATE OR REPLACE VIEW v_top_games AS
SELECT
    title,
    platform,
    genre,
    release_date,
    release_year,
    developer,
    metascore,
    user_score,
    critics_count,
    user_reviews_count,
    score_gap,
    score_category
FROM games
WHERE metascore IS NOT NULL
ORDER BY metascore DESC;

-- =============================================================================
-- DONNÉES DE TEST (optionnel — à supprimer en production)
-- =============================================================================
-- INSERT INTO games (title, release_date, release_year, developer, platform, genre,
--     metascore, score_category, critics_count, user_score, user_reviews_count,
--     score_gap, url, scraped_at)
-- VALUES ('Test Game', '2024-01-01', 2024, 'Test Dev', 'pc', 'action',
--     85.0, 'Bon', 20, 7.5, 150, 10.0,
--     'https://www.metacritic.com/game/test-game/', NOW());

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE 'Schéma GameMetrics initialisé avec succès.';
    RAISE NOTICE 'Tables créées : games';
    RAISE NOTICE 'Vues créées   : v_genres_popularity, v_press_vs_users, v_top_games';
END $$;
