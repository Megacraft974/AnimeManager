# from tkinter import *
from operator import itemgetter
from thefuzz import fuzz, process as fuzz_process
from getters import Getters
import time
from datetime import datetime, timezone, timedelta, time as datetime_time
import requests
from classes import SortedDict, Anime, AnimeList, SortedList, RegroupList
import re
import os
import threading
import queue
import multiprocessing
import json
from qbittorrentapi import Client
import random
from animeManager import Manager
import search_engines
import search_engines.nova3.custom_engine
from media_players import MediaPlayers
from tkinter import *

from utils import *

import classes
from animeAPI.JikanMoe import JikanMoeWrapper
appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
dbPath = os.path.join(appdata, "animeData.db")


# path = "C:/Users/William/Documents/AnimeManager/Animes/Chainsaw Man - 17794/[SubsPlease] Chainsaw Man - 01 (720p) [88C94187].mkv"

# if __name__ == '__main__':
	
	# multiprocessing.freeze_support()
	# man = MediaPlayers()
	# name, player = list(man.media_players.items())[1]
	# print(name)
	# player([path])

if __name__ == '__main__':
	multiprocessing.freeze_support()
	p = multiprocessing.current_process()
	if p.name == 'MainProcess':
		m = Manager(remote=True)

		hash = 'b15810986dad9c6f46a09221912ebefdd598b6d1'
		path = 'E:\\AnimeManager\\Animes\\Liar Liar - 27046'
		m.tm.move(path, [hash])

if False:
	fen = Tk()
	Label(fen, text='loooool').pack()
	frame = Frame(fen)
	frame.pack(fill='both')
	table = TableFrame(frame, {'titre': 'title', 'col': 'row', 'autre': 'looool'}, cb=print)
	table.extend([{'title': f'aaaa{i}', 'row': i} for i in range(50)])
	table.draw_table()
	table.pack()
	fen.mainloop()

# db = Getters.getDatabase()

# qb = Client("http://localhost:8080", REQUESTS_ARGS={'timeout': 2})
# qb.auth_log_in("admin", "1234567")

# data = db.sql('SELECT * FROM animeRelations')
# seen = set()

# keys = ('id',
#         'type',
#         'name',
#         'rel_id')

# for rel in data:
#     if rel in seen:
#         db.sql(
#             'DELETE FROM animeRelations WHERE id=? AND type=? AND name=? AND rel_id=?', rel)
#     else:
#         seen.add(rel)


# def send_animes():
#     for i, anime in enumerate(db.sql("SELECT * FROM anime WHERE tag IS NOT null;", to_dict=True)):
#         anime = Anime(anime)

#         def format_keys(key):
#             key = str(key)
#             if key in ('status',
#                        'like'):
#                 key = "has_" + key
#             return key

#         def format_values(val):
#             if type(val) != str:
#                 val = str(val)
#             if "\\" in val:
#                 val = val.replace("\\", "/")
#             return val

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
