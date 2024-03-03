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


from .constants import Constants
from .animeManager import Manager
from .getters import Getters
from .utils import TableFrame
from .animeAPI.JikanMoe import JikanMoeWrapper
from .classes import SortedDict, Anime, AnimeList, SortedList, RegroupList
from .db_managers.dbManager import db_instance

# terms = 'classroom of the elite'
# data = main.api.searchAnime(terms, limit=main.animePerPage)
# while not data.empty():
# 	anime = data.get()
# 	if anime is not None:
# 		print(anime.title)

main = Manager(remote=True)

mydb = main.getDatabase()

if not hasattr(main, 'dbPath'):
	appdata = Constants.getAppdata()
	main.dbPath = os.path.join(appdata, "animeData.db") # type: ignore
db = db_instance(main.dbPath) # type: ignore

mydb.execute('DROP DATABASE anime_manager;')
mydb.save()

is_none = lambda e: e is None or e == 'None'

mydb = main.getDatabase()
mydb.execute('SHOW TABLES')
for x in mydb.cur.fetchall():
	print(x[0])
	db.execute(f'SELECT * FROM {x[0]}')
	desc = [e[0].replace('desc', 'description') for e in db.cur.description]
	while True:
		data = db.cur.fetchone()
		if data is None:
			break
		desc_tmp = list(map(lambda e: e[1], filter(lambda e: not is_none(data[e[0]]), enumerate(desc))))
		keys = ', '.join(desc_tmp)
		values = ('%s, ' * len(desc_tmp))[:-2]
		sql = f'INSERT INTO {x[0]}({keys}) VALUES ({values})'
		data = list(filter(lambda e: not is_none(e), data))
		try:
			mydb.execute(sql, data)
		except Exception as e:
			pass
		pass
	mydb.save()

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
