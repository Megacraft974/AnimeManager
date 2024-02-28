# from tkinter import *
from operator import itemgetter
from thefuzz import fuzz, process as fuzz_process
import time
from datetime import datetime, timezone, timedelta, time as datetime_time, tzinfo
import requests
from collections import defaultdict, deque
import re
import os
import threading
import queue
import multiprocessing
import json
import random
import sys
import os
import mysql.connector
from mysql.connector.errors import ProgrammingError

print('aaaa')

from .animeManager import Manager
from .getters import Getters
from .utils import TableFrame
from .animeAPI.JikanMoe import JikanMoeWrapper
from .classes import SortedDict, Anime, AnimeList, SortedList, RegroupList


# terms = 'classroom of the elite'
# data = main.api.searchAnime(terms, limit=main.animePerPage)
# while not data.empty():
# 	anime = data.get()
# 	if anime is not None:
# 		print(anime.title)

# main = Manager(remote=True)

try:
	mydb = mysql.connector.connect(
		host="localhost",
		user="web_user",
		password="ncFgz-mCBby/Us2g",
		database="anime_manager"
	)
except ProgrammingError as e:
	if e.errno == 1045:
		pass
	elif e.errno == 1049:
		pass
	else:
		raise

cur = mydb.cursor()
cur.execute('SHOW DATABASES')
for x in cur:
	print(x)

a = JikanMoeWrapper()

sys.exit()

db = main.getDatabase()

data = db.sql("SELECT * FROM animeRelations")
seen = set()

keys = ("id", "type", "name", "rel_id")

for rel in data:
    if rel in seen:
        db.sql(
            "DELETE FROM animeRelations WHERE id=? AND type=? AND name=? AND rel_id=?",
            rel,
        )
    else:
        seen.add(rel)


def send_animes():
    for i, anime in enumerate(
        db.sql("SELECT * FROM anime WHERE tag IS NOT null;", to_dict=True)
    ):
        anime = Anime(anime)

        def format_keys(key):
            key = str(key)
            if key in ("status", "like"):
                key = "has_" + key
            return key

# qb = Client("http://localhost:8080", REQUESTS_ARGS={'timeout': 2})
# qb.auth_log_in("admin", "1234567")

        url = "http://animemanager/add_anime.php?" + "&".join(
            format_keys(k) + "=" + format_values(v)
            for k, v in anime.items()
            if k not in anime.metadata_keys and v is not None
        )

        if anime["tag"] == "WATCHING":
            print(f"\n{url} -- {anime['tag']}\n")

        a = requests.get(url)
        print(i, anime["title"])
        for line in a.content.split(b"<br/>"):
            print(re.sub(b"<.*>", b"", line))
        # time.sleep(1)


for anime in db.sql("SELECT * FROM anime WHERE broadcast IS NOT null", to_dict=True):
    anime = Anime(anime)
    b = anime.broadcast

    weekday, hour, min = b.split("-")

    print(anime.id, anime.title, anime.broadcast, weekday, hour, min)
    db.sql(
        "INSERT INTO broadcasts(id, weekday, hour, minute) VALUES (?, ?, ?, ?)",
        (anime.id, weekday, hour, min),
    )

#         url = "http://animemanager/add_anime.php?" + '&'.join(format_keys(k) + "=" + format_values(
#             v) for k, v in anime.items() if k not in anime.metadata_keys and v is not None)

#         if anime['tag'] == "WATCHING":
#             print(f"\n{url} -- {anime['tag']}\n")

#         a = requests.get(url)
#         print(i, anime['title'])
#         for line in a.content.split(b"<br/>"):
#             print(re.sub(b'<.*>', b'', line))
#         # time.sleep(1)


# for anime in db.sql('SELECT * FROM anime WHERE broadcast IS NOT null', to_dict=True):
#     anime = Anime(anime)
#     b = anime.broadcast

#     weekday, hour, min = b.split('-')

#     print(anime.id, anime.title, anime.broadcast, weekday, hour, min)
#     db.sql('INSERT INTO broadcasts(id, weekday, hour, minute) VALUES (?, ?, ?, ?)',
#            (anime.id, weekday, hour, min))

# db.save()
