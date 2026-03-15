CREATE TABLE games (
    id SERIAL PRIMARY KEY,
    title TEXT,
    genre TEXT,
    critic_score FLOAT,
    user_score FLOAT,
    price FLOAT,
    platform TEXT,
    release_date DATE
);