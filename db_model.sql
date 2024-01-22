BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "indexList" (
	"id"	INTEGER NOT NULL UNIQUE,
	"mal_id"	INTEGER UNIQUE,
	"kitsu_id"	INTEGER UNIQUE,
	"anilist_id"	INTEGER UNIQUE,
	"anidb_id"	INTEGER UNIQUE,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "genres" (
	"id"	INTEGER NOT NULL,
	"value"	INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS "title_synonyms" (
	"id"	INTEGER NOT NULL,
	"value"	TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "torrentsIndex" (
	"id"	INTEGER NOT NULL,
	"value"	TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "animeRelations" (
	"id"	INTEGER NOT NULL,
	"type"	TEXT NOT NULL,
	"name"	TEXT NOT NULL,
	"rel_id"	INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS "broadcasts" (
	"id"	INTEGER NOT NULL UNIQUE,
	"weekday"	INTEGER,
	"hour"	INTEGER,
	"minute"	INTEGER
);
CREATE TABLE IF NOT EXISTS "pictures" (
	"id"	INTEGER NOT NULL,
	"url"	TEXT,
	"size"	TEXT
);
CREATE TABLE IF NOT EXISTS "characterRelations" (
	"id"	INTEGER,
	"anime_id"	INTEGER,
	"role"	TEXT
);
CREATE TABLE IF NOT EXISTS "characters" (
	"id"	INTEGER NOT NULL UNIQUE,
	"name"	TEXT NOT NULL,
	"picture"	TEXT,
	"desc"	TEXT,
	"like"	INTEGER
);
CREATE TABLE IF NOT EXISTS "genresIndex" (
	"id"	INTEGER NOT NULL UNIQUE,
	"mal_id"	INTEGER,
	"kitsu_id"	INTEGER,
	"anilist_id"	INTEGER,
	"name"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "charactersIndex" (
	"id"	INTEGER NOT NULL UNIQUE,
	"mal_id"	INTEGER UNIQUE,
	"kitsu_id"	INTEGER UNIQUE,
	"anilist_id"	INTEGER,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "torrents" (
	"hash"	TEXT NOT NULL UNIQUE,
	"name"	TEXT,
	"trackers"	TEXT,
	PRIMARY KEY("hash")
);
CREATE TABLE IF NOT EXISTS "rateLimiters" (
	"id"	TEXT NOT NULL,
	"name"	TEXT NOT NULL,
	"value"	INTEGER,
	PRIMARY KEY("id","name")
);
CREATE TABLE IF NOT EXISTS "user_tags" (
	"user_id"	INTEGER NOT NULL,
	"anime_id"	INTEGER NOT NULL,
	"tag"	TEXT,
	"liked"	INTEGER,
	PRIMARY KEY("user_id","anime_id")
);
CREATE TABLE IF NOT EXISTS "anime" (
	"id"	INTEGER NOT NULL UNIQUE,
	"title"	TEXT,
	"picture"	TEXT,
	"date_from"	INTEGER,
	"date_to"	INTEGER,
	"synopsis"	TEXT,
	"episodes"	INTEGER,
	"duration"	INTEGER,
	"rating"	TEXT,
	"status"	TEXT,
	"broadcast"	TEXT,
	"last_seen"	INTEGER,
	"trailer"	TEXT,
	PRIMARY KEY("id")
);
COMMIT;
