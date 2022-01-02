import auto_launch

import ctypes
import io
import json
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
from datetime import datetime, timedelta
from operator import itemgetter
from tkinter import *

try:
    import bencoding
    from bs4 import BeautifulSoup
    from lxml import etree
    from PIL import Image, ImageTk
    import qbittorrentapi.exceptions
    import requests

    import sys
    if getattr(sys, 'frozen', None):
        basedir = sys._MEIPASS
        os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(basedir, 'certifi', 'cacert.pem')  # Required for requests and certifi
except ModuleNotFoundError as e:
    print("Installing modules!", e)
    subprocess.run("pip install qbittorrent-api lxml jikanpy jsonapi_client requests Pillow python-mpv pytube bencoding bs4")
    time.sleep(20)
    import sys
    # os.execv(sys.argv[0], sys.argv)
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
    from anime_search import AnimeSearch
    from media_players import MediaPlayers
    from dbManager import db
    from classes import Anime, Character, AnimeList, TorrentList, SortedList, SortedDict
except ModuleNotFoundError as e:
    print(e)
    print("Please verify your app installation!")
    import sys
    sys.exit()


# TODO - Add filter for torrent list (seeds / name)
# TODO - Add scrolling bar on ScrollableFrame
# TODO - Implement dropdowns (Episode list)
# TODO - Handle huge seasons / Add an episode window?
# TODO - Allow window resizing
# TODO - Online search raise database is locked error
# TODO - Some image aren't loading with online search (sk8)
# TODO - jikanpy.exceptions.APIException: HTTP 500 - status=500, type=ParserException, message=Unable to parse this request. Please follow report_url to generate an issue on GitHub, error=Failed to parse 'https://myanimelist.net/...'
# TODO - Avoid accessing to db with the API wrappers
# TODO - Figure out how to update anime list when tag change
# TODO - Torrent publisher list freeze when internet is slow
# TODO - Add an option to modify the torrent search
# TODO - Improve torrent matching algorithm
# TODO - Auto associate latest torrents?
# TODO - Add python-based torrent client
# TODO - Characters don't have the 'anime_id' key
# TODO - Image thread starting multiple times
# TODO - Add RSS option
# TODO - Automatic torrent downloading from RSS?
# TODO - Compile into an executable
# TODO - Phone version


class Manager(Constants, Logger, UpdateUtils, Getters, AnimeSearch, MediaPlayers, *windows.windows):
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
        self.animeListReady = False
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

        self.database = self.getDatabase()
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
        if force_search:
            self.stopSearch = False
            self.animeListReady = True
            self.root.update()
            self.animeList = self.searchAnime(terms)
            self.loading()
            self.createList(None)
        elif len(terms) > 2:
            animeList = self.searchDb(terms)
            if animeList is not False:
                self.animeListReady = True
                self.root.update()
                self.animeList = animeList
                self.createList(None)
            else:
                self.stopSearch = False
                self.animeList = self.searchAnime(terms)
                self.loading()
                self.animeListReady = True
                self.root.update()
                self.createList(None)
        elif self.animeList is not None:
            self.stopSearch = True
            self.animeListReady = True
            self.root.update()
            self.animeList = None
            self.createList()

        if self.root is None:
            return
        self.fen.update()

    def searchDb(self, terms):
        def enumerator(terms):
            sql = "SELECT anime.*,tag.tag,like.like FROM searchTitles JOIN anime using(id) LEFT JOIN tag using(id) LEFT JOIN like using(id) WHERE searchTitles.title LIKE '%{}%' GROUP BY anime.id ORDER BY anime.date_from DESC;".format(
                terms)
            keys = list(self.database.keys(table="anime")) + ['tag', 'like']
            anime_list = AnimeList(Anime(keys=keys, values=data) for data in self.database.sql(sql, iterate=True))
            return anime_list

        self.updateTitles()  # TODO
        terms = "".join([c for c in terms if c.isalnum()]).lower()
        if bool(
            self.database.sql(
                "SELECT EXISTS(SELECT 1 FROM searchTitles WHERE searchTitles.title LIKE '%{}%');".format(terms))[0][0]):
            return enumerator(terms)
        else:
            return False

    def searchTorrents(self, id):
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

        database = self.getDatabase()
        data = database(id=id, table="anime")
        titles = json.loads(data['title_synonyms'])
        titles.append(data['title'])
        publisher_pattern = re.compile(r'^\[(.*?)\]+')

        data = []
        torrents = TorrentList(search_engines.search(titles))
        timer = utils.Timer("Torrent search")

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

    # ___Main List generation___
    def createList(self, criteria="DEFAULT", listrange=None, add_to_end=False):
        def wait_for_next(animelist, default):
            if isinstance(animelist, AnimeList):
                empty_test = "not animelist.is_ready()"
            else:
                que = queue.Queue()
                t = threading.Thread(
                    target=lambda que, animelist, default: que.put(
                        next(animelist, default)),
                    args=(que, animelist, default), daemon=True)
                t.start()
                animelist = que
                empty_test = "que.empty()"
            while eval(empty_test):
                try:
                    self.root.update()
                except AttributeError:
                    pass
                if self.closing:
                    return None
                time.sleep(0.01)
            data = animelist.get()
            return data

        if criteria == "DEFAULT" or self.animeList is None:
            if criteria == "DEFAULT":
                filter = "anime.status != 'UPCOMING'"
                if self.hideRated:
                    filter += " AND (rating NOT IN('R+','Rx') OR rating IS null)"
                sort = "DESC"
                order = "anime.date_from"
            else:
                # \nAND rating NOT IN('R+','Rx')"
                commonFilter = "\nAND anime.id NOT IN(SELECT anime.id FROM anime WHERE status = 'UPCOMING')"
                order = "anime.date_from"
                sort = "DESC"
                if self.hideRated:
                    commonFilter += " \nAND (rating NOT IN('R+','Rx') OR rating IS null)"

                if criteria == 'LIKED':
                    filter = "like.like = 1" + commonFilter

                elif criteria == 'NONE':
                    filter = "tag.tag = 'NONE' OR anime.id NOT IN(SELECT id FROM tag)" + commonFilter

                elif criteria in ['UPCOMING', 'FINISHED', 'AIRING']:
                    if criteria == 'UPCOMING':
                        commonFilter = "\nAND (rating NOT IN('R+','Rx') OR rating IS null)" if self.hideRated else ""
                    if criteria == "UPCOMING":
                        sort = "ASC"
                    filter = "status = '{}'".format(criteria) + commonFilter

                elif criteria == 'RATED':
                    filter = "rating IN('R+','Rx')\nAND anime.id NOT IN(SELECT anime.id FROM anime WHERE status = 'UPCOMING')"

                elif criteria == "RANDOM":
                    order = "RANDOM()"
                    filter = "anime.picture is not null"

                elif criteria == "SEASON":
                    return self.seasonSelector()
                else:
                    if criteria == 'WATCHING':
                        commonFilter = "\nAND anime.id NOT IN(SELECT anime.id FROM anime WHERE status = 'UPCOMING')"
                        order = """
                            CASE WHEN anime.status = "AIRING" AND broadcast IS NOT NULL
                            THEN (({}-SUBSTR(broadcast,1,1)+6)%7*24*60
                                +({}-SUBSTR(broadcast,3,2))*60
                                +({}-SUBSTR(broadcast,6,2))
                            +86400)%86400 ELSE "9" END ASC,
                            date_from
                        """
                        sort_date = datetime.today() - timedelta(hours=5)
                        order = order.format(
                            sort_date.weekday(), sort_date.hour, sort_date.minute)
                        # Depend on timezone - TODO
                    filter = "tag.tag = '{}'".format(criteria) + commonFilter

            self.animeList = self.database.filter(
                sort=sort,
                range=listrange,
                order=order,
                filter=filter)

        self.animeListReady = True  # Interrupt previous list generation
        self.root.update()

        if listrange is None:
            listrange = (0, 50)
            if not add_to_end:
                self.scrollable_frame.canvas.yview_moveto(0)

        if not add_to_end:
            for child in self.scrollable_frame.winfo_children():
                child.destroy()

        # Ensure the Load More button is on the last column
        listrange = (
            listrange[0],
            listrange[1] // self.animePerRow * self.animePerRow - 1)

        que = queue.Queue()
        self.getElemImages(que)

        self.animeListReady = False
        self.list_timer = utils.Timer("list")
        for i in range(listrange[0], listrange[1]):
            try:
                data = wait_for_next(self.animeList, None)
            except TypeError:
                if isinstance(self.animeList, None):
                    self.animeList = []
                    break
            else:
                if self.animeListReady or self.closing:
                    que.put("STOP")
                    return
                if data is None:
                    if i == listrange[0]:
                        self.log("MAIN_STATE", "No results!")
                        Label(
                            self.scrollable_frame,
                            text="No results",
                            font=(
                                "Source Code Pro Medium",
                                20),
                            bg=self.colors['Gray2'],
                            fg=self.colors['Gray4'],
                        ).grid(
                            columnspan=self.animePerRow,
                            row=0,
                            pady=50)
                        print("NO RESULTS")
                    break
                self.createElem(i, data, que)

            if i % self.animePerRow == 0:
                if self.root is None:
                    que.put("STOP")
                    return
                self.fen.update()

        # self.list_timer.stats()
        que.put("STOP")

        try:
            e, self.animeList = utils.peek(self.animeList)
        except TypeError:
            pass
        else:
            if e is not None:
                self.loadMoreButton(i + 1, listrange, criteria)

        self.scrollable_frame.update()
        try:
            self.fen.update()
        except BaseException:
            pass

    def createElem(self, index, anime, queue):
        if self.root is None:
            return
        self.list_timer.start()
        if self.blank_image is None:
            self.blank_image = self.getImage(None, (225, 310))
        title = anime.title
        if title is None:
            self.list_timer.stop()
            return
        if len(title) > 35:
            title = title[:35] + "..."

        img_can = Canvas(self.scrollable_frame, width=225, height=310, highlightthickness=0, bg=self.colors['Gray3'])
        img_can.bind("<Button-1>", lambda e,
                     id=anime.id: self.optionsWindow(id))
        img_can.bind("<Button-3>", lambda e, id=anime.id: self.view(id))
        img_can.grid(column=index % self.animePerRow,
                     row=index // self.animePerRow * 2)

        img_can.create_image(0, 0, image=self.blank_image, anchor='nw')
        img_can.image = self.blank_image

        data = self.database(id=anime.id, table='tag')
        if 'tag' in anime:
            tag = anime.tag
            if tag is None:
                tag = "NONE"
        else:
            tag = data['tag']
        if 'like' in anime:
            like = anime.like
        else:
            like = data['like']
        if like == 1:
            title += " ❤"
        lbl = Label(self.scrollable_frame,
                    text=title,
                    bg=self.colors['Gray2'],
                    fg=self.colors[self.tagcolors[tag]],
                    font=("Source Code Pro Medium", 13),
                    bd=0,
                    wraplength=220)
        lbl.grid(column=index % self.animePerRow,
                 row=(index // self.animePerRow * 2) + 1)
        lbl.name = str(anime.id)

        self.scrollable_frame.update()

        filename = os.path.join(self.cache, str(anime.id) + ".jpg")
        url = anime.picture
        queue.put((filename, url, img_can))
        self.list_timer.stop()

    def loadMoreButton(self, index, listrange, filter):
        img_can = Canvas(self.scrollable_frame, width=225, height=310, highlightthickness=0, bg=self.colors['Gray2'])
        img_can.grid(column=index % self.animePerRow,
                     row=index // self.animePerRow * 2)
        img_can.bind("<Button-1>", lambda e, a=listrange,
                     b=filter: self.loadMore(a, b))

        size = 75
        x, y = int(225 / 2 - size / 2), int(310 / 2 - size / 2)
        pos = (x, y + size / 2, x + size, y + size / 2, x + size / 2,
               y + size / 2, x + size / 2, y, x + size / 2, y + size)
        img_can.create_line(*pos, capstyle='round',
                            fill=self.colors['Gray4'], width=15)

        lbl = Label(self.scrollable_frame, text="Load more...",
                    bg=self.colors['Gray2'], fg=self.colors['Gray4'], font=(
                        "Source Code Pro Medium", 13),
                    bd=0, wraplength=220)
        lbl.grid(column=index % self.animePerRow,
                 row=(index // self.animePerRow * 2) + 1)
        lbl.name = str(-1)

    def loadMore(self, listrange, filter):
        listrange = (listrange[1], (listrange[1] + (listrange[1] - listrange[0])) // self.animePerRow * self.animePerRow - 1)
        # posy = self.scrollable_frame.canvas.canvasy(0)
        self.animeList = None
        self.createList(filter, listrange, add_to_end=True)
        # self.scrollable_frame.canvas.yview_moveto(posy / self.scrollable_frame.canvas.bbox('all')[3])
        return

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
                if not self.loadfen.winfo_exists():
                    break
            loadStop = (i + 1) / lenght * 100
            while thread.is_alive():
                time.sleep(1 / 60)
                loadStart += (loadStop - loadStart) / max(100 - loadStop, 2)
                try:
                    self.loadProgress['value'] = loadStart
                    self.loadfen.update()
                except BaseException:
                    if not self.loadfen.winfo_exists():
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
        # del self
        # Manager()

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

    # ___Misc___
    def downloadFile(self, id, url=None, file=None):
        def handler(id, url=None, file=None):
            database = self.getDatabase()
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
                        return
                    self.log('NETWORK', "Downloading", file)
                    filePath = os.path.join(self.torrentPath, file)
                    with open(filePath, 'wb') as f:
                        f.write(req.content)
            else:
                filePath = os.path.join(self.torrentPath, file)
            if not isMagnet:
                filePath = os.path.normpath(filePath)

            if self.getQB() == "OK":
                path = self.getFolder(id)
                if not os.path.isdir(path):
                    try:
                        os.mkdir(path)
                    except FileExistsError:
                        pass
                if isMagnet:
                    torrent_url = url
                else:
                    torrent_url = open(filePath, 'rb')
                try:
                    self.qb.torrents_add(
                        torrent_files=torrent_url, save_path=path)  # urls=url
                except qbittorrentapi.exceptions.APIConnectionError:
                    self.log(
                        'NETWORK', "[ERROR] - Couldn't find the torrent client!")
                else:

                    torrenthash = self.getTorrentHash(filePath)
                    self.qb.torrents_set_location(
                        location=path, torrent_hashes=[torrenthash])
            else:
                self.log(
                    'NETWORK', "[ERROR] - Couldn't find the torrent client!")

            torrents = database.sql(
                "SELECT torrent FROM anime WHERE id = ?", (id,))[0][0]
            torrents = json.loads(torrents) if torrents is not None else []
            torrents.append(file)
            torrents = list(set(torrents))
            database.set(
                {'id': id, 'torrent': json.dumps(torrents)},
                table="anime")

            if database(id=id, table='tag')['tag'] != 'WATCHING':
                database.set({'id': id, 'tag': 'WATCHING'}, table='tag')

        assert url is not None or file is not None, "You need to specify either an url or a file path"
        threading.Thread(target=handler, args=(id, url, file), daemon=True).start()

    def redownload(self, id):
        if self.getQB() == "OK":
            database = self.getDatabase()

            torrents = database.sql(
                "SELECT torrent FROM anime WHERE id = ?", (id,))[0][0]
            torrents = json.loads(torrents) if torrents is not None else []

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

        self.animeList = self.api.season(year, season)
        print(self.animeList)
        self.animeListReady = True
        self.root.update()
        self.createList(None, (0, 1000))

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
    m = Manager()
