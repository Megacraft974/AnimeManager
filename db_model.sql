CREATE TABLE anime (
    "id"    INTEGER NOT NULL UNIQUE,
    "title" TEXT,
    "picture"   TEXT,
    "date_from" TEXT,
    "date_to"   TEXT,
    "synopsis"  TEXT,
    "episodes"  INTEGER,
    "duration"  INTEGER,
    "rating"    TEXT,
    "status"    TEXT,
    "broadcast" TEXT,
    "last_seen" INTEGER,
    "trailer"   TEXT,
    "like"  INTEGER,
    "tag"   TEXT,
    PRIMARY KEY("id")
);
CREATE TABLE indexList (
    "id"    INTEGER NOT NULL UNIQUE,
    "mal_id"    INTEGER UNIQUE,
    "kitsu_id"    INTEGER UNIQUE,
    "anilist_id"    INTEGER UNIQUE,
    "anidb_id"    INTEGER UNIQUE,
    PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE charactersIndex (
    "id"    INTEGER NOT NULL UNIQUE,
    "mal_id"    INTEGER UNIQUE,
    "kitsu_id"    INTEGER UNIQUE,
    "anilist_id"    INTEGER UNIQUE,
    PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE characters (
    "id"    INTEGER NOT NULL,
    "anime_id"    INTEGER NOT NULL,
    "name"    TEXT NOT NULL,
    "role"    TEXT,
    "picture"    TEXT,
    "desc"    TEXT,
    "like"    INTEGER
);
CREATE TABLE genresIndex (
    "id"    INTEGER NOT NULL UNIQUE,
    "mal_id"    INTEGER,
    "kitsu_id"  INTEGER,
    "anilist_id"    INTEGER,
    "name"  INTEGER,
    PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE genres (
    "id"    INTEGER NOT NULL,
    "value" INTEGER NOT NULL
);
CREATE TABLE title_synonyms (
    "id"    INTEGER NOT NULL,
    "value" TEXT NOT NULL
);
CREATE TABLE torrents (
    "id"    INTEGER NOT NULL,
    "value" TEXT NOT NULL
);
CREATE TABLE broadcasts (
    "id" INTEGER NOT NULL, 
    "weekday" INTEGER, 
    "hour" INTEGER, 
    "minute" INTEGER
);
CREATE TABLE animeRelations (
    "id" INTEGER NOT NULL,
    "rel_id" INTEGER NOT NULL,
    "type" TEXT,
    "name" TEXT
);
CREATE TABLE pictures (
    "id" INTEGER NOT NULL,
    "url" TEXT,
    "size"
)