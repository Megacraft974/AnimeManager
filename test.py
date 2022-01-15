from tkinter import *
from thefuzz import fuzz, process as fuzz_process
from getters import Getters
import time
from collections import defaultdict, deque
from classes import SortedDict, Anime, AnimeList, SortedList, RegroupList
import re, os, threading, queue, multiprocessing, json
from qbittorrentapi import Client
import random

from utils import TableFrame

db = Getters.getDatabase()

qb = Client("http://localhost:8080", REQUESTS_ARGS={'timeout': 2})
qb.auth_log_in("admin", "1234567")


anime = db(id=9902, table="anime")

fen = Tk()

a = fen.after(1000, print)
print(a, dir(a))
fen.after_cancel(a)
print(a, dir(a))