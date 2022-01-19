from tkinter import *
from thefuzz import fuzz, process as fuzz_process
from getters import Getters
import time
import requests
from collections import defaultdict, deque
from classes import SortedDict, Anime, AnimeList, SortedList, RegroupList
import re, os, threading, queue, multiprocessing, json
from qbittorrentapi import Client
import random

from utils import TableFrame

db = Getters.getDatabase()

qb = Client("http://localhost:8080", REQUESTS_ARGS={'timeout': 2})
qb.auth_log_in("admin", "1234567")

for anime in db.sql("SELECT * FROM anime WHERE tag='WATCHING';", to_dict=True):
    anime = Anime(anime)


    def format_values(val):
        if type(val) == str:
            val = '"' + val + '"'
        else:
            val = str(val)
        if "\\" in val:
            val = val.replace("\\", "/")
        return val


    url = "http://animemanager/add_anime.php?" + '&'.join(str(k) + "=" + format_values(v) for k, v in anime.items() if k not in anime.metadata_keys and v is not None)

    # print(url)

    a = requests.get(url)
    print(anime['title'])
    # for line in a.content.split(b"<br/>"):
    #     print(line)