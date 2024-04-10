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

db = main.getDatabase()

main.getSchedule(force=True)

pass
# data = main.api.schedule(limit=main.maxTrendingAnime)

# queue = []

# timeout = time.time() + main.scheduleTimeout

# while not data.empty():
# 	anime = data.get(timeout=10)
# 	if anime is None or len(anime) == 0:
# 		continue

# 	queue.append(anime)

# pass