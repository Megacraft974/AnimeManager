# import re,requests,urllib,socket

# url = "magnet:?xt=urn:btih:RRN4MNLGBHMAVYU372YXQ46NU3WVZ5WR&dn=%5BSubsPlease%5D%20Mushoku%20Tensei%20-%2015%20%28720p%29%20%5B14A68BE1%5D.mkv&xl=686477749&tr=http%3A%2F%2Fnyaa.tracker.wf%3A7777%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2F9.rarbg.to%3A2710%2Fannounce&tr=udp%3A%2F%2F9.rarbg.me%3A2710%2Fannounce&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.internetwarriors.net%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.cyberia.is%3A6969%2Fannounce&tr=udp%3A%2F%2Fexodus.desync.com%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker3.itzmx.com%3A6961%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce&tr=udp%3A%2F%2Ftracker.tiny-vps.com%3A6969%2Fannounce&tr=udp%3A%2F%2Fretracker.lanta-net.ru%3A2710%2Fannounce&tr=http%3A%2F%2Fopen.acgnxtracker.com%3A80%2Fannounce&tr=wss%3A%2F%2Ftracker.openwebtorrent.com"
# pattern = re.compile(r"^magnet:?")

# print(str("0x41727101980"))

# def getTracker(protocol,url,port,info_hash,size):
#     params = {
#         'info_hash': info_hash,
#         'peer_id': "weshweshcava12345678",
#         'port': port,
#         'uploaded': '0',
#         'downloaded': '0',
#         'left': str(size),
#         'compact': '1',
#         'no_peer_id': '0',
#         'event': 'started'
#     }
#     if protocol == "http":
#         try:
#             page = requests.get(url, params=params)
#         except ConnectionResetError as e:
#             print(e)
#         except requests.exceptions.ConnectionError as e:
#             print(2,e)
#         except requests.exceptions.InvalidSchema as e:
#             print(3,e)
#         else:
#             print("---",page.text)
#     elif protocol == "udp":
#         sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
#         sock.sendto(bytes(MESSAGE, "utf-8"), (UDP_IP, UDP_PORT))
#     else:
#         print(protocol,"not supported")

# if pattern.match(url):
#     print("Magnet!")

#     parameters = re.compile(r"(\w{2})=([^&]+)")
#     data = list((a,urllib.parse.unquote(b)) for a,b in parameters.findall(url))
#     for i,d in enumerate(data):
#         k,v = d
#         if k == "tr":
#             try:
#                 v = urllib.parse.urlparse(v)
#             except Exception as e:
#                 print(e)
#         else:
#             print(k,v)
#         data[i] = (k,v)

#     print("___________")
#     info_hash = [d[1] for d in data if d[0] == "xt"][0].split(":")[-1]
#     size = [d[1] for d in data if d[0] == "xl"][0]
#     print(info_hash,size)
#     for k,v in (d for d in data if d[0] == "tr"):
#         url = urllib.parse.urlunparse(v)
#         print(url)
#         getTracker(v.scheme,url,v.port,info_hash,size)

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



fen = Tk()
keys = list("abcdefghi")
table = TableFrame(fen, dict(zip("abcdefghi".upper(), keys)), print, main_key="title")
table.configure(
    bd=0,
    height=1,
    relief='solid',
    font=(
        "Source Code Pro Medium",
        13),
    activebackground="#181915",
    activeforeground="#FFFFFF",
    bg="#181915",
    fg="#FFFFFF"
)
table.configure_keys(bg="#383935", activebackground="#181915", border="#FF0000")

data = [{k: random.randint(0, 100) for k in keys} for i in range(20)]
print(data)
table.extend(data)
table.update()
table.pack(expand=True, fill="both")
fen.mainloop()