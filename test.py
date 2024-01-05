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
from qbittorrentapi import Client
import random
import sys
import os




try:
    from .animeManager import Manager
    from .getters import Getters
    from .utils import TableFrame
    from .animeAPI.JikanMoe import JikanMoeWrapper
    from .classes import SortedDict, Anime, AnimeList, SortedList, RegroupList
    from . import dbManager

except ImportError:
    sys.path.append(os.path.abspath("../"))
    import AnimeManager.test

    sys.exit()

appdata = os.path.join(os.getenv("APPDATA"), "Anime Manager")
dbPath = os.path.join(appdata, "animeData.db")

# db = Getters.getDatabase()
main = Manager(remote=True)
db = main.getDatabase()

data = db.sql('SELECT id, date_from, date_to FROM anime', save=False)
out = []
epoch = datetime(1970, 1, 1)
for i, f, t in data:
    tmp = [i]
    for d in (f, t):
        if d is None or d == 'None':
            tmp.append(None)
        elif isinstance(d, int):
            tmp.append(d)
        else:
            d = datetime.fromisoformat(d)
            tmp.append(int((d - epoch).total_seconds()))
    out.append(tmp)

db.executemany('UPDATE anime SET date_to=?, date_from=? WHERE id=?', list(map(lambda a: a[::-1], out)))
db.save()

a = main.api.anime(2)
if a:
    pass

sys.exit()


qb = Client("http://localhost:8080", REQUESTS_ARGS={"timeout": 2})
qb.auth_log_in("admin", "1234567")

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

        def format_values(val):
            if type(val) != str:
                val = str(val)
            if "\\" in val:
                val = val.replace("\\", "/")
            return val

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

db.save()
