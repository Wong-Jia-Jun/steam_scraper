DELETE_TABLES_QUERY = "DROP TABLE IF EXISTS urls, url_info, steam_game_info, steam_game_reviews;"

# We dont want duplicate URLs
CREATE_TABLES_URLS_QUERY = "CREATE TABLE IF NOT EXISTS urls (\
    id SERIAL PRIMARY KEY,\
    url TEXT UNIQUE NOT NULL,\
    seen BOOLEAN NOT NULL DEFAULT FALSE\
);"

CREATE_TABLES_URL_INFO_QUERY = "CREATE TABLE IF NOT EXISTS url_info (\
    id SERIAL PRIMARY KEY,\
    url_id INTEGER REFERENCES urls(id),\
    response_time DOUBLE PRECISION,\
    ip_address INET,\
    server_region TEXT,\
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\
);"

CREATE_TABLE_STEAM_GAME_INFO_QUERY = """
CREATE TABLE IF NOT EXISTS steam_game_info (
    id SERIAL PRIMARY KEY,
    url_id INTEGER REFERENCES urls(id),
    name TEXT,
    developer TEXT,
    genres TEXT[],
    overall_review_rating TEXT,
    overall_review_count NUMERIC,
    average_price_SGD NUMERIC,
    release_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_TABLE_STEAM_GAME_REVIEWS_QUERY = """
CREATE TABLE IF NOT EXISTS steam_game_reviews (
    id SERIAL PRIMARY KEY,
    url_id INTEGER REFERENCES urls(id),
    review_text TEXT,
    review_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

ADD_URL_QUERY = """
INSERT INTO urls (url)
VALUES (%s)
ON CONFLICT (url) DO NOTHING;
"""

ADD_URL_INFO_QUERY = """
INSERT INTO url_info (url_id, response_time, ip_address, server_region)
VALUES (%s, %s, %s, %s);
"""

ADD_STEAM_GAME_INFO_QUERY = """
INSERT INTO steam_game_info (url_id, name, average_price_SGD, genres, overall_review_rating, overall_review_count, developer, release_date)
VALUES (%s, %s, %s, %s, %s, %s, %s, TO_DATE(%s, 'DD Mon, YYYY'));
"""

ADD_STEAM_GAME_REIVEW_QUERY = """
INSERT INTO steam_game_reviews (url_id, review_text, review_url)
VALUES (%s, %s, %s);
"""

FETCH_AND_MARK_SEEN_PROCEDURE = """
CREATE OR REPLACE FUNCTION fetch_and_mark_seen()
RETURNS TABLE(url_id INT, url_text VARCHAR) AS $$
BEGIN
    FOR url_id, url_text IN
        (SELECT id, url FROM urls WHERE NOT seen LIMIT 1 FOR UPDATE SKIP LOCKED)
    LOOP
        UPDATE urls SET seen = TRUE WHERE id = url_id;
        RETURN NEXT;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
"""

FETCH_AND_MARK_SEEN_CALL = "fetch_and_mark_seen"

COUNT_URL_INFOS_QUERY = "SELECT COUNT(*) FROM url_info;"

COUNT_GAME_INFOS_QUERY = "SELECT COUNT(*) FROM steam_game_info;"
