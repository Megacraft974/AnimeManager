import threading
import os
import hashlib
import time
import re

import bencoding

from qbittorrentapi import Client
import qbittorrentapi.exceptions

from dbManager import db
from PIL import Image, ImageTk
from classes import Anime

if 'database_threads' not in globals().keys():
    globals()['database_threads'] = {}


class Getters:
    def getDatabase(self):
        if threading.main_thread() == threading.current_thread() and hasattr(self, "database"):
            return self.database
        else:
            for db_t in list(globals()['database_threads'].keys()):
                if not db_t.is_alive():
                    del globals()['database_threads'][db_t]

            t = threading.current_thread()
            if t in globals()['database_threads'].keys():
                return globals()['database_threads'][t]
            else:
                if not hasattr(self, 'dbPath'):
                    appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
                    self.dbPath = os.path.join(appdata, "animeData.db")
                database = db(self.dbPath)
                globals()['database_threads'][t] = database
                return database

    def getQB(self, use_thread=False, reconnect=False):
        if use_thread:
            threading.Thread(target=self.getQB, args=(False, reconnect)).start()
            return
        try:
            if reconnect:
                if self.qb is not None:
                    self.qb.auth_log_out()
                    self.log("MAIN_STATE",
                             "Logged off from qBittorrent client")
            if self.qb is None or not self.qb.is_logged_in:
                self.qb = Client(self.torrentApiAddress)
                self.qb.auth_log_in(self.torrentApiLogin,
                                    self.torrentApiPassword)
                if not self.qb.is_logged_in:
                    self.log(
                        'MAIN_STATE',
                        '[ERROR] - Invalid credentials for the torrent client!')
                    self.qb = None
                    state = "CREDENTIALS"
                else:
                    self.qb.app_set_preferences(self.qb_settings)
                    self.log(
                        'MAIN_STATE',
                        'Qbittorrent version:',
                        self.qb.app_version(),
                        "- web API version:",
                        self.qb.app_web_api_version())
                    # self.log('MAIN_STATE','Connected to torrent client')
                    state = "OK"
            else:
                state = "OK"
        except qbittorrentapi.exceptions.NotFound404Error as e:
            self.qb = None
            self.log('MAIN_STATE',
                     '[ERROR] - Error 404 while connecting to torrent client')
            state = "ADDRESS"
        except qbittorrentapi.exceptions.APIConnectionError as e:
            self.qb = None
            self.log('MAIN_STATE',
                     '[ERROR] - Error while connecting to torrent client')
            state = "ADDRESS"
        return state

    def getImage(self, path, size=None):
        if path is not None and os.path.isfile(path):
            img = Image.open(path)
        else:
            img = Image.new('RGB', (10, 10), self.colors['Gray'])
        if size is not None:
            img = img.resize(size)
        return ImageTk.PhotoImage(img, master=self.root)

    def getStatus(self, anime, reverse=True):
        if anime.status is not None:
            if anime.status in self.status.values():
                return anime.status
            if anime.status == 'NONE':
                self.log('DB_ERROR', "Unknown status for id", id)
            if anime.status == 'UPDATE':
                return 'UNKNOWN'
            return anime.status

        if anime.date_from is None:
            status = 'UNKNOWN'
        else:
            if date.fromisoformat(anime.date_from) > date.today():
                status = 'UPCOMING'
            else:
                if anime.date_to is None:
                    if anime.episodes == 1:
                        status = 'FINISHED'
                    else:
                        status = 'AIRING'
                else:
                    if date.fromisoformat(anime.date_to) > date.today():
                        status = 'AIRING'
                    else:
                        status = 'FINISHED'
        return status

    def getTorrentName(self, file):
        with open(file, 'rb') as f:
            m = re.findall(rb"name\d+:(.*?)\d+:piece length", f.read())
        if len(m) != 0:
            return m[0].decode()
        else:
            return None

    def getTorrentHash(self, path):
        objTorrentFile = open(path, "rb")
        try:
            decodedDict = bencoding.bdecode(objTorrentFile.read())
        except Exception as e:
            raise e

        info_hash = hashlib.sha1(bencoding.bencode(
            decodedDict[b"info"])).hexdigest()
        return info_hash

    def getTorrentColor(self, title):
        def fileFormat(f):
            return ''.join(f.rsplit(".torrent", 1)[0].split(" ")).lower()
        timeNow = time.time()
        if hasattr(self, 'formattedTorrentFiles') and timeNow - \
                self.formattedTorrentFiles[0] < 10:
            files = self.formattedTorrentFiles[1]
        else:
            files = [fileFormat(f) for f in os.listdir(self.torrentPath)]
            self.formattedTorrentFiles = (timeNow, files)

        fg = self.colors['White']
        for f in files:
            t = fileFormat(title)
            if t in f or f in t:
                fg = self.colors['Blue']
        else:
            for color, marks in self.fileMarkers.items():
                for mark in marks:
                    if mark in title.lower():
                        fg = self.colors[color]
                        break
        return fg

    def getFolderFormat(self, title):
        chars = []
        spaceLike = list("-")
        if title is None:
            return " "
        for char in title:
            if char.isalnum() or char == " ":
                chars.append(char)
            if char in spaceLike:
                chars.append(" ")
        return "".join(chars)

    def getFolder(self, id=None, anime=None):
        if anime is None or anime == {}:
            if id is None:
                raise Exception("Id required!")
            database = self.getDatabase()
            anime = database(id=id, table="anime").get()
            self.animeFolder = os.listdir(self.animePath)
        else:
            if not isinstance(anime, Anime):
                anime = Anime(anime)
            if id is None:
                id = anime.id

        for f in self.animeFolder:
            f_id = int(f.rsplit(" ", 1)[1])
            if f_id == id:
                folder = os.path.normpath(os.path.join(self.animePath, f))
                return folder
        folderFormat = self.getFolderFormat(anime.title)
        folderName = "{} - {}".format(folderFormat, id)
        folder = os.path.normpath(os.path.join(self.animePath, folderName))
        return folder
