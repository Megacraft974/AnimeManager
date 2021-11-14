import json
import os
import io
import time
import ctypes
import threading
import urllib
import re
import shutil
import queue
import traceback
import socket
import webbrowser
from operator import itemgetter
from datetime import datetime, timedelta
from tkinter import *

try:
    from PIL import Image, ImageTk
    import qbittorrentapi.exceptions
    import lxml.etree
    import requests
    import bencoding

except ModuleNotFoundError as e:
    print("Installing modules!", e)
    import sys
    os.system("pip install qbittorrent-api lxml jikanpy jsonapi_client requests Pillow python-mpv pytube bencoding")
    print(sys.argv)
    os.system(" ".join(["python"] + sys.argv))
    sys.exit()

try:
    import utils
    import search_engines
    import animeAPI
    import windows

    from update_utils import UpdateUtils
    from getters import Getters
    from logger import Logger
    from anime_search import AnimeSearch
    from dbManager import db
    from classes import Anime, Character, AnimeList, CharacterList
except ModuleNotFoundError as e:
    print(e)
    print("Please verify your app installation!")
    import sys
    sys.exit()


class Manager(UpdateUtils, Getters, Logger, AnimeSearch, *windows.windows):
    def __init__(self, remote=False):
        self.start = time.time()

        self.logs = ['DB_ERROR', 'DB_UPDATE', 'MAIN_STATE',
                     'NETWORK', 'SERVER', 'SETTINGS', 'TIME']

        appid = 'megacraft.anime.manager.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
        # 181915 - 282923 - 373734 - F8F8C4 - 98E22B(G) - E79622(O)

        cwd = os.path.dirname(os.path.abspath(__file__))  # TODO - Constants files / get settings?
        self.iconPath = os.path.join(cwd, "icons")

        appdata = os.path.join(os.getenv('APPDATA'), "AnimeManager")
        self.dbPath = os.path.join(appdata, "animeData.db")
        self.settingsPath = os.path.join(appdata, "settings.json")
        self.cache = os.path.join(appdata, "cache")
        self.logsPath = os.path.join(appdata, "logs")
        if not os.path.exists(appdata):
            os.mkdir(appdata)

        filesData = os.path.expanduser('~\\Documents\\AnimeManager')
        if not os.path.exists(filesData):
            os.mkdir(filesData)
        self.animePath = os.path.join(filesData, "Animes")
        self.torrentPath = os.path.join(filesData, "Torrents")

        self.hideRated = True
        self.enableServer = True

        self.remote = remote
        self.animeFolder = []
        self.searchQueue = []
        self.relationIds = []
        self.characterIds = []
        self.timer_id = None
        self.lastSearch = None
        self.searchThread = None
        self.stopSearch = False
        self.maxLogsSize = 50000  # In bytes
        self.animeListReady = False
        self.blank_image = None
        self.qb = None
        self.root = None
        self.fen = None
        self.choice = None
        self.publisherChooser = None
        self.fileChooser = None
        self.loadfen = None
        self.characterList = None
        self.characterInfo = None
        self.settings = None
        self.diskfen = None
        self.server = None

        self.hostName = "0.0.0.0"
        self.serverPort = 8081

        self.qb = None
        self.torrentApiAddress = 'http://' + \
            str(socket.gethostbyname(socket.gethostname())) + ":8080"
        self.torrentApiLogin = 'admin'
        self.torrentApiPassword = '123456'

        if True:
            self.allLogs = [
                'CHARACTER',
                'CONFIG',
                'DB_ERROR',
                'DB_UPDATE',
                'DISK_ERROR',
                'FILE_SEARCH',
                'MAIN_STATE',
                'NETWORK',
                'NETWORK_DATA',
                'PICTURE',
                'RELATED',
                'SCHEDULE',
                'SERVER',
                'SETTINGS',
                'THREAD',
                'TIME']
            self.pathSettings = ["animePath", "torrentPath",
                                 "iconPath", "cache", "dbPath", "logsPath"]
            self.websitesViewUrls = {
                "mal_id": "https://myanimeList.net/anime/{}",
                "kitsu_id": "https://kitsu.io/anime/{}",
                "anilist_id": "https://anilist.co/anime/{}",
                "anidb_id": "https://anidb.net/anime/{}"}
            self.seasons = {'winter': {'start': 1, 'end': 3},
                            'spring': {'start': 4, 'end': 6},
                            'summer': {'start': 7, 'end': 9},
                            'fall': {'start': 10, 'end': 12}}
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
                {'text': 'Delete files', 'color': 'Red', 'command': self.deleteFiles},
                {'text': 'Remove from db', 'color': 'Red', 'command': self.delete},)
            self.filterOptions = {'Liked': {'color': 'Red', 'filter': 'LIKED'},
                                  'Seen': {'color': 'Green', 'filter': 'SEEN'},
                                  'Watching': {'color': 'Orange', 'filter': 'WATCHING'},
                                  'Watchlist': {'color': 'Blue', 'filter': 'WATCHLIST'},
                                  'Finished': {'color': 'Green', 'filter': 'FINISHED'},
                                  'Airing': {'color': 'Orange', 'filter': 'AIRING'},
                                  'Upcoming': {'color': 'Blue', 'filter': 'UPCOMING'},
                                  'Rated': {'color': 'Red', 'filter': 'RATED'},
                                  'By season': {'color': 'Blue', 'filter': 'SEASON'},
                                  'Random': {'color': 'Green', 'filter': 'RANDOM'},
                                  'No tags': {'color': 'White', 'filter': 'NONE'},
                                  'No filter': {'color': 'Gray', 'filter': 'DEFAULT'}}
            self.status = {
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


        self.database = self.getDatabase()
        if not os.path.exists(self.dbPath):
            self.checkSettings()
            self.reloadAll()
            return
        else:
            self.checkSettings()

        self.api = animeAPI.AnimeAPI('all', self.dbPath)
        self.getQB()
        self.imQueue = queue.Queue()

        if not self.remote:
            try:
                self.initWindow()

                self.log('MAIN_STATE', "Stopping")
                self.start = time.time()
                self.updateAll()
                self.log('TIME', "Stopping time:".ljust(25),
                         round(time.time() - self.start, 2), 'sec')
            except Exception as e:
                self.log("MAIN_STATE", "[ROOT]:\n", traceback.format_exc())

    # ___Search___
    def search(self, *args, force_search=False):
        terms = None
        loop = True
        while terms != self.searchTerms.get() and loop:
            terms = self.searchTerms.get()
            if force_search:
                self.stopSearch = False
                self.animeList = self.searchAnime(terms)
                self.loading()
                self.createList(None)
            elif len(terms) > 2:
                animeList = self.searchDb(terms)
                if animeList is not False:
                    self.animeList = animeList
                    self.createList(None)
                else:
                    self.stopSearch = False
                    self.animeList = self.searchAnime(terms)
                    self.loading()
                    self.createList(None)
                    # TODO - Show when there are no results
                    # Label(
                    #     self.scrollable_frame,
                    #     text="No results",
                    #     font=(
                    #         "Source Code Pro Medium",
                    #         20),
                    #     bg=self.colors['Gray2'],
                    #     fg=self.colors['Gray4'],
                    # ).grid(
                    #     columnspan=4,
                    #     row=0,
                    #     pady=50)
            elif self.animeList is not None:
                self.stopSearch = True
                self.animeList = None
                self.animeListReady = True
                self.createList()
            self.fen.update()

    def searchDb(self, terms):
        def enumerator(terms):
            sql = "SELECT anime.* FROM searchTitles JOIN anime on searchTitles.id = anime.id WHERE searchTitles.title LIKE '%{}%' GROUP BY anime.id ORDER BY anime.date_from DESC;".format(
                terms)
            keys = self.database(table="anime").keys()
            for data in self.database.sql(sql):
                data = Anime(dict(zip(keys, data)))
                yield data

        self.updateTitles()
        terms = "".join([c for c in terms if c.isalnum()]).lower()
        if bool(
            self.database.sql(
                "SELECT EXISTS(SELECT 1 FROM searchTitles WHERE searchTitles.title LIKE '%{}%');".format(terms))[0][0]):
            return enumerator(terms)
        else:
            return False

    def searchTorrents(self, id):
        def handler(titles, que):
            for a in search_engines.search(titles):
                que.put(a)

        database = self.getDatabase()
        titles = json.loads(database(id=id, table="anime")['title_synonyms'])
        titles.append(database(id=id, table="anime")['title'])
        pattern = re.compile(r'^\[(.*?)\]+')

        que = queue.Queue()
        data = []
        thread = threading.Thread(target=handler, args=(titles, que))
        timer = utils.Timer("Torrent search")
        thread.start()

        titles = {}
        while thread.is_alive() or not que.empty():
            if que.empty():
                self.root.update()
                time.sleep(1 / 60)
                continue

            a = que.get()
            title = a['filename']
            if title.rsplit(".", 1)[0] in {
                    d['filename'].rsplit(".", 1)[0] for d in data}:
                continue

            result = pattern.findall(a['filename'])
            if len(result) >= 1:
                publisher = result[0]
            else:
                publisher = None
            if publisher in titles.keys():
                if not a['filename'] in (e['filename']
                                         for e in titles[publisher]):
                    titles[publisher].append(a)
            else:
                titles[publisher] = [a]

        timer.stats()

        for publisher, titlelist in titles.items():
            titles[publisher] = sorted(
                titlelist, key=itemgetter('seeds'), reverse=True)

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

        titles = sorted(titles.items(), key=lambda k: max(
            (t['seeds'] for t in k[1])), reverse=True)
        titles = sorted(titles, key=sortkey, reverse=True)

        for p, d in titles:
            obj = []
            for t in d:
                # obj.append({'title':t['name'],'size':t['size'],'link':['link'],'seeds':['seeds']})
                obj.append(t)
            yield p, obj

    def regroupFiles(self):
        self.log("DB_UPDATE", "Regrouping files")
        database = self.getDatabase()

        files = []
        for file in os.listdir(self.animePath):
            if os.path.isfile(os.path.join(self.animePath, file)):
                files.append(file)

        if self.getQB() == "OK":
            torrents = self.qb.torrents_info()
        else:
            torrents = []

        if not os.path.isdir(self.torrentPath):
            self.log("DISK_ERROR", "Torrent folder doesn't exists!")
            return

        keys = ('id', 'title', 'torrent')
        torrentDb = database.sql(
            'SELECT id,title,torrent FROM anime WHERE torrent is not null',
            iterate=True)
        torrentData = (dict(zip(keys, d)) for d in torrentDb)
        c = 0

        for data in torrentData:
            anime = Anime(data)
            path = self.getFolder(anime=anime)
            if os.path.isdir(path):
                hashes = []
                for t in json.loads(anime.torrent):
                    filePath = os.path.join(self.torrentPath, t)
                    if os.path.isfile(filePath):
                        torrent_hash = self.getTorrentHash(filePath)
                        hashes.append(torrent_hash)
                if self.getQB() == "OK":
                    self.qb.torrents_set_location(
                        location=path, torrent_hashes=hashes)

        self.log("DB_UPDATE", "Files regrouped!")

    # ___Main List generation___
    def createList(self, criteria="DEFAULT", listrange=(0, 50)):
        def enumerator(ids):
            ids = list(ids)
            for id in ids:
                yield self.database(id=id[0], table="anime").get()

        def wait_for_next(animelist, default):
            que = queue.Queue()
            if type(animelist) == AnimeList:
                t = threading.Thread(
                    target=lambda que, animelist, default:
                        que.put(animelist.get(timeout=30, default=None)),
                    args=(que, animelist, default))
            else:
                t = threading.Thread(
                    target=lambda que, animelist, default: que.put(
                        next(
                            animelist, default)), args=(
                        que, animelist, default))
            t.start()
            while que.empty():
                try:
                    self.root.update()
                except AttributeError:
                    pass
                time.sleep(0.01)
            data = que.get()
            return data

        if criteria == "DEFAULT" or self.animeList is None:
            print(criteria, self.animeList)
            if criteria == "DEFAULT":
                table = "anime"
                filter = "anime.status != 'UPCOMING'"
                if self.hideRated:
                    filter += " AND (rating NOT IN('R+','Rx') OR rating IS null)"
                sort = "DESC"
                order = "anime.date_from"
            else:
                # \nAND rating NOT IN('R+','Rx')"
                table = 'anime'
                commonFilter = "\nAND anime.id NOT IN(SELECT anime.id FROM anime WHERE status = 'UPCOMING')"
                order = "anime.date_from"
                sort = "DESC"
                if self.hideRated:
                    commonFilter += " \nAND (rating NOT IN('R+','Rx') OR rating IS null)"

                if criteria == 'LIKED':
                    table = 'like'
                    filter = "like.like = 1" + commonFilter

                elif criteria == 'NONE':
                    table = 'tag'
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
                            sort_date.day, sort_date.hour, sort_date.minute)
                        # Depend on timezone - TODO
                    table = 'tag'
                    filter = "tag.tag = '{}'".format(criteria) + commonFilter

            ids = self.database.allkeys(
                table=table,
                sort=sort,
                range=listrange,
                order=order,
                filter=filter)

            self.animeList = enumerator(ids)

        self.animeListReady = True  # Interrupt previous list generation
        self.root.update()

        if listrange == (0, 50):
            self.scrollable_frame.canvas.yview_moveto(0)
        for child in self.scrollable_frame.winfo_children():
            child.destroy()

        # Ensure the Load More button is on the last column
        listrange = (
            listrange[0],
            listrange[1] // self.animePerRow * self.animePerRow - 1)

        que = queue.Queue()
        threading.Thread(target=self.getImgThread, args=(que,)).start()
        self.getElemImages()

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
                if self.animeListReady:
                    return
                if data is None:
                    break
                self.createElem(i, data, que)

            if i % self.animePerRow == 0:
                self.fen.update()

        self.list_timer.stats()
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
        self.list_timer.start()
        if self.blank_image is None:
            self.blank_image = self.getImage(None, (225, 310))
        # im = Image.new('RGB', (225, 310), self.colors['Gray'])
        # image = ImageTk.PhotoImage(im)  # TODO - Use getImage instead

        img_can = Canvas(self.scrollable_frame, width=225, height=310, highlightthickness=0, bg=self.colors['Gray3'])
        img_can.bind("<Button-1>", lambda e,
                     id=anime.id: self.optionsWindow(id))
        img_can.bind("<Button-3>", lambda e, id=anime.id: self.view(id))
        img_can.grid(column=index % self.animePerRow,
                     row=index // self.animePerRow * 2)

        img_can.create_image(0, 0, image=self.blank_image, anchor='nw')
        img_can.image = self.blank_image

        title = anime.title
        if len(title) > 35:
            title = title[:35] + "..."

        if self.database(id=anime.id, table='like').exist() and bool(
                self.database(id=anime.id, table='like')['like']):
            title += " ❤"
        lbl = Label(self.scrollable_frame,
                    text=title,
                    bg=self.colors['Gray2'],
                    fg=self.colors[self.tagcolors[self.database(id=anime.id,
                                                                table='tag')['tag']]],
                    font=("Source Code Pro Medium", 13),
                    bd=0,
                    wraplength=220)
        lbl.grid(column=index % self.animePerRow,
                 row=(index // self.animePerRow * 2) + 1)
        lbl.name = str(anime.id)

        self.scrollable_frame.update()

        queue.put((anime, img_can))
        self.list_timer.stop()

    def getElemImages(self):
        while not self.imQueue.empty():
            data = self.imQueue.get()
            if data != "STOP":
                im, can = data
                try:
                    image = ImageTk.PhotoImage(im)  # TODO - Use getImage instead
                    can.create_image(0, 0, image=image, anchor='nw')
                    can.image = image
                except BaseException:
                    pass
            else:
                self.log("THREAD", "All images loaded")
                return
        if self.root is not None:
            self.root.after(100, self.getElemImages)

    def getImgThread(self, que):
        def usePlaceholder(can):
            im = Image.open(os.path.join(self.iconPath, "placeholder.png"))
            im = im.resize((225, 310))
            self.imQueue.put((im, can))
        self.log("THREAD", "Started image thread")
        no_internet = False
        args = que.get()
        while args != "STOP":
            anime, can = args
            if no_internet:
                usePlaceholder(can)
                args = que.get()
                continue
            filename = os.path.join(self.cache, str(anime.id) + ".jpg")

            if str(anime.id) + ".jpg" in os.listdir(self.cache):
                try:
                    im = Image.open(filename)
                    self.imQueue.put((im, can))
                    args = que.get()
                    continue
                except BaseException:
                    self.log(
                        'DISK_ERROR',
                        "[ERROR] Image file is corrupted, deleting, anime",
                        anime.title,
                        "id",
                        anime.id,
                        "file",
                        filename)
                    os.remove(filename)

            self.log("PICTURE", "Requesting picture for anime id",
                     anime.id, "title", anime.title)
            if anime.picture is not None:
                try:
                    req = requests.get(anime.picture)
                except requests.exceptions.ReadTimeout as e:
                    self.log("PICTURE", "Timed out!")
                    usePlaceholder(can)
                except requests.exceptions.ConnectionError as e:
                    self.log('PICTURE', "[ERROR] - No internet connection!")
                    usePlaceholder(can)
                    no_internet = True
                except requests.exceptions.MissingSchema as e:
                    self.log("PICTURE", "[ERROR] - Invalid url!", anime.picture)
                    usePlaceholder(can)
                else:
                    if req.status_code == 200:
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
                        self.imQueue.put((im, can))
                    else:
                        self.log(
                            "PICTURE",
                            "[ERROR] Status code",
                            req.status_code,
                            "for anime",
                            anime.title,
                            "requesting new picture.")
                        repdata = self.api.animePictures(anime.id)

                        if len(repdata) >= 1:
                            args = list(args)
                            args[2]['picture'] = repdata[-1]['small']
                            database = self.getDatabase()
                            database.sql("UPDATE anime SET picture = ? WHERE id = ?",
                                         (repdata[-1]['small'], anime.id), save=True)
                            que.put((anime, can))
                        else:
                            usePlaceholder(can)

            else:
                self.log("PICTURE", "No image yet", anime.title)
                que.put((anime, can))
            args = que.get()

        self.imQueue.put("STOP")
        self.log("THREAD", "Stopped image thread")
        return

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
        listrange = (0, (listrange[1] + 50) // self.animePerRow * self.animePerRow - 1)
        posy = self.scrollable_frame.canvas.canvasy(0)
        self.createList(filter, listrange)
        self.scrollable_frame.canvas.yview_moveto(posy / self.scrollable_frame.canvas.bbox('all')[3])
        return

    # ___Clean up___
    def clearLogs(self):
        for f in os.listdir(self.logsPath):
            path = os.path.join(self.logsPath, f)
            if path != self.logFile:
                os.remove(path)

    def clearCache(self):
        os.system('del /F /S /Q "{}"'.format(self.cache))
        shutil.rmtree(self.cache)

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

    def onClose(self):
        # .
        self.stopSearch = True

    def quit(self):
        self.onClose()
        try:
            self.root.destroy()
            self.root = None
        except Exception as e:
            self.log("ERROR", e)

    # ___Utils___
    def reloadAll(self):
        try:
            self.log('MAIN_STATE', "Reloading")
        except AttributeError:
            pass
        self.onClose()
        try:
            self.fen.destroy()
        except BaseException:
            pass
        self.fen = None

        self.loadingWindow()

        reloadFunc = {
            self.updateCache: "Updating cache",
            self.updateDirs: "Updating directories",
            self.updateTag: "Updating tags",
            self.regroupFiles: "Regrouping files",
            self.updateTitles: "Updating titles",
        }  # self.getSchedule:"Updating schedule"}#,self.getCharacters)
        self.start = time.time()
        loadStart = 0
        for i, item in enumerate(reloadFunc.items()):
            f, text = item
            thread = threading.Thread(target=f)
            thread.start()
            try:
                self.loadLabel['text'] = text
            except BaseException:
                if not self.loadfen.winfo_exists():
                    break
            loadStop = (i + 1) / len(reloadFunc) * 100
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
        Manager()

    def view(self, id):
        index = "indexList"
        keys = self.database(table="indexList").keys()
        ids = self.database.sql("SELECT * FROM indexList WHERE id=?", (id,))[0]
        ids = dict(zip(keys, ids))
        ids.pop("id")
        for api_key, id in ids.items():
            if id is not None:
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
        self.timer_id = self.fen.after(30, self.loading, n + 1, True)

    # ___Settings___
    def checkSettings(self):
        self.initLogs()
        self.log('CONFIG', "Settings:")
        if not os.path.exists(self.settingsPath):
            shutil.copyfile("settings.json", self.settingsPath)
        with open(self.settingsPath, 'r') as f:
            self.settings = json.load(f)
        updatedSettings = {}
        for cat, values in self.settings.items():
            for var, value in values.items():
                if var in self.pathSettings:
                    if value == "":
                        value = getattr(self, var)
                        updatedSettings[var] = value
                    if not os.path.exists(value):
                        os.mkdir(value)
                setattr(self, var, value)
                self.log('CONFIG', " ", var.ljust(30), '-', value)
        if updatedSettings != {}:
            self.setSettings(updatedSettings)

    def setSettings(self, settings):
        with open(self.settingsPath, 'r') as f:
            self.settings = json.load(f)
        for updateKey, updateValue in settings.items():
            for cat, values in self.settings.items():
                if updateKey in values.keys():
                    self.settings[cat][updateKey] = updateValue
                    break
            setattr(self, updateKey, updateValue)
        with open(self.settingsPath, 'w') as f:
            json.dump(self.settings, f, sort_keys=True, indent=4)

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
                        'NETWORK', "[ERROR] Couldn't find the torrent client!")
                else:

                    torrenthash = self.getTorrentHash(filePath)
                    self.qb.torrents_set_location(
                        location=path, torrent_hashes=[torrenthash])
            else:
                self.log(
                    'NETWORK', "[ERROR] Couldn't find the torrent client!")

            torrents = database.sql(
                "SELECT torrent FROM anime WHERE id = ?", (id,))[0][0]
            torrents = json.loads(torrents) if torrents is not None else []
            torrents.append(file)
            torrents = list(set(torrents))
            database(table="anime").set(
                {'id': id, 'torrent': json.dumps(torrents)})

            if id not in database.allkeys('tag') or database(
                    id=id, table='tag')['tag'] in (None, 'NONE'):
                database(table='tag').set({'id': id, 'tag': 'WATCHING'})

        assert url is not None or file is not None, "You need to specify either an url or a file path"
        threading.Thread(target=handler, args=(id, url, file)).start()

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
            self.log('NETWORK', "[ERROR] Couldn't find the torrent client!")

    def bluetoothConnect(self):
        pass
        # TODO -> En fait c'est chiant

    # ___Data update___
    def getSeason(self, year, season):
        def handler(year, season):
            for i, a in enumerate(self.api.season(year, season)):
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
        threading.Thread(target=handler, args=(year, season)).start()

        self.animeList = iter()
        # self.animeListReady = True
        self.createList(None, (0, 1000))

    def getCharactersData(self, id, callback=None):
        database = self.getDatabase()

        self.log('NETWORK_DATA', "Requesting characters data for id", id)
        characters = []

        keys = database(id=id, table="indexList").get()

        data = self.api.animeCharacters(id)

        for c in data:
            if c['id'] not in (b['id'] for b in characters):
                characters.append(c)

        # self.log("CHARACTER",len(characters),"characters found for anime id",id,"title",database(id=id,table="anime")['title'])
        for character in characters:
            sql = "SELECT EXISTS(SELECT 1 FROM characters WHERE id = ? AND anime_id = ?);"
            exists = bool(database.sql(
                sql, (character['id'], character['anime_id']))[0][0])
            if not exists:
                self.log("CHARACTER", "New character, anime id", id,
                         "id", character['id'], "name", character['name'])
                sql = "INSERT INTO characters(" + "{}," * (len(character.keys(
                )) - 1) + "{}) VALUES (" + "?," * (len(character.keys()) - 1) + "?);"
                sql = sql.format(*character.keys())
                try:
                    database.sql(sql, character.values())
                except Exception as e:
                    raise e
            database.save()

        if callback is not None:
            callback()

    def getCharacterData(self, id):
        database = self.getDatabase()

        self.log("NETWORK", "Requesting data for character id", id)
        # data = self.jikan.character(id)
        sql = "SELECT * FROM charactersIndex WHERE id=?"
        keys = database(table="charactersIndex").keys()[1:]
        api_keys = dict(zip(keys, database.sql(sql, (id,))[0][1:]))

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
            #     except Exception as e:
            #         raise e

        return character


if __name__ == '__main__':
    m = Manager()
