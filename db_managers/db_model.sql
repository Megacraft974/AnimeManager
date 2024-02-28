BEGIN
CREATE TABLE indexList ( id INTEGER NOT NULL AUTO_INCREMENT PRIMARY KEY, mal_id INTEGER, kitsu_id INTEGER, anilist_id INTEGER, anidb_id INTEGER);
CREATE TABLE genres ( id INTEGER NOT NULL, value INTEGER NOT NULL);
CREATE TABLE title_synonyms ( id INTEGER NOT NULL, value TEXT NOT NULL);
CREATE TABLE torrentsIndex ( id INTEGER NOT NULL, value TEXT NOT NULL);
CREATE TABLE animeRelations ( id INTEGER NOT NULL, type TEXT NOT NULL, name TEXT NOT NULL, rel_id INTEGER NOT NULL);
CREATE TABLE broadcasts ( id INTEGER NOT NULL UNIQUE, weekday INTEGER, hour INTEGER, minute INTEGER);
CREATE TABLE pictures ( id INTEGER NOT NULL, url TEXT, size TEXT);
CREATE TABLE characterRelations ( id INTEGER, anime_id INTEGER, role TEXT);
CREATE TABLE characters ( id INTEGER NOT NULL UNIQUE, name TEXT NOT NULL, picture TEXT, description TEXT);
CREATE TABLE genresIndex ( id INTEGER NOT NULL UNIQUE AUTO_INCREMENT PRIMARY KEY, mal_id INTEGER, kitsu_id INTEGER, anilist_id INTEGER, name TEXT);
CREATE TABLE charactersIndex ( id INTEGER NOT NULL UNIQUE AUTO_INCREMENT PRIMARY KEY, mal_id INTEGER UNIQUE, kitsu_id INTEGER UNIQUE, anilist_id INTEGER);
CREATE TABLE torrents ( hash VARCHAR(40) NOT NULL UNIQUE PRIMARY KEY, name TEXT, trackers TEXT);
CREATE TABLE user_tags ( user_id INTEGER NOT NULL, anime_id INTEGER NOT NULL, tag TEXT, liked INTEGER);
CREATE TABLE anime ( id INTEGER NOT NULL UNIQUE PRIMARY KEY, title TEXT, picture TEXT, date_from INTEGER, date_to INTEGER, synopsis TEXT, episodes INTEGER, duration INTEGER, rating TEXT, status TEXT, broadcast TEXT, last_seen INTEGER, trailer TEXT);
COMMIT
