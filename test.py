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

db = Getters.getDatabase()

qb = Client("http://localhost:8080", REQUESTS_ARGS={'timeout': 2})
qb.auth_log_in("admin", "1234567")

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


    url = "http://localhost/anime_manager/add_anime.php?" + '&'.join(format_keys(k) + "=" + format_values(v) for k, v in anime.items() if k not in anime.metadata_keys and v is not None)

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
