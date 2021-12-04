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

    from constants import Constants
    from update_utils import UpdateUtils
    from getters import Getters
    # from logger import Logger
    from anime_search import AnimeSearch
    from dbManager import db
    from classes import Anime, Character, AnimeList, CharacterList, TorrentList, SortedList, SortedDict
except ModuleNotFoundError as e:
    print(e)
    print("Please verify your app installation!")
    import sys
    sys.exit()


class Manager(Constants, UpdateUtils, Getters, AnimeSearch, *windows.windows):
    def __init__(self, remote=False):
        self.start = time.time()
        for e in Manager.__mro__:
            super(e, self).__init__()

        self.remote = remote
        self.animeFolder = []
        self.searchQueue = []
        self.relationIds = []
        self.characterIds = []
        self.timer_id = None
        self.searching = False
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
        self.getQB(use_thread=True)
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
        # if not self.searching:
        #     self.searching = True
        # else:
        #     return
        terms = None
        loop = True
        # while terms != self.searchTerms.get() and loop:
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
            print(self.animeList, dir(self.animeList))
            self.stopSearch = True
            self.animeListReady = True
            self.root.update()
            self.animeList = None
            self.createList()
        self.fen.update()

    def searchDb(self, terms):
        def enumerator(terms):
            sql = "SELECT anime.*,tag.tag,like.like FROM searchTitles JOIN anime using(id) LEFT JOIN tag using(id) LEFT JOIN like using(id) WHERE searchTitles.title LIKE '%{}%' GROUP BY anime.id ORDER BY anime.date_from DESC;".format(
                terms)
            keys = list(self.database.keys(table="anime")) + ['tag', 'like']
            anime_list = AnimeList(Anime(dict(zip(keys, data))) for data in self.database.sql(sql))
            return anime_list
            # TODO - Efficient?
            for data in self.database.sql(sql):
                data = Anime(dict(zip(keys, data)))
                # yield data

        self.updateTitles()
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
        while not torrents.empty():  # thread.is_alive() or
            while not torrents.is_ready():
                if self.root is not None:
                    self.root.update()
                time.sleep(0.001)
                continue

            a = torrents.get()
            title = a['filename']

            result = publisher_pattern.findall(a['filename'])
            if len(result) >= 1:
                publisher = result[0]
            else:
                publisher = None
            if publisher in titles.keys():
                if not a['filename'].replace(" ", "") in (e['filename'].replace(" ", "") for e in titles[publisher]):
                    titles[publisher].append(a)
            else:
                titles[publisher] = SortedList(keys=((itemgetter('seeds'), True),))
                titles[publisher].append(a)

            if not torrents.is_ready():
                yield titles.items()

        timer.stats()

    # ___Main List generation___
    def createList(self, criteria="DEFAULT", listrange=(0, 50)):
        def wait_for_next(animelist, default):
            if isinstance(animelist, AnimeList):
                empty_test = "not animelist.is_ready()"
            else:
                que = queue.Queue()
                t = threading.Thread(
                    target=lambda que, animelist, default: que.put(
                        next(
                            animelist, default)), args=(
                        que, animelist, default))
                t.start()
                animelist = que
                empty_test = "que.empty()"
            while eval(empty_test):
                try:
                    self.root.update()
                except AttributeError:
                    pass
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
                    if i == listrange[0]:
                        # TODO - Show when there are no results
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
        self.list_timer.start()
        if self.blank_image is None:
            self.blank_image = self.getImage(None, (225, 310))
        title = anime.title
        if title is None:
            print("No title for id:", anime.id, anime)
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

        queue.put((anime, img_can))
        self.list_timer.stop()

    def getElemImages(self):
        while not self.imQueue.empty():
            data = self.imQueue.get()
            if data != "STOP":
                im, can = data
                try:
                    image = ImageTk.PhotoImage(im)
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
        database = self.getDatabase()
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
        self.animeList = None
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
        self.log('MAIN_STATE', "Reloading")
        self.onClose()
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
            # thread = threading.Thread(target=f)
            # thread.start()
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
        keys = self.database.keys(table="indexList")
        ids = self.database.sql("SELECT * FROM indexList WHERE id=?", (id,))[0]
        ids = dict(zip(keys, ids))
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
        self.timer_id = self.fen.after(30, self.loading, n + 1, True)

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

            if database(id=id, table='tag')['tag'] in (None, 'NONE'):
                database.set({'id': id, 'tag': 'WATCHING'}, table='tag')

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
            self.log('NETWORK', "[ERROR] - Couldn't find the torrent client!")

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
        self.animeListReady = True
        self.root.update()
        self.createList(None, (0, 1000))

    def getCharactersData(self, id, callback=None):
        database = self.getDatabase()

        self.log('NETWORK_DATA', "Requesting characters data for id", id)
        characters = []

        keys = database(id=id, table="indexList")

        data = self.api.animeCharacters(id)

        for c in data:
            if c['id'] not in (b['id'] for b in characters):
                characters.append(c)

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
        sql = "SELECT * FROM charactersIndex WHERE id=?"
        keys = database.keys(table="charactersIndex")[1:]
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
            #     except Exception:
            #         raise

        return character


if __name__ == '__main__':
    m = Manager()
