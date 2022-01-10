# if __name__ == "__main__":
#     multiprocessing.freeze_support()
#     import auto_launch

globals()['auto_launch_initialized'] = True

import ctypes
import io
import json
import multiprocessing
import os
import queue
import re
import shutil
import socket
import subprocess
import threading
import time
import traceback
import urllib
import webbrowser
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timedelta
from operator import itemgetter
from tkinter import *

try:
    import bencoding
    # from bs4 import BeautifulSoup
    from lxml import etree
    from PIL import Image, ImageTk
    import qbittorrentapi.exceptions
    import requests
    from thefuzz import fuzz

    import sys
    if getattr(sys, 'frozen', None):
        basedir = sys._MEIPASS
        os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(basedir, 'certifi', 'cacert.pem')  # Required for requests and certifi
except ModuleNotFoundError as e:
    import sys
    if getattr(sys, 'frozen', None):
        print("Module missing:", e)
    else:
        print("Installing modules!", e)
        subprocess.run("pip install qbittorrent-api lxml jikanpy jsonapi_client requests Pillow bencoding bs4 thefuzz python-Levenshtein pytube python-mpv ffpyplayer python-vlc")
        # os.execv(sys.argv[0], sys.argv)
    time.sleep(20)

    sys.exit()

try:
    import utils
    import search_engines
    import animeAPI
    import windows

    from constants import Constants
    from logger import Logger
    from update_utils import UpdateUtils
    from getters import Getters
    from media_players import MediaPlayers
    from dbManager import db
    from classes import Anime, Character, AnimeList, TorrentList, SortedList, SortedDict
except ModuleNotFoundError as e:
    print(e)
    print("Please verify your app installation!")
    import sys
    sys.exit()


# TODO - Load new images on downloading error
# TODO - Scrollbar thumb is going out of range
# TODO - Implement the TableFrame class
# TODO - Add filter for torrent list (seeds / name)
# TODO - Play button on media player isn't centered
# TODO - Update the loading... text on media player
# TODO - Put single files in directories
# TODO - Add search by studios
# TODO - Add pictures window
# TODO - Allow window resizing
# TODO - Online search raise database is locked error
# TODO - Use the db.get_lock() with API wrappers
# TODO - Improve torrent matching algorithm
# TODO - Auto associate latest torrents?
# TODO - Add python-based torrent client
# TODO - Add RSS option
# TODO - Automatic torrent downloading from RSS?
# TODO - Compile into an executable
# TODO - Fix media player problem with executable
# TODO - Phone version


class Manager(Constants, Logger, UpdateUtils, Getters, MediaPlayers, *windows.windows):
    def __init__(self, remote=False):
        self.start = time.time()
        Logger.__init__(self)
        Constants.__init__(self)
        MediaPlayers.__init__(self)

        self.remote = remote
        self.animeFolder = []
        self.searchQueue = []
        self.relationIds = []
        self.characterIds = []
        self.timer_id = None
        self.stopSearch = False
        self.closing = False
        self.maxLogsSize = 50000  # In bytes
        self.blank_image = None

        self.qb = None
        self.root = None
        self.fen = None
        self.choice = None
        self.publisherChooser = None
        self.fileChooser = None
        self.torrentFilesChooser = None
        self.loadfen = None
        self.characterList = None
        self.characterInfo = None
        self.settings = None
        self.diskfen = None
        self.popupWindow = None

        self.menuOptions = {
            'Liked characters': {'color': 'Green', 'command': lambda: self.characterListWindow("LIKED")},
            'Disk manager': {'color': 'Orange', 'command': self.diskWindow},
            'Clear logs': {'color': 'Green', 'command': self.clearLogs},
            'Clear cache': {'color': 'Blue', 'command': self.clearCache},
            'Clear db': {'color': 'Red', 'command': self.clearDb},
            'Settings': {'color': 'Gray', 'command': self.settingsWindow},
            'Reload': {'color': 'Orange', 'command': self.reloadAll},
            'Exit': {'color': 'Red', 'command': self.quit}}
        self.actionButtons = (
            {'text': 'Copy title', 'color': 'Green', 'command': self.copy_title},
            {'text': 'Reload', 'color': 'Blue', 'command': self.reload},
            {'text': 'Redownload files', 'color': 'Green', 'command': self.redownload},
            {'text': 'Characters', 'color': 'Green', 'command': self.characterListWindow},
            {'text': 'Delete seen episodes', 'color': 'Blue', 'command': self.deleteSeenEpisodes},
            {'text': 'Delete all files', 'color': 'Red', 'command': self.deleteFiles},
            {'text': 'Remove from db', 'color': 'Red', 'command': self.delete},)

        with self.getDatabase() as self.database:
            if not os.path.exists(self.dbPath):
                self.checkSettings()
                self.reloadAll()
                return
            else:
                self.checkSettings()

            self.api = animeAPI.AnimeAPI('all', self.dbPath)
            self.player = self.media_players[self.player_name]
            self.getQB(use_thread=True)

            if not self.remote:
                try:
                    self.initWindow()
                except Exception as e:
                    self.log("MAIN_STATE", "[ROOT]:\n", traceback.format_exc())

                self.log('MAIN_STATE', "Stopping")
                self.start = time.time()
                self.updateAll()
                self.database.close()
                self.log('TIME', "Stopping time:".ljust(25),
                         round(time.time() - self.start, 2), 'sec')

    # ___Search___
    def search(self, *args, force_search=False):
        terms = None
        loop = True
        terms = self.searchTerms.get()
        if len(terms) > 2 or force_search:
            if not force_search:
                animeList = self.searchDb(terms)
            if not force_search and animeList is not False:
                self.animeList.set(animeList)
            else:
                self.stopSearch = False
                self.loading()
                # self.animeList.set(self.searchAnime(terms))
                self.animeList.set(self.api.searchAnime(terms, limit=self.animePerPage))
        else:
            self.animeList.from_filter("DEFAULT")

        if self.root is None:
            return
        self.fen.update()

    def searchDb(self, terms):
        def fuzzy_enumerator(terms):  # Unused
            sql = """
                SELECT value, anime.*
                FROM title_synonyms
                JOIN anime using(id)
                GROUP BY anime.id
                ORDER BY anime.date_from DESC;
            """

            match_threshold = 70
            partial_threshold = 50
            keys = list(self.database.keys(table="anime"))
            match = SortedList(keys=[(lambda e: e[1], True)])
            partial = []
            for data in self.database.sql(sql):
                ratio = fuzz.WRatio(terms, data[0])
                if ratio >= match_threshold:
                    match.append((data[1:], ratio))
                elif ratio >= partial_threshold:
                    partial.append((data[1:], ratio))
            if len(match) == 0:
                yield False
                return
            else:
                yield True
            for data in match + partial:
                yield Anime(keys=keys, values=data[0])

        def like_enumerator(terms):
            sql = """
                SELECT anime.*
                FROM anime
                JOIN title_synonyms using(id)
                GROUP BY anime.id HAVING value LIKE "%{}%"
                ORDER BY anime.date_from DESC;
            """

            keys = list(self.database.keys(table="anime"))
            matchs = self.database.sql(sql.format(terms))
            if len(matchs) == 0:
                yield False
                return
            else:
                yield True
                for m in matchs:
                    yield Anime(keys=keys, values=m)

        terms = "".join([c for c in terms if c.isalnum()]).lower()
        # return self.searchNgrams(terms)

        enum = like_enumerator(terms)
        if next(enum):
            anime_list = AnimeList(enum)
            return anime_list
        else:
            return False

    def searchNgrams(self, terms):  # TODO
        def ngrams(string, n=3):
            string = [l for l in string.lower() if l.isalnum() or l == " "]
            ngrams = zip(*[string[i:] for i in range(n)])
            return (''.join(ngram) for ngram in ngrams)

        with self.database.get_lock():
            data = self.database.sql("SELECT id, value FROM title_synonyms")

            t_ngrams = set(ngrams(terms))
            matches = defaultdict(lambda: 0)
            for id, value in data:
                # for ngram in ngrams(value):
                    if ngram in t_ngrams:
                        matches[id] += 1

            sql = 'SELECT * FROM anime WHERE id IN(' + ','.join("?" * len(matches)) + ');'
            return AnimeList(
                Anime(data)
                for data in SortedList(
                    [(lambda e: matches[e['id']], True)]
                ).extend(
                    self.database.sql(
                        sql,
                        matches.keys(),
                        to_dict=True
                    )
                )
            )

    def searchTorrents(self, id, titles=None):
        def sortkey(k):
            score = 0
            if k[0] in self.topPublishers:
                score = len(self.topPublishers) - \
                    self.topPublishers.index(k[0])
            marked = ('dual', 'dub')
            breakLock = False
            for mark in marked:
                for title in k[1]:
                    if mark in title['filename'].lower():
                        score += len(self.topPublishers) + 1
                        breakLock = True
                        break
                if breakLock:
                    break
            return score

        if titles is None:
            database = self.getDatabase()
            data = database(id=id, table="anime")
            titles = data.title_synonyms

        print("Searching for titles:", titles)

        torrents = TorrentList(search_engines.search(titles))
        timer = utils.Timer("Torrent search")

        publisher_pattern = re.compile(r'^\[(.*?)\]+')
        keys = (
            (lambda k: max((t['seeds'] for t in k[1])), True),
            (sortkey, True)
        )

        titles = SortedDict(keys=keys)
        while not torrents.empty():
            # timer.start()
            torrent = torrents.get()
            if torrent is None:
                continue
            title = torrent['filename']

            result = publisher_pattern.findall(torrent['filename'])
            if len(result) >= 1:
                publisher = result[0]
            else:
                publisher = None
            if publisher in titles.keys():
                if not torrent['filename'].replace(" ", "") in {e['filename'].replace(" ", "") for e in titles[publisher]}:
                    titles[publisher].append(torrent)
            else:
                titles[publisher] = SortedList(keys=((itemgetter('seeds'), True),))
                titles[publisher].append(torrent)

            if not torrents.is_ready():
                yield titles.items()
            # timer.stop()

        timer.stats()

    # ___Clean up___
    def clearLogs(self):
        for f in os.listdir(self.logsPath):
            path = os.path.join(self.logsPath, f)
            if path != self.logFile:
                os.remove(path)

    def clearCache(self):  # TODO
        if self.cache is None or len(self.cache) == 0:
            self.log("MAIN_STATE", "[ERROR] - Cache path is invalid!")
        cmd = 'del /F /S /Q "{}"'.format(self.cache)
        try:
            subprocess.run(cmd)
            shutil.rmtree(self.cache)
        except BaseException as e:
            self.log("MAIN_STATE", "[ERROR] - Cannot delete cache:", e, "-", cmd)

    def clearDb(self):
        # ONLY FOR TESTING!!! DO NOT USE WITH PROD DB!
        try:
            self.database.close()
        except Exception as e:
            self.log("DB_ERROR", "Database already closed?")
        try:
            os.remove(self.dbPath)
        except PermissionError as e:
            self.log("DB_ERROR", "File is already used", e)
        else:
            shutil.rmtree(self.cache)
            self.database = self.getDatabase()
            self.reloadAll()

    def quit(self):
        self.stopSearch = True
        self.closing = True
        try:
            self.database.close()
        except Exception as e:
            self.log("MAIN_STATE", "[ERROR] - While closing db:", e)
        try:
            self.root.update()
            if self.fen is not None:
                # self.fen.destroy()
                pass
            if self.root is not None:
                self.root.destroy()
            self.root = None
        except Exception as e:
            self.log("MAIN_STATE", "[ERROR] - Can't destroy root:", e)

    # ___Utils___
    def mainloop_error_handler(self, exc, val, tb):
        # if exc == tkinter.TclError and "application has been destroyed" in val:
        #     self.log("MAIN_STATE", "[ERROR] - In tkinter mainloop: Application has been destroyed")
        # else:
        self.log("MAIN_STATE", "[ERROR] - In tkinter mainloop:\n", ''.join(map(lambda t: t.replace('  ', '    '), traceback.format_exception(exc, val, tb))))

    def reloadAll(self):
        self.log('MAIN_STATE', "Reloading")
        self.stopSearch = True
        self.closing = True
        try:
            self.fen.destroy()
        except BaseException:
            pass
        self.fen = None

        self.loadingWindow()

        processes = self.updateAllProgression()
        lenght = next(processes)

        self.start = time.time()
        loadStart = 0
        for i, item in enumerate(processes):
            thread, text = item
            try:
                self.loadLabel['text'] = text
            except BaseException:
                if self.closing or not self.loadfen.winfo_exists():
                    break
            loadStop = (i + 1) / lenght * 100
            while thread.is_alive():
                time.sleep(1 / 60)
                loadStart += (loadStop - loadStart) / max(100 - loadStop, 2)
                try:
                    self.loadProgress['value'] = loadStart
                    self.loadfen.update()
                except BaseException:
                    if self.closing or not self.loadfen.winfo_exists():
                        break

        try:
            self.loadfen.destroy()
            self.quit()
        except BaseException:
            pass
        try:
            self.log('TIME', "Reload time:".ljust(25),
                     round(time.time() - self.start, 2), 'sec')
        except AttributeError:
            pass
        self.__init__()

    def view(self, id):
        index = "indexList"
        # keys = self.database.keys(table="indexList")
        ids = self.database.sql("SELECT * FROM indexList WHERE id=?", (id,), to_dict=True)[0]
        # ids = dict(zip(keys, ids))
        ids.pop("id")
        for api_key, id in ids.items():
            if id is not None and api_key in self.websitesViewUrls.keys():
                url = self.websitesViewUrls[api_key].format(id)
                threading.Thread(target=webbrowser.open, args=(url,)).start()
                # webbrowser.open(url)

    def loading(self, n=0, after=False):
        if self.stopSearch:
            self.loadCanvas.delete(ALL)
            self.timer_id = None
            return
        elif self.timer_id is None or after:
            n = n % len(self.giflist)
            gif = self.giflist[n % len(self.giflist)]
            self.loadCanvas.delete(ALL)
            self.loadCanvas.create_image(
                gif.width() // 2, gif.height() // 2, image=gif)
        if self.timer_id is not None:
            self.fen.after_cancel(self.timer_id)
        self.timer_id = self.fen.after(30, self.loading, n + 1, True)  # TODO - Use a timer instead of n

    # ___Networking___
    def downloadFile(self, id, url=None, file=None):
        def handler(id, put, url=None, file=None):
            isMagnet = False
            if url is not None:
                pattern = re.compile(r"^magnet:\?xt=urn:")
                if pattern.match(url):
                    isMagnet = True
                else:
                    try:
                        # if url.startswith("https://nyaa.si/"):
                        #     url = "https://torproxy.cyou/?cdURL="+url
                        req = None
                        req = requests.get(url, allow_redirects=True)
                        file = urllib.parse.unquote(
                            req.headers['content-disposition'].split('"')[-2])
                    except BaseException:
                        self.log(
                            'NETWORK',
                            "[ERROR] - Error downloading file at url",
                            url,
                            "status_code",
                            req.status_code if req is not None else "unknown")
                        out.put(False)
                        return
                    self.log('NETWORK', "Downloading", file)
                    filePath = os.path.join(self.torrentPath, file)
                    with open(filePath, 'wb') as f:
                        f.write(req.content)
            else:  # File is not None
                filePath = os.path.join(self.torrentPath, file)
            if not isMagnet:
                filePath = os.path.normpath(filePath)

            if self.getQB() == "OK":
                out.put(True)
                path = self.getFolder(id)
                if not os.path.isdir(path):
                    try:
                        os.mkdir(path)
                    except FileExistsError:
                        pass
                if isMagnet:
                    args = {'urls': url}
                else:
                    args = {'torrent_files': open(filePath, 'rb')}
                try:
                    self.qb.torrents_add(**args, save_path=path)
                except qbittorrentapi.exceptions.APIConnectionError:
                    self.log(
                        'NETWORK', "[ERROR] - Couldn't find the torrent client!")
                else:
                    if isMagnet:
                        torrenthash = self.getMagnetHash(url)
                    else:
                        torrenthash = self.getTorrentHash(filePath)
                    qb_path = os.path.join(self.qbCache, str(torrenthash) + ".torrent")

                    if isMagnet:
                        file = str(torrenthash) + ".torrent"
                        qb_path = os.path.join(self.qbCache, torrenthash)
                        filePath = os.path.join(self.torrentPath, file)
                        shutil.copyfile(qb_path, filePath)

                    while not os.path.exists(qb_path):
                        time.sleep(1)
                        print("Waiting for torrent:", qb_path)
                    self.qb.torrents_set_location(
                        location=path, torrent_hashes=[torrenthash])
            else:
                out.put(False)
                self.log(
                    'NETWORK', "[ERROR] - Couldn't find the torrent client!")

            database = self.getDatabase()
            with database.get_lock():
                torrents = database.get_metadata(id, "torrents")
                database.save_metadata(id, {"torrents": torrents + [file]})

                if database(id=id, table='anime')['tag'] != 'WATCHING':
                    database.set({'id': id, 'tag': 'WATCHING'}, table='anime')
                database.save()

            self.root.after(10, self.optionsWindow(id))

        assert url is not None or file is not None, "You need to specify either an url or a file path"
        out = queue.Queue()
        threading.Thread(target=handler, args=(id, out, url, file), daemon=True).start()
        return out

    def redownload(self, id):
        if self.getQB() == "OK":
            database = self.getDatabase()

            torrents = database.get_metadata(id, "torrents")

            for torrent in torrents:
                self.downloadFile(id, file=torrent)
            if len(torrents) > 0:
                self.log(
                    'NETWORK',
                    'Redownloaded {} torrents'.format(
                        len(torrents)))
            else:
                self.log(
                    'NETWORK',
                    'No torrents to download!'.format(
                        len(torrents)))

        else:
            self.log('NETWORK', "[ERROR] - Couldn't find the torrent client!")

    def bluetoothConnect(self):
        pass
        # TODO -> En fait c'est chiant

    # ___Data update___
    def getSeason(self, year, season):
        def handler(year, season):
            for i, a in enumerate():
                self.season_ids.append(a)
            self.season_ids.append("STOP")

        def iter():
            data = None
            while True:
                if len(self.season_ids) > 0:
                    data = self.season_ids.pop()
                    if data == "STOP":
                        break
                    yield data
                else:
                    time.sleep(1 / 60)
                    try:
                        self.root.update()
                    except BaseException:
                        break
        # threading.Thread(target=handler, args=(year, season), daemon=True).start()

        self.animeList.set(self.api.season(year, season))

    def getCharactersData(self, id):
        database = self.getDatabase()

        self.log('NETWORK_DATA', "Requesting characters data for id", id)

        data = self.api.animeCharacters(id)

        def cb(character):
            sql = "SELECT EXISTS(SELECT 1 FROM characters WHERE id = ? AND anime_id = ?);"
            exists = bool(database.sql(
                sql, (character['id'], character['anime_id']))[0][0])
            if not exists:
                self.log("CHARACTER", "New character, anime id", id,
                         "id", character['id'], "name", character['name'])
                sql = "INSERT INTO characters(" + ",".join(["{}"] * len(character.keys())) + ") VALUES (" + ",".join("?" * len(character.keys())) + ");"
                sql = sql.format(*character.keys())
                try:
                    database.sql(sql, character.values())
                except Exception as e:
                    raise e
            database.save()

        data.add_callback(cb)

        return data

    def getCharacterData(self, id):
        database = self.getDatabase()

        self.log("NETWORK", "Requesting data for character id", id)

        character = self.api.character(id)

        sql = "SELECT role FROM characters WHERE id = ? AND role IS NOT NULL;"
        roleData = database.sql(sql, (character['id'],))
        if len(roleData) >= 1:
            character['role'] = roleData[0][0]

        if 'animeography' in character.keys():
            animes = character.pop('animeography')
            self.log("CHARACTER", "Adding character with id", id,
                     "name", character['name'], "to", len(animes), "animes.")
            # for anime in animes: TODO
            #     character['anime_id'] = database.getId(api_key,anime['mal_id'])
            #     sql = "SELECT EXISTS(SELECT 1 FROM characters WHERE id = ? AND anime_id = ?);"
            #     values = list(character.values())
            #     if bool(database.sql(sql,(character['id'],character['anime_id']))[0][0]):
            #         sql = "UPDATE characters SET " + "{} = ?,"*(len(character)-1) + "{} = ? WHERE id = ? AND anime_id = ?;"
            #         sql = sql.format(*character.keys())
            #         values += [character['id'],character['anime_id']]
            #     else:
            #         sql = "INSERT INTO characters(" + "{},"*(len(character)-1) + "{}) VALUES(" + "?,"*(len(character)-1)+"?);"
            #         sql = sql.format(*character.keys())
            #     try:
            #         database.sql(sql,values,save=True)
            #     except Exception:
            #         raise

        return character


if __name__ == '__main__':
    multiprocessing.freeze_support()
    p = multiprocessing.current_process()
    if p.name == 'MainProcess':
        m = Manager()
