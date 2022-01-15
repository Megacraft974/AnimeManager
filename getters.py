if __name__ == "__main__":
    import auto_launch

import threading
import os
import io
import hashlib
import time
import re
import requests
import queue
import traceback

from datetime import date
# from multiprocessing import Pool, Queue
from multiprocessing.pool import ThreadPool

import bencoding

from qbittorrentapi import Client
import qbittorrentapi.exceptions
from PIL import Image, ImageTk

from dbManager import thread_safe_db
from classes import Anime, ReturnThread, RegroupList

if 'database_threads' not in globals().keys():
    globals()['database_threads'] = {}


class Getters:
    def getDatabase(self=None):
        if self is None:
            self = type('EmptyObject', (), {})()
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
                database = thread_safe_db(self.dbPath)
                globals()['database_threads'][t] = database
                return database

    def getQB(self, use_thread=False, reconnect=False, update=True):
        if use_thread:
            threading.Thread(target=self.getQB, args=(False, reconnect), daemon=True).start()
            return
        try:
            if update and reconnect and self.qb is not None:
                self.qb.auth_log_out()
                self.log("MAIN_STATE",
                         "Logged off from qBittorrent client")
            if self.qb is None or not self.qb.is_logged_in:
                if update:
                    self.qb = Client(self.torrentApiAddress, REQUESTS_ARGS={'timeout': 2})
                    self.qb.auth_log_in(self.torrentApiLogin,
                                        self.torrentApiPassword)
                if self.qb is None or not self.qb.is_logged_in:
                    self.log(
                        'MAIN_STATE',
                        '[ERROR] - Invalid credentials for the torrent client!')
                    self.qb = None
                    state = "CREDENTIALS"
                else:
                    if update:
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
        if (isinstance(path, str) and os.path.isfile(path)) or isinstance(path, io.IOBase):
            img = Image.open(path)
            if size is not None:
                img = img.resize(size, Image.ANTIALIAS)
        else:
            img = Image.new('RGB', (10, 10) if size is None else size, self.colors['Gray'])
        return ImageTk.PhotoImage(img, master=self.root)

    @staticmethod
    def getStatus(anime):
        all_status = {  # TODO - Why is this a dict?
            'airing': 'AIRING',
            'Currently Airing': 'AIRING',
            'completed': 'FINISHED',
            'complete': 'FINISHED',
            'Finished Airing': 'FINISHED',
            'to_be_aired': 'UPCOMING',
            'tba': 'UPCOMING',
            'upcoming': 'UPCOMING',
            'Not yet aired': 'UPCOMING',
            'NONE': 'UNKNOWN',
            'UPDATE': 'UNKNOWN'}
        if anime.status is not None:
            if anime.status in all_status.values():
                return anime.status
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

    @staticmethod
    def getTorrentHash(path):
        objTorrentFile = open(path, "rb")

        decodedDict = bencoding.bdecode(objTorrentFile.read())

        info_hash = hashlib.sha1(bencoding.bencode(
            decodedDict[b"info"])).hexdigest()
        return info_hash

    @staticmethod
    def getMagnetHash(url):
        m = re.findall(r'magnet:\?xt=urn:btih:([a-fA-F0-9]*)', url)
        if len(m) > 0:
            return m[0]

    def getTorrentColor(self, title):
        def fileFormat(f):
            return ''.join(f.rsplit(".torrent", 1)[0].split(" ")).lower()
        timeNow = time.time()
        if hasattr(self, 'formattedTorrentFiles') and timeNow - self.formattedTorrentFiles[0] < 10:
            files = self.formattedTorrentFiles[1]
        else:
            files = [fileFormat(f) for f in os.listdir(self.torrentPath)]
            self.formattedTorrentFiles = (timeNow, files)

        pat_cache = {re.compile(pat, re.I): col for col, pats in self.fileMarkers.items() for pat in pats}

        fg = self.colors['White']
        for f in files:
            t = fileFormat(title)
            if t in f or f in t:
                fg = self.colors['Blue']
        else:
            for pat, color in pat_cache.items():
                if re.match(pat, title):
                    fg = self.colors[color]
                    break

        return fg

    @staticmethod
    def getFolderFormat(title):
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
            anime = database(id=id, table="anime")
            self.animeFolder = os.listdir(self.animePath)
        else:
            if not isinstance(anime, Anime):
                anime = Anime(anime)
            if id is None:
                id = anime.id

        for f in self.animeFolder:
            if not os.path.isdir(os.path.normpath(os.path.join(self.animePath, f))):
                continue

            try:
                f_id = int(f.rsplit(" ", 1)[1])
            except Exception:
                pass
            else:
                if f_id == id:
                    folder = os.path.normpath(os.path.join(self.animePath, f))
                    return folder
        folderFormat = self.getFolderFormat(anime.title)
        folderName = "{} - {}".format(folderFormat, id)
        folder = os.path.normpath(os.path.join(self.animePath, folderName))
        return folder

    def getEpisodes(self, folder):
        def folderLister(folder):
            if folder in {"", None} or not os.path.isdir(folder):
                return []
            files = []
            folders = []
            for f in os.listdir(folder):
                path = os.path.join(folder, f)
                if os.path.isdir(path):
                    folders.append(path)
                else:
                    files.append(path)

            yield files
            for path in folders:
                for f in folderLister(path):
                    yield f
        out = []
        videoSuffixes = ("mkv", "mp4", "avi")
        blacklist = ("Specials", "Extras")

        if folder == "" or folder is None or not os.path.isdir(
                os.path.join(self.animePath, folder)):
            return {}

        folder = folder + "/"
        folders = folderLister(os.path.join(self.animePath, folder))

        publisherPattern = re.compile(r'^\[(.*?)\]')

        epsPatternsFormat = (
            r"-\s(\d+)",
            r"(?:E|Episode|Ep|Eps)(\d+)",
            r" (\d+) ")
        epsPatterns = list(re.compile(p) for p in epsPatternsFormat)

        seasonPatternsFormat = (
            r'(?:S|Season|Seasons)\s?([0-9]{1,2})',
            r'([0-9])(?:|st|nd|rd|th)\s?(?:S|Season|Seasons)')
        seasonPatterns = list(re.compile(p)
                              for p in seasonPatternsFormat)

        for files in folders:
            eps = []
            for file in files:
                if os.path.isfile(file) and file.split(
                        ".")[-1] in videoSuffixes:
                    filename = os.path.basename(file)
                    self.log('FILE_SEARCH', filename, end=" - ")

                    result = re.findall(publisherPattern, file)  # [...]
                    if len(result) >= 1:
                        publisher = result[0] + " "
                    else:
                        publisher = "None"

                    episode = "?"

                    for p in epsPatterns:
                        m = re.findall(p, filename)
                        if len(m) > 0:
                            episode = m[0]
                            break
                    if episode == "?":
                        episode = str(len(eps) + 1).zfill(2)  # Hacky

                    season = 0
                    for p in seasonPatterns:
                        result = re.findall(p, file)
                        if len(result) >= 1:
                            season = result[0]
                            break

                    title = filename.rsplit(".", 1)[0]
                    title = re.sub(r'([\._])', ' ', title)  # ./,/-/_
                    title = re.sub(r'  +?', '', title)  # "  "
                    eps.append({'title': title, 'path': file,
                               'season': season, 'episode': episode})

            eps.sort(key=lambda d: int(
                str(d['season']).zfill(5) + str(d['episode']).zfill(5)))
            out.extend(eps)

        return out

    def getElemImages(self, que, imQueue=None, start_thread=True):
        if start_thread:
            self.log("THREAD", "Started image thread")
            imQueue = queue.Queue()
            threading.Thread(target=self.getImgThread, args=(que, imQueue), daemon=True).start()

        while not imQueue.empty():
            data = imQueue.get()
            if data == "STOP":
                self.log("THREAD", "All images loaded")
                return

            im, can = data
            try:
                image = ImageTk.PhotoImage(im)
                can.create_image(0, 0, image=image, anchor='nw')
                can.image = image
            except Exception:
                pass

        if self.root is not None and not self.closing:
            self.root.after(50, self.getElemImages, None, imQueue, False)

    def getImgThread(self, que, imQueue):
        global processes, no_internet

        def usePlaceholder(can):
            im = Image.open(os.path.join(self.iconPath, "placeholder.png"))
            im = im.resize((225, 310))
            return im, can

        def get_processes_data():
            if len(processes) == 0:
                return
            for data in filter(lambda t: t[0].ready(), processes):
                p, filename, can = data
                if not p.ready():
                    continue

                processes.remove(data)
                try:
                    req = p.get()
                except requests.exceptions.ReadTimeout as e:
                    self.log("PICTURE", "Timed out!")
                    imQueue.put(usePlaceholder(can))
                except requests.exceptions.ConnectionError as e:
                    self.log('PICTURE', "[ERROR] - No internet connection!")
                    imQueue.put(usePlaceholder(can))
                    no_internet = True
                except requests.exceptions.MissingSchema as e:
                    self.log("PICTURE", "[ERROR] - Invalid url!")
                    imQueue.put(usePlaceholder(can))
                else:
                    if req and req.status_code == 200:
                        raw_data = req.content
                        im = Image.open(io.BytesIO(raw_data))
                        im = im.resize((225, 310))
                        if im.mode != 'RGB':
                            im = im.convert('RGB')

                        try:
                            im.save(filename)
                        except FileNotFoundError:
                            self.log(
                                "DISK_ERROR",
                                "File not found error while saving image",
                                filename)
                        imQueue.put((im, can))
                    else:
                        continue  # TODO
                        self.log(
                            "PICTURE",
                            "[ERROR] Status code",
                            req.status_code,
                            "for anime id",
                            anime.id,
                            "requesting new picture.")
                        repdata = self.api.animePictures(anime.id)

                        if len(repdata) >= 1:  # TODO - Disabled - Wait for response + handle Characters too
                            anime.picture = repdata[-1]['small']
                            database = self.getDatabase()
                            database.sql("UPDATE anime SET picture = ? WHERE id = ?",
                                         (repdata[-1]['small'], anime.id), save=True, get_output=False)
                            que.put((anime, can))  # TODO - Check if it works
                        else:
                            imQueue.put(usePlaceholder(can))

        self.log("THREAD", "Started image thread")
        no_internet = False
        args = que.get()
        processes = []
        c = 0
        while args != "STOP":
            filename, url, can = args
            if no_internet:
                imQueue.put(usePlaceholder(can))

            if os.path.exists(filename):
                try:
                    with Image.open(filename) as im:
                        imQueue.put((im.copy(), can))
                    args = que.get()
                    continue
                except Exception:
                    self.log(
                        'DISK_ERROR',
                        "[ERROR] Image file is corrupted, deleting file",
                        filename)
                    os.remove(filename)

            self.log("PICTURE", "Requesting picture for url", url)

            if url is not None:
                p = ReturnThread(target=requests.get, args=(url,))
                processes.append((p, filename, can))
            else:
                imQueue.put(usePlaceholder(can))

            get_processes_data()

            args = que.get()

        while len(processes) > 0:
            get_processes_data()
            time.sleep(0.1)

        imQueue.put("STOP")
        self.log("THREAD", "Stopped image thread")
        return

    def get_relations(self, id, **filters):
        data = self.database.sql("SELECT * FROM relations WHERE id=?", (id,), to_dict=True)
        return RegroupList("id", ["rel_id"], *(filter(lambda e: all(e[k] == v for k, v in filters.items()), data)))
