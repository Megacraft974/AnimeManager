from tkinter import *
from thefuzz import fuzz, process as fuzz_process
from getters import Getters
import time
from datetime import datetime, timezone, timedelta, time as datetime_time
import requests
from collections import defaultdict, deque
from classes import SortedDict, Anime, AnimeList, SortedList, RegroupList
import re, os, threading, queue, multiprocessing, json
from qbittorrentapi import Client
import random
from animeManager import Manager

from utils import TableFrame

import classes
from animeAPI.JikanMoe import JikanMoeWrapper
appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
dbPath = os.path.join(appdata, "animeData.db")

# api = JikanMoeWrapper(dbPath)
# print(api.anime(5))
# for a in api.schedule():
#     print('-', a, type(a))

db = Getters.getDatabase()

qb = Client("http://localhost:8080", REQUESTS_ARGS={'timeout': 2})
qb.auth_log_in("admin", "1234567")

def send_animes():
    for i, anime in enumerate(db.sql("SELECT * FROM anime WHERE tag IS NOT null;", to_dict=True)):
        anime = Anime(anime)


        def format_keys(key):
            key = str(key)
            if key in ('status', 'like'):
                key = "has_" + key
            return key


        def format_values(val):
            if type(val) != str:
                val = str(val)
            if "\\" in val:
                val = val.replace("\\", "/")
            return val


        url = "http://animemanager/add_anime.php?" + '&'.join(format_keys(k) + "=" + format_values(v) for k, v in anime.items() if k not in anime.metadata_keys and v is not None)

        if anime['tag'] == "WATCHING":
            print("\n")
            print(url)
            print("--", anime["tag"])
            print("\n")

        a = requests.get(url)
        print(i, anime['title'])
        for line in a.content.split(b"<br/>"):
            print(re.sub(b'<.*>', b'', line))
        # time.sleep(1)

for anime in db.sql('SELECT * FROM anime WHERE broadcast IS NOT null', to_dict=True):
    anime = Anime(anime)
    b = anime.broadcast
    
    weekday, hour, min = b.split('-')

    print(anime.id, anime.title, anime.broadcast, weekday, hour, min)
    db.sql('INSERT INTO broadcasts(id, weekday, hour, minute) VALUES (?, ?, ?, ?)', (anime.id, weekday, hour, min))

db.save()