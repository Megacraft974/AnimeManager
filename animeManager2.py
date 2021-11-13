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
import subprocess
import traceback
import socket
import hashlib
import webbrowser
from operator import itemgetter
from datetime import date, datetime, timedelta, time as datetime_time
from tkinter import *
from tkinter.ttk import Progressbar
from tkinter.filedialog import askopenfilename, askopenfilenames, askdirectory
from sqlite3 import OperationalError

try:
    from PIL import Image, ImageTk
    from qbittorrentapi import Client
    import qbittorrentapi.exceptions
    import lxml.etree
    import simplejson.errors  # TODO - WTF??
    from jikanpy.exceptions import APIException
    import jsonapi_client
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
    from dbManager import db
    from playerManager import MpvPlayer
    from classes import Anime, Character, AnimeList, CharacterList
    import utils
    import search_engines
    import animeAPI
except ModuleNotFoundError as e:
    print(e)
    print("Please verify your app installation!")
    import sys
    sys.exit()


class Manager():
    def __init__(self, remote=False):
        self.start = time.time()

        self.logs = ['DB_ERROR', 'DB_UPDATE', 'MAIN_STATE',
                     'NETWORK', 'SERVER', 'SETTINGS', 'TIME']

        appid = 'megacraft.anime.manager.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
        # 181915 - 282923 - 373734 - F8F8C4 - 98E22B(G) - E79622(O)

        cwd = os.path.dirname(os.path.abspath(__file__))
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
        self.qbLoop = None
        self.timer_id = None
        self.lastSearch = None
        self.searchThread = None
        self.stopSearch = False
        self.maxLogsSize = 50000  # In bytes
        self.animeListReady = False
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
            self.allLogs = ['CHARACTER', 'CONFIG', 'DB_ERROR', 'DB_UPDATE', 'DISK_ERROR',
                            'FILE_SEARCH', 'MAIN_STATE', 'NETWORK', 'NETWORK_DATA',
                            'PICTURE', 'RELATED', 'SCHEDULE', 'SERVER',
                            'SETTINGS', 'THREAD', 'TIME']
            self.pathSettings = ["animePath", "torrentPath",
                                 "iconPath", "cache", "dbPath", "logsPath"]
            self.websitesViewUrls = {"mal_id": "https://myanimeList.net/anime/{}",
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
                {'text': 'Redownload files', 'color': 'Green',
                 'command': self.redownload},
                {'text': 'Characters', 'color': 'Green',
                 'command': self.characterListWindow},
                {'text': 'Delete files', 'color': 'Red',
                 'command': self.deleteFiles},
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
                                  'No filter': {'color': 'Gray', 'filter': None}}
            self.status = {'airing': 'AIRING', 'Currently Airing': 'AIRING',
                           'completed': 'FINISHED', 'complete': 'FINISHED', 'Finished Airing': 'FINISHED',
                           'to_be_aired': 'UPCOMING', 'tba': 'UPCOMING', 'upcoming': 'UPCOMING', 'Not yet aired': 'UPCOMING',
                           'NONE': 'UNKNOWN', 'UPDATE': 'UNKNOWN'}

        if not os.path.exists(self.dbPath):
            self.database = db(self.dbPath)
            self.checkSettings()
            self.reloadAll()
            return
        else:
            self.database = db(self.dbPath)
            self.checkSettings()
        self.api = animeAPI.AnimeAPI('all', self.dbPath)
        # self.qb = Client(host=self.torrentApiAddress, username=self.torrentApiLogin, password=self.torrentApiPassword)
        self.getQB()
        self.imQueue = queue.Queue()

        if not self.remote:
            try:
                self.initWindow()

                self.log('MAIN_STATE', "Stopping")
                self.start = time.time()
                self.updateCache()
                self.updateDirs()
                self.updateTag()
                self.regroupFiles()
                self.updateTitles()
                self.getSchedule()
                self.log('TIME', "Stopping time:".ljust(25),
                         round(time.time() - self.start, 2), 'sec')
            except Exception as e:
                self.log("MAIN_STATE", "[ROOT]:\n", traceback.format_exc())

    def search(self, *args):
        terms = None
        loop = True
        while terms != self.searchTerms.get() and loop:
            terms = self.searchTerms.get()
            if len(terms) > 2:
                animeList = self.searchDb(terms)
                if animeList != False:
                    self.animeList = animeList
                    self.createList("")
                else:
                    self.getAnimeDataThread(terms)
                    loop = False
                    break
            else:
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
        if bool(self.database.sql(
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

    def getTorrentFiles(self, terms):  # Not used
        def getData(torrentDb, terms):
            name = torrentDb['name']
            lastTerms = None
            terms = terms.replace("-", " ")
            terms = re.sub(r'(^ | $)', '', terms)  # " ..." / "... "
            if name == "tokyo":
                searchterms = urllib.parse.quote(terms)
            else:
                searchterms = urllib.parse.quote_plus(terms)
            if lastTerms != searchterms:
                url = torrentDb['url'].format(searchterms)
                self.log('NETWORK_DATA', "Requesting data, url:", url)
                try:
                    r = requests.get(url)
                except BaseException:
                    self.log('NETWORK', "[ERROR] - Error while fetching data")
                    r = None
                # rep = r.text
                if r is not None:
                    # with open(lastSearchCache,"w",encoding="utf-8") as ls:
                    # 	ls.write(r.text)
                    try:
                        tree = lxml.etree.parse(io.BytesIO(r.content))
                    except Exception as e:
                        tree = None
                else:
                    tree = None

            if tree is not None:
                for child in tree.getroot().find('channel'):
                    if child.tag == 'item':
                        id = name + \
                            str(child.find('guid').text.split(
                                "?id=")[-1].split("/")[-1])
                        title = child.find('title').text
                        link = child.find('link').text
                        if name == "tokyo":
                            text = child.find('description').text
                            result = re.compile(
                                r'Size: (.*?)<br />').findall(text)
                            size = result[0] if len(result) >= 1 else ""
                        else:
                            size = child.find(
                                "{https://nyaa.si/xmlns/nyaa}size").text
                        # category = child.find('category').text
                        linkList = [d['link'] for d in data.values()]
                        if link not in linkList:
                            data[id] = {'name': title,
                                        'link': link, 'size': size}
            return data

        def sortTorrents(data):
            method = 'PUBLISHER'
            if method == 'COMMON_LETTERS':
                commons = {}
                for i in range(len(data)):
                    titlea = list(data.values())[i]['name']
                    for j in range(i, len(data)):
                        titleb = list(data.values())[j]['name']
                        if i != j:
                            for lastCommonPair, pair in enumerate(
                                    zip(titlea, titleb)):
                                if pair[0] != pair[1]:
                                    break
                            if lastCommonPair in commons.keys():
                                commons[lastCommonPair].append(
                                    (titlea, titleb))
                            else:
                                commons[lastCommonPair] = [(titlea, titleb)]
                minCommon = sorted([len(d['name'])
                                   for d in data.values()])[0] // 2
                sortedTitles = {}
                titles = []

                for l, pairs in sorted(commons.items(), reverse=True):
                    for pair in pairs:
                        for title in pair:
                            if title not in titles:
                                titles.append(title)
                                if l in sortedTitles.keys():
                                    sortedTitles[l].append(title)
                                else:
                                    sortedTitles[l] = [title]
                for l, titles in sortedTitles.items():
                    prefix = titles[0][:l - 1]
            elif method == 'PUBLISHER':
                pattern = re.compile(r'^\[(.*?)\]+')
                titles = {}
                for id, d in data.items():
                    title = d['name']
                    result = pattern.findall(title)
                    if len(result) >= 1:
                        publisher = result[0]
                    else:
                        publisher = None
                    if publisher in titles.keys():
                        if not d['name'] in (e['name']
                                             for e in titles[publisher]):
                            titles[publisher].append(d)
                    else:
                        titles[publisher] = [d]

                # 	decorated = [(title[::-1], title) for title in t]
                # 	decorated.sort()
                # 	t = [x[1] for x in decorated]
                # 	titles[p] = sorted(titles[p],key=lambda k:k[::-1])
                # 	titles[p] = t

            def sortkey(k):
                score = 0
                if k[0] in self.topPublishers:
                    score = len(self.topPublishers) - \
                        self.topPublishers.index(k[0])
                marked = ('dual', 'dub')
                breakLock = False
                for mark in marked:
                    for title in k[1]:
                        if mark in title['name'].lower():
                            score += len(self.topPublishers) + 1
                            breakLock = True
                        if breakLock:
                            break
                    if breakLock:
                        break
                return score

            titles = dict(sorted(titles.items(), key=sortkey, reverse=True))

            return titles
        torrentDbList = [
            {'name': 'tokyo',
             'url': "https://www.tokyotosho.info/rss.php?filter=1,10,4,12,11,5&terms={}&searchComment=0&entries=450",
             'file': "lastTokyoSearch.xml"},
            {'name': 'nyaa',
             'url': "https://nyaa.si/?page=rss&q={}&c=1_0&f=0",
             'file': "lastNyaaSearch.xml"}]
        data = {}
        que = queue.Queue()
        threads = []
        for torrentDb in torrentDbList:
            t = threading.Thread(target=lambda q, db, t, f: q.put(
                getData(db, t, f)), args=(que, torrentDb, terms))
            t.start()
            threads.append(t)

        for thread in threads:
            thread.join()

        while not que.empty():
            data = data | que.get()

        # return data
        return sortTorrents(data)

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
            'SELECT id,title,torrent FROM anime WHERE torrent is not null', iterate=True)
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

    def createList(self, filter=None, listrange=(0, 50)):
        def enumerator(ids):
            ids = list(ids)
            for id in ids:
                yield self.database(id=id[0], table="anime").get()

        def wait_for_next(animelist, default):
            que = queue.Queue()
            t = threading.Thread(target=lambda que, animelist, default: que.put(
                next(animelist, default)), args=(que, animelist, default))
            t.start()
            while que.empty():
                self.root.update()
                time.sleep(0.01)
            return que.get()

        if filter is None:
            commonFilter = "anime.status != 'UPCOMING'"
            if self.hideRated:
                commonFilter += " AND (rating NOT IN('R+','Rx') OR rating IS null)"
            ids = self.database.allkeys(
                "anime", range=listrange, sort=True, filter=commonFilter)
            self.animeList = enumerator(ids)
        elif self.animeList is None:
            # \nAND rating NOT IN('R+','Rx')"
            commonFilter = "\nAND anime.id NOT IN(SELECT anime.id FROM anime WHERE status = 'UPCOMING')"
            if self.hideRated:
                commonFilter += " \nAND (rating NOT IN('R+','Rx') OR rating IS null)"

            if filter == 'LIKED':
                ids = self.database.allkeys(
                    'like', sort=True, filter="like.like = 1" + commonFilter)

            elif filter == 'NONE':
                ids = self.database.allkeys(
                    'tag', sort=True, range=listrange, filter="tag.tag = 'NONE' OR anime.id NOT IN(SELECT id FROM tag)" + commonFilter)
                # b = self.database.allkeys('anime',sort=True,range=(0,listrange[1]-len(ids)),filter="id NOT IN(SELECT id FROM tag)"+commonFilter)
                # ids = utils.merge_iter(a,b)

            elif filter in ['UPCOMING', 'FINISHED', 'AIRING']:
                if filter == 'UPCOMING':
                    commonFilter = "\nAND (rating NOT IN('R+','Rx') OR rating IS null)" if self.hideRated else ""
                if filter == "UPCOMING":
                    sort = "ASC"
                else:
                    sort = True
                ids = self.database.allkeys(
                    'anime', sort=sort, range=listrange, filter="status = '{}'".format(filter) + commonFilter)

            elif filter == 'RATED':
                commonFilter = "\nAND anime.id NOT IN(SELECT anime.id FROM anime WHERE status = 'UPCOMING')"
                ids = self.database.allkeys(
                    'anime', sort=True, range=listrange, filter="rating IN('R+','Rx')" + commonFilter)

            elif filter == "RANDOM":
                ids = self.database.allkeys(
                    'anime', sort=True, range=listrange, order="RANDOM()", filter="anime.picture is not null")

            elif filter == "SEASON":
                return self.seasonSelector()
            else:
                if filter == 'WATCHING':
                    commonFilter = "\nAND anime.id NOT IN(SELECT anime.id FROM anime WHERE status = 'UPCOMING')"
                    order = """
						CASE WHEN anime.status = "AIRING" AND broadcast IS NOT NULL
						THEN (({}-SUBSTR(broadcast,1,1)+6)%7*24*60
							+({}-SUBSTR(broadcast,3,2))*60
							+({}-SUBSTR(broadcast,6,2))
						+86400)%86400 ELSE "9" END ASC,
						date_from DESC
					"""
                    sort_date = datetime.today() - timedelta(hours=5)
                    order = order.format(
                        sort_date.day, sort_date.hour, sort_date.minute)
                    # print(order,sort_date) # Depend on timezone - TODO
                else:
                    order = None
                ids = self.database.allkeys('tag', sort=True, range=listrange, filter="tag.tag = '{}'".format(
                    filter) + commonFilter, order=order)

            self.animeList = enumerator(ids)

        self.animeListReady = True  # Interrupt previous list generation
        self.root.update()
        # try:
        # 	for child in [c for c in self.fen.winfo_children() if "!progressbar" in str(c)]:
        # 		if "!progressbar" in str(child):
        # 			child.destroy()
        # except:
        # 	pass

        if listrange == (0, 50):
            self.scrollable_frame.canvas.yview_moveto(0)
        for child in self.scrollable_frame.winfo_children():
            child.destroy()
        # Ensure the Load More button is on the last column
        listrange = (listrange[0], listrange[1] //
                     self.animePerRow * self.animePerRow - 1)

        que = queue.Queue()
        threading.Thread(target=self.getImgThread, args=(que,)).start()
        self.getElemImages()

        self.animeListReady = False
        for i in range(listrange[0], listrange[1]):
            try:
                # data = self.animeList.get(10)
                # data = next(self.animeList,None)
                data = wait_for_next(self.animeList, None)
                # print(data.title)
            except TypeError:
                if type(self.animeList) is None:
                    self.animeList = []
                    break
            else:
                # print(data)
                if self.animeListReady or data is None:
                    break
                self.createElem(i, data, que)

            if i % self.animePerRow == 0:
                self.fen.update()

        # self.animeListReady = True

        que.put("STOP")

        try:
            e, self.animeList = utils.peek(self.animeList)
        except TypeError:
            pass
        else:
            if e is not None:
                self.loadMoreButton(i + 1, listrange, filter)

        self.scrollable_frame.update()
        try:
            self.fen.update()
        except BaseException:
            pass

        if 'TIME_ANIMELIST' in self.logs:
            self.logs.remove('TIME_ANIMELIST')
            self.log('TIME', "Anime list generated:".ljust(
                25), round(time.time() - self.start, 2), "sec")

    def createElem(self, index, anime, queue):
        im = Image.new('RGB', (225, 310), self.colors['Gray'])
        image = ImageTk.PhotoImage(im)

        img_can = Canvas(self.scrollable_frame, width=225, height=image.height(
        ), highlightthickness=0, bg=self.colors['Gray3'])
        img_can.bind("<Button-1>", lambda e,
                     id=anime.id: self.optionsWindow(id))
        img_can.bind("<Button-3>", lambda e, id=anime.id: self.view(id))
        img_can.grid(column=index % self.animePerRow,
                     row=index // self.animePerRow * 2)

        img_can.create_image(0, 0, image=image, anchor='nw')
        img_can.image = image

        title = anime.title
        if len(title) > 35:
            title = title[:35] + "..."

        if self.database(id=anime.id, table='like').exist() and bool(
                self.database(id=anime.id, table='like')['like']):
            title += " ❤"
        lbl = Label(self.scrollable_frame, text=title,
                    bg=self.colors['Gray2'], fg=self.colors[self.tagcolors[self.database(
                        id=anime.id, table='tag')['tag']]], font=("Source Code Pro Medium", 13),
                    bd=0, wraplength=220)
        lbl.grid(column=index % self.animePerRow,
                 row=(index // self.animePerRow * 2) + 1)
        lbl.name = str(anime.id)

        self.scrollable_frame.update()

        # filename = os.path.join(self.cache,str(anime.id)+".jpg")
        queue.put((anime, img_can))  # (filename,anime.id,anime,img_can)

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
        args = que.get()
        while args != "STOP":
            anime, can = args
            filename = os.path.join(self.cache, str(anime.id) + ".jpg")

            if str(anime.id) + ".jpg" in os.listdir(self.cache):
                try:
                    im = Image.open(filename)
                    self.imQueue.put((im, can))
                    args = que.get()
                    continue
                except BaseException:
                    self.log('DISK_ERROR', "[ERROR] Image file is corrupted, deleting, anime",
                             anime.title, "id", anime.id, "file", filename)
                    os.remove(filename)

            self.log("PICTURE", "Requesting picture for anime id",
                     anime.id, "title", anime.title)
            try:
                if anime.picture is not None:
                    req = requests.get(anime.picture)
                else:
                    print("No image yet", anime.title)
                    que.put((anime, can))
            except requests.exceptions.ReadTimeout as e:
                self.log("PICTURE", "Timed out!")
                usePlaceholder(can)
            except requests.exceptions.ConnectionError as e:
                self.log('PICTURE', "[ERROR] - No internet connection!")
                usePlaceholder(can)
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
                            "DISK_ERROR", "File not found error while saving image", filename)
                    self.imQueue.put((im, can))
                else:
                    self.log("PICTURE", "[ERROR] Status code", req.status_code,
                             "for anime", anime.title, "requesting new picture.")
                    try:
                        repdata = self.api.animePictures(anime.id)
                    except requests.exceptions.ReadTimeout as e:
                        self.log("PICTURE", "Timed out!")
                    except requests.exceptions.ConnectionError as e:
                        self.log(
                            'PICTURE', "[ERROR] - No internet connection!")
                    else:
                        if len(repdata) >= 1:
                            args = list(args)
                            args[2]['picture'] = repdata[-1]['small']
                            database = self.getDatabase()
                            database.sql("UPDATE anime SET picture = ? WHERE id = ?",
                                         (repdata[-1]['small'], anime.id), save=True)
                            que.put((anime, can))
                        else:
                            usePlaceholder(can)
            args = que.get()

        self.imQueue.put("STOP")
        self.log("THREAD", "Stopped image thread")
        return

    def loadMoreButton(self, index, listrange, filter):
        im = Image.new('RGB', (225, 310), self.colors['Gray4'])
        image = ImageTk.PhotoImage(im)
        img_can = Canvas(self.scrollable_frame, width=225, height=image.height(
        ), highlightthickness=0, bg=self.colors['Gray2'])
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
        if filter is not None:
            self.animeList = None

        listrange = (0, (listrange[1] + 50) //
                     self.animePerRow * self.animePerRow - 1)
        posy = self.scrollable_frame.canvas.canvasy(0)
        self.createList(filter, listrange)
        self.scrollable_frame.canvas.yview_moveto(
            posy / self.scrollable_frame.canvas.bbox('all')[3])
        return

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
            self.database = db(self.dbPath)
            self.reloadAll()

    def onClose(self):
        # .
        self.stopSearch = True

    def getQB(self, reconnect=False):
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
                        'MAIN_STATE', '[ERROR] - Invalid credentials for the torrent client!')
                    self.qb = None
                    state = "CREDENTIALS"
                else:
                    self.qb.app_set_preferences(self.qb_settings)
                    self.log('MAIN_STATE', 'Qbittorrent version:', self.qb.app_version(
                    ), "- web API version:", self.qb.app_web_api_version())
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

    def quit(self):
        self.onClose()
        try:
            self.root.after_cancel(self.qbLoop)
        except ValueError:
            pass
        try:
            self.root.destroy()
            self.root = None
        except Exception as e:
            self.log("ERROR", e)

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

        reloadFunc = {self.updateCache: "Updating cache",
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
        if self.searchThread is None or not self.searchThread.is_alive() or self.stopSearch:
            self.loadCanvas.delete(ALL)
            self.timer_id = None
            return
            # self.search()
        elif self.timer_id is None or after:
            n = n % len(self.giflist)
            gif = self.giflist[n % len(self.giflist)]
            self.loadCanvas.delete(ALL)
            self.loadCanvas.create_image(
                gif.width() // 2, gif.height() // 2, image=gif)
        if self.timer_id is not None:
            self.fen.after_cancel(self.timer_id)
        self.timer_id = self.fen.after(30, self.loading, n + 1, True)

    def log(self, category, *text, end="\n"):
        toLog = "[{}]".format(category.center(13)) + " - "
        toLog += " ".join([str(t) for t in text])
        if category in self.logs:
            print(toLog, flush=True, end=end)
        if self.loadfen is not None and threading.main_thread() == threading.current_thread():
            try:
                self.loadLabel['text'] = toLog
                self.loadfen.update()
            except BaseException:
                pass
        with open(self.logFile, "a", encoding='utf-8') as f:
            timestamp = "[{}]".format(time.strftime("%H:%M:%S"))
            f.write(timestamp + toLog + "\n")

    def initLogs(self):
        if not os.path.exists(self.logsPath):
            os.mkdir(self.logsPath)

        logsList = os.listdir(self.logsPath)
        size = sum(os.path.getsize(os.path.join(self.logsPath, f))
                   for f in logsList)

        while size >= self.maxLogsSize and len(logsList) > 1:
            os.remove(os.path.join(self.logsPath, logsList[0]))
            logsList = os.listdir(self.logsPath)
            size = sum(os.path.getsize(os.path.join(self.logsPath, f))
                       for f in logsList)

        self.logFile = os.path.normpath(os.path.join(self.logsPath, "log_{}.txt".format(
            datetime.today().strftime("%Y-%m-%dT%H.%M.%S"))))
        with open(self.logFile, "w") as f:
            f.write(
                "_" *
                10 +
                date.today().strftime("%d/%m/%y") +
                "_" *
                10 +
                "\n")

        if self.remote:
            self.logs = []

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
                    print(cat, updateKey,
                          self.settings[cat][updateKey], updateValue)
                    self.settings[cat][updateKey] = updateValue
                    break
            setattr(self, updateKey, updateValue)
        with open(self.settingsPath, 'w') as f:
            json.dump(self.settings, f, sort_keys=True, indent=4)

    def getDatabase(self):
        if threading.main_thread() == threading.current_thread():
            return self.database
        else:
            return db(self.dbPath)

    def getImage(self, path, size=None):
        if os.path.isfile(path):
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
        def fileFormat(f): return ''.join(
            f.rsplit(".torrent", 1)[0].split(" ")).lower()
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
            if type(anime) != Anime:
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

    def getChild(self, w):
        out = []
        if not type(w) in (Button, Checkbutton, Toplevel, OptionMenu):
            out.append(w)
        if type(w) in [Toplevel, Canvas, Frame]:
            for w in w.winfo_children():
                out += self.getChild(w)
        return out

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
                        # 	url = "https://torproxy.cyou/?cdURL="+url
                        req = None
                        req = requests.get(url, allow_redirects=True)
                        file = urllib.parse.unquote(
                            req.headers['content-disposition'].split('"')[-2])
                    except BaseException:
                        self.log('NETWORK', "[ERROR] - Error downloading file at url", url,
                                 "status_code", req.status_code if req is not None else "unknown")
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
                    'NETWORK', 'Redownloaded {} torrents'.format(len(torrents)))
            else:
                self.log(
                    'NETWORK', 'No torrents to download!'.format(len(torrents)))

        else:
            self.log('NETWORK', "[ERROR] Couldn't find the torrent client!")

    def round_rectangle(self, canvas, x1, y1, x2, y2,
                        r=25, inner=False, **kwargs):
        points = (x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y1 + r, x2, y2 - r, x2, y2 - r, x2,
                  y2, x2 - r, y2, x2 - r, y2, x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1)
        innerKwargs = kwargs.copy()
        if not inner:
            if 'fill' in innerKwargs.keys(
            ) and innerKwargs['fill'] == self.colors['Gray2']:
                innerKwargs['fill'] = self.colors['Gray3']
            else:
                innerKwargs['fill'] = self.colors['Gray2']
        canvas.create_polygon(points, **innerKwargs, smooth=True)
        if not inner:
            border = 2
            self.round_rectangle(canvas, x1 + border, y1 + border,
                                 x2 - border, y2 - border, r, inner=True, **kwargs)

    def bluetoothConnect(self):
        pass
        # TODO -> En fait c'est chiant

    def copy_title(self, id):
        database = self.getDatabase()
        self.root.clipboard_clear()
        title = database(id=id, table="anime")['title']
        self.root.clipboard_append(title)

    def reload(self, id, update=True):
        def handler(id, que):
            database = self.getDatabase()
            keys = database(id=id, table="indexList").get()
            data = None
            try:
                data = self.api.anime(id)
            except requests.exceptions.ConnectionError as e:
                self.log(
                    'NETWORK',
                    "No internet connection, skipping schedule")
                return
            except APIException as e:
                if e.status_code == 429:
                    self.log('NETWORK', "[ERROR] - Status code 429, skipping")
                else:
                    raise e
                return
            except requests.exceptions.ReadTimeout as e:
                self.log("NETWORK", "Timed out!")
                return
            except simplejson.errors.JSONDecodeError as e:
                self.log("NETWORK", "[ERROR] -", e)
                raise e
            que.put(data)

        if 'TIME' in self.logs:
            self.start = time.time()

        reloadFen = True
        if update:
            que = queue.Queue()
            thread = threading.Thread(target=handler, args=(id, que))
            thread.start()

            sql = "DELETE FROM characters WHERE anime_id=?"
            self.database.sql(sql, (id,), save=True)

            while thread.is_alive():
                self.root.update()
                if self.choice is None or not self.choice.winfo_exists():
                    reloadFen = False
            data = que.get()
            if data is not None:
                self.database(id=id, table="anime").set(data)

        if reloadFen:
            self.choice.clear()
            self.optionsWindow(id)
            self.choice.focus_force()

            self.log('TIME', "Reloading:".ljust(25),
                     round(time.time() - self.start, 2), "sec")

    def deleteFiles(self, id):
        def clearFolder(path):
            if len(os.listdir(path)) >= 1:
                self.log("DISK_ERROR",
                         "Some files haven't been removed from folder", path)
            try:
                os.rmdir(path)
            except BaseException:
                self.log("DISK_ERROR", "Couldn't delete folder", path)
        folder = self.getFolder(id)
        path = os.path.join(
            self.animePath,
            folder) if folder is not None else ""

        if os.path.exists(path):
            anime = self.database(id=id, table="anime")
            torrents = json.loads(
                anime.torrent) if anime.torrent is not None else []

            if self.getQB() == "OK":
                hashes = [self.getTorrentHash(os.path.join(
                    self.torrentPath, torrent)) for torrent in torrents]
                # hashes = [torrent['hash'] for torrent in self.qb.torrents_info() if torrent['name'] + ".torrent" in torrents]

                self.log('DB_UPDATE', "Deleting", path, "-",
                         len(hashes), "torrents to remove")

                self.qb.torrents_delete(
                    delete_files=True, torrent_hashes=hashes)  # TODO - NOT WORKING

            try:
                # rd /S /Q "\\?\D:\Animes\folder."
                os.system('del /F /S /Q "{}"'.format(path))
                clearFolder(path)
            except Exception as e:
                self.log('DISK_ERROR', "Error while removing file", path)
                raise e
        else:
            self.log("DISK_ERROR", "Folder path doesn't exist:", path)
        self.log("DB_UPDATE", "Deleted all files")
        self.reload(id, False)

    def delete(self, id):
        self.log('DB_UPDATE', "Deleted", self.database(
            id=id, table="anime")['title'])
        for anime in self.animeList:
            if anime.id == id:
                self.animeList.remove(anime)
        self.database(id=id).remove()
        self.createList()
        self.choice.exit()

    def initWindow(self):
        # Functions
        if True:
            def options(e):
                # Placeholder
                self.menuOptions[e]['command']()

            def filter(e):
                self.searchTerms.set("")
                self.animeList = None
                self.createList(self.filterOptions[e]['filter'])

            def bringToTop(e):
                try:
                    self.fen.lift()
                    self.fen.focus_force()
                except BaseException:
                    pass
                # self.fen.focus_force()
                self.root.iconify()

            def checkFocus(e):
                if e.widget.winfo_toplevel() == self.fen:
                    for c in self.fen.winfo_children():
                        if type(c) == Toplevel:
                            if hasattr(c, "topLevel"):
                                c.topLevel.focus_force()
                            else:
                                c.focus_force()

            def checkServer():
                if threading.main_thread() == threading.current_thread():
                    threading.Thread(target=checkServer).start()
                    return
                if self.enableServer:
                    self.server = utils.startServer(
                        self.hostName, self.serverPort, self.dbPath, self)
                elif self.server is not None:
                    utils.stopServer(self.server, self)
                    self.server = None

            def start_move(event, window):
                window.x = event.x
                window.y = event.y

            def do_move(event, window):
                try:
                    deltax = event.x - window.x
                    deltay = event.y - window.y
                    x = window.winfo_x() + deltax
                    y = window.winfo_y() + deltay
                    window.geometry(f"+{x}+{y}")
                except AttributeError as e:
                    self.log("[ERROR]", "Error while moving main window")

        if self.root is None:
            self.root = Tk()
            path = os.path.join(self.iconPath, "favicon.png")
            self.root.iconphoto(False, self.getImage(path))
            self.root.title(self.mainWindowTitle)
            self.root.attributes('-alpha', 0.0)
            self.root.attributes('-topmost', 1)
            self.root.protocol("WM_DELETE_WINDOW", self.onClose)
            self.root.focus_force()
            self.root.update()
            # root.lower()
            self.root.iconify()
            self.root.bind("<Map>", bringToTop)

        if self.fen is None:
            self.fen = Toplevel(self.root)
            self.fen.focus_force()
            self.fen.configure(bg=self.colors['Gray3'])
            self.fen.geometry(
                "{}x{}+100+100".format(self.mainWindowWidth, self.mainWindowHeight))
            self.fen.overrideredirect(True)
            self.fen.title(self.mainWindowTitle)
            path = os.path.join(self.iconPath, "favicon.png")
            self.fen.wm_iconphoto(False, self.getImage(path))
            self.fen.bind("<FocusIn>", checkFocus)

            self.fen.resizable(False, True)
            dbFrame = Frame(self.fen, bg=self.colors['Gray2'], width=920)
            head = Frame(dbFrame, bg=self.colors['Gray2'])
            head.pack(fill="both")
            head.grid_columnconfigure(1, weight=1)

            # Top bar
            if True:
                droplistIcon = self.getImage(os.path.join(
                    self.iconPath, "menu.png"), (30, 30))
                droplist = OptionMenu(
                    head, StringVar(), *self.menuOptions.keys(), command=options)
                droplist.configure(indicatoron=False, image=droplistIcon, highlightthickness=0, borderwidth=0,
                                   activebackground=self.colors['Gray2'], bg=self.colors['Gray2'],)
                droplist["menu"].configure(bd=0, borderwidth=0, activeborderwidth=0, font=("Source Code Pro Medium", 13),
                                           activebackground=self.colors['Gray2'], activeforeground=self.colors['White'], bg=self.colors['Gray2'], fg=self.colors['White'],)
                droplist.image = droplistIcon
                droplist.grid(row=0, column=0, padx=15)

                for i, color in enumerate([c['color']
                                          for c in self.menuOptions.values()]):
                    droplist['menu'].entryconfig(
                        i, foreground=self.colors[color])

                self.searchTerms = StringVar(self.fen)
                self.searchTerms.trace_add(("write"), self.search)

                searchBar = Entry(head, textvariable=self.searchTerms, highlightthickness=0, borderwidth=0, font=("Source Code Pro Medium", 13),
                                  bg=self.colors['Gray2'], fg=self.colors['White'])
                searchBar.grid(row=0, column=1, sticky="nsew", pady=10)
                #searchBar.bind("<Return>", search)
                searchBar.bind("<ButtonPress-1>",
                               lambda e: start_move(e, self.fen))
                searchBar.bind("<B1-Motion>", lambda e: do_move(e, self.fen))
                searchBar.bind("<Control-Return>", lambda e: self.getAnimeDataThread(
                    self.searchTerms.get()) if self.searchTerms.get() != "" else None)

                self.giflist = [PhotoImage(file=os.path.join(
                    self.iconPath, 'loading.gif'), format='gif -index %i' % (i)) for i in range(30)]
                self.loadCanvas = Canvas(
                    head, bg=self.colors['Gray2'], highlightthickness=0, width=56, height=56)
                self.loadCanvas.grid(row=0, column=2)

                filterIcon = self.getImage(os.path.join(
                    self.iconPath, "filter.png"), (35, 35))
                filter = OptionMenu(head, StringVar(), *
                                    self.filterOptions.keys(), command=filter)
                filter.configure(indicatoron=False, image=filterIcon, highlightthickness=0, borderwidth=0,
                                 activebackground=self.colors['Gray2'], bg=self.colors['Gray2'])
                filter["menu"].configure(bd=0, borderwidth=0, activeborderwidth=0, font=("Source Code Pro Medium", 13),
                                         activebackground=self.colors['Gray2'], activeforeground=self.colors['White'], bg=self.colors['Gray2'], fg=self.colors['White'],)
                filter.image = filterIcon
                filter.grid(row=0, column=3, padx=0)

                for i, color in enumerate(
                        [c['color'] for c in self.filterOptions.values()]):
                    filter['menu'].entryconfig(
                        i, foreground=self.colors[color])

                closeIcon = self.getImage(os.path.join(
                    self.iconPath, "close.png"), (40, 40))
                Button(head, image=closeIcon, bd=0, relief='solid', activebackground=self.colors['Gray2'], bg=self.colors['Gray2'],
                       command=self.quit
                       ).grid(row=0, column=4, padx=10)

            self.scrollable_frame = utils.ScrollableFrame(
                dbFrame, bg=self.colors['Gray2'], width=900)
            self.scrollable_frame.pack(fill="both", expand=True)

            Label(self.scrollable_frame, text="Loading...", bg=self.colors['Gray2'], fg=self.colors['Gray4'], font=(
                "Source Code Pro Medium", 20)).grid(row=0, column=0, columnspan=4, sticky="nsew")

            dbFrame.pack(fill="both", expand=True)
            for i in range(4):
                self.scrollable_frame.grid_columnconfigure(i, weight=1)

        self.fen.update()

        self.log('TIME', "Window created:".ljust(25),
                 round(time.time() - self.start, 2), "sec")

        if 'TIME' in self.logs:
            self.logs.append('TIME_ANIMELIST')
        self.animeList = None
        self.createList()
        checkServer()

        self.log('TIME', "Ready:".ljust(25), round(
            time.time() - self.start, 2), "sec")

        self.fen.mainloop()

    def optionsWindow(self, id):
        # Functions
        if True:
            def importTorrent(id):
                def removeOld(self, t_id, t_torrents):
                    self.log('DB_UPDATE', "Removing torrent duplicates")
                    if threading.main_thread() == threading.current_thread():
                        database = self.database
                    else:
                        try:
                            database = db(self.dbPath)
                        except OperationalError as e:
                            if e.args == ('unable to open database file',):
                                self.log(
                                    "[DB_ERROR]", "Error while connecting to database")
                                return
                            else:
                                self.log("ERROR", e.args)
                                raise e
                    for id, torrents in database.sql(
                            "SELECT id,torrent FROM anime WHERE torrent is not null AND id != ?;", (t_id,), iterate=True):
                        torrents = json.loads(torrents)
                        for t_torrent in t_torrents:
                            if id != t_id and t_torrent in torrents:
                                torrents.remove(t_torrent)
                                if len(torrents) >= 1:
                                    data = json.dumps(torrents)
                                else:
                                    data = None
                                self.log('DB_UPDATE', "Id", id,
                                         "has torrent", t_id, "removing")
                                database(id=id, table="anime").update(
                                    'torrent', data)
                    self.log('DB_UPDATE', "Done!")

                torrents = self.database.sql(
                    "SELECT torrent FROM anime WHERE id = ?", (id,))[0][0]
                torrents = json.loads(torrents) if torrents is not None else []
                default = '"' + '" "'.join(torrents) + '"'
                filepaths = askopenfilenames(parent=self.root, title="Select torrents", initialdir=self.torrentPath,
                                             initialfile=default, filetypes=[("Torrents files", (".torrent"))])
                torrents = []
                for path in filepaths:
                    torrents.append(path.rsplit("/")[-1])
                if len(torrents) >= 1:
                    self.database(id=id, table="anime").set(
                        {'id': id, 'torrent': json.dumps(torrents)})
                    threading.Thread(target=removeOld, args=(
                        self, id, torrents)).start()

            def findTorrent(id):
                if self.getQB() == "OK":
                    if threading.main_thread() == threading.current_thread():
                        database = self.database
                    else:
                        database = db(self.dbPath)

                    torrents = database.sql(
                        "SELECT torrent FROM anime WHERE id = ?", (id,))[0][0]
                    torrents = json.loads(
                        torrents) if torrents is not None else []
                    target = None

                    if torrents == []:
                        return

                    torrent_hashes = []
                    for t in torrents:
                        path = os.path.join(self.torrentPath, t)
                        if os.path.exists(path):
                            torrent_hash = self.getTorrentHash(path)
                            torrent_hashes.append(torrent_hash)

                    qbtorrents = self.qb.torrents_info(
                        status_filter="downloading", torrent_hashes="|".join(torrent_hashes))

                    if len(qbtorrents) > 0:
                        self.choice.hash = qbtorrents[0].hash
                        self.choice.after(
                            1, lambda id=id: self.reload(id, False))
                    # return target

            def updateLoadingBar(id, bar, text):
                hash = self.choice.hash
                try:
                    torrent = self.qb.torrents_properties(hash)
                except qbittorrentapi.exceptions.NotFound404Error:
                    value = 100
                else:
                    value = torrent.pieces_have / torrent.pieces_num * 100
                if value == 100:
                    del self.choice.hash
                    self.reload(id, update=False)
                else:
                    try:
                        bar['value'] = value
                        text.configure(text=str(round(value, 2)) + "%")
                        self.choice.update()
                    except BaseException:
                        pass
                    self.choice.after(500, lambda id=id, bar=bar,
                                      hash=hash: updateLoadingBar(id, bar, text))

            def tag(id, tag):
                self.database(table='tag').set({'id': id, 'tag': tag})

                for lbl in self.scrollable_frame.winfo_children():
                    if lbl.winfo_class() == 'Label' and lbl.name == str(id):
                        lbl.configure(fg=self.colors[self.tagcolors[tag]])
                        break
                self.reload(id, False)

            def like(id, b):
                d = self.database(id=id, table='like')
                liked = d.exist() and bool(d['like'])
                d.set({'id': id, 'like': not liked})

                if not liked:
                    im = Image.open(os.path.join(self.iconPath, "heart.png"))
                else:
                    im = Image.open(os.path.join(
                        self.iconPath, "heart(1).png"))

                folder = self.getFolder(id)
                showFolderButtons = folder is not None and os.path.isdir(
                    os.path.join(self.animePath, folder))
                iconSize = (50, 50) if showFolderButtons else (30, 30)
                im = im.resize(iconSize)
                image = ImageTk.PhotoImage(im)
                b.configure(image=image)
                b.image = image
                b.update()

                for lbl in self.scrollable_frame.winfo_children():
                    if lbl.winfo_class() == 'Label' and lbl.name == str(id):
                        text = lbl.cget("text").replace(" ❤", "")
                        if not liked:
                            text += " ❤"
                        lbl['text'] = text
                        lbl.update()
                        break

            def watch(e, eps, var):
                var.set("Watch")
                video = [i['title'] for i in eps].index(e)
                playlist = [i['path'] for i in eps]
                self.log('MAIN_STATE', "Watching", e)
                # threading.Thread(target=MpvPlayer, args=(self.root, playlist, video, id, self.dbPath)).start()
                MpvPlayer(playlist, video, id, self.dbPath)

            def openEps(e, eps, var):
                var.set("Watch")
                playlist = [os.path.normpath(i['path']) for i in eps.values()]
                folder = os.path.dirname(playlist[0])
                self.log('MAIN_STATE', "Opening", len(playlist), "files")
                subprocess.call(
                    [os.path.normpath("C:/Program Files/VideoLAN/VLC/vlc.exe"), folder])

            def ddlFromUrl(id):
                def callback(var, id):
                    url = var.get()
                    self.downloadFile(id, url=url)
                self.textPopupWindow(self.choice, "Enter torrent url",
                                     lambda var, id=id: callback(var, id), fentype="TEXT")

            def trailer(id):
                data = self.database(id=id, table="anime").get()
                trailer = anime.trailer
                if trailer is not None:
                    self.log('MAIN_STATE', "Watching trailer for anime",
                             anime.title, "url", trailer)
                    # threading.Thread(target=MpvPlayer, args=((trailer,), 0, None, None, True)).start()
                    MpvPlayer((trailer,), 0, url=True)

            def getEpisodes(folder):
                def folderLister(folder):
                    if folder == "" or folder is None or not os.path.isdir(
                            folder):
                        return
                    for f in os.listdir(folder):
                        path = os.path.join(folder, f)
                        if os.path.isdir(path):
                            for f in folderLister(path):
                                yield f
                        else:
                            yield path
                eps = []
                videoSuffixes = ("mkv", "mp4", "avi")
                blacklist = ("Specials", "Extras")

                if folder == "" or folder is None or not os.path.isdir(
                        os.path.join(self.animePath, folder)):
                    return {}

                folder = folder + "/"
                files = folderLister(os.path.join(self.animePath, folder))

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
                        # (r'(?:E|Episode|Ep|Eps|-|_) ?([0-9]{1,2})(?: |_|\.|v\d )'),)

                        for p in epsPatterns:
                            m = re.findall(p, filename)
                            if len(m) > 0:
                                episode = m[0]
                                break
                        # self.log('FILE_SEARCH',"/",episode,"/",end=" - ")
                        if episode == "?":
                            episode = str(len(eps) + 1).zfill(2)  # Hacky

                        season = ""
                        for p in seasonPatterns:
                            result = re.findall(p, file)
                            if len(result) >= 1:
                                season = result[0]
                                break

                        # seasonText = "S"+str(season) if season != "" else ""
                        # title = "[{}] - {}E{}: {}".format(publisher, seasonText, episode, filename)
                        # self.log('FILE_SEARCH',filename)
                        title = filename.rsplit(".", 1)[0]
                        title = re.sub(r'([\._])', ' ', title)  # ./,/-/_
                        title = re.sub(r'  +?', '', title)  # "  "
                        eps.append({'title': title, 'path': file,
                                   'season': season, 'episode': episode})

                eps.sort(key=lambda d: int(
                    str(d['season']) + str(d['episode'])))
                return eps

            def getDateText(datefrom, dateto, broadcast):
                today = date.today()
                delta = today - datefrom  # - timedelta(days=1)
                if status == 'FINISHED':
                    if dateto is None:
                        datetext = "Published on {}".format(
                            datefrom.strftime("%d %b %Y"))
                    else:
                        datetext = "From {} to {} ({} days)".format(
                            datefrom.strftime("%d %b %Y"), dateto.strftime("%d %b %Y"), delta.days)
                elif status == 'AIRING':
                    datetext = "Since {} ({} days)".format(
                        datefrom.strftime("%d %b %Y"), delta.days)
                    # ,'Unknown','Not scheduled once per week'):
                    if broadcast is not None:
                        weekday, hour, minute = map(int, broadcast.split("-"))

                        daysLeft = (weekday - today.weekday()) % 7
                        dateObj = datetime.today() + timedelta(days=daysLeft)

                        # Depends on timezone - TODO
                        hourDateObj = timedelta(hours=hour - 5, minutes=minute)
                        dateObj = datetime.combine(
                            dateObj.date(), datetime_time.min) + hourDateObj
                        text = dateObj.strftime(
                            "Next episode on %a %d at %H:%M")
                        datetext += "\n{}".format(text)

                        daysSince = (today.weekday() - weekday) % 7
                        text = "Last episode: {}"
                        if daysSince == 0:
                            text = text.format("Today")
                        elif daysSince == 1:
                            text = text.format("Yesterday")
                        elif daysSince > 1:
                            text = text.format(str(daysSince) + " days ago")
                        else:
                            text = text.format("uhh?")
                        datetext += "\n{}".format(text)
                    else:
                        daysSince = ((delta.days - 1) % 7)
                        dateObj = date.today() - timedelta(days=daysSince)
                        text = dateObj.strftime("Last episode on %a %d ({})")
                        if daysSince == 0:
                            text = text.format("Today")
                        elif daysSince == 1:
                            text = text.format("Yesterday")
                        elif daysSince > 1:
                            text = text.format(str(daysSince) + " days ago")
                        else:
                            text = text.format("uhh?")
                        datetext += "\n{}".format(text)

                elif status == 'UPCOMING':
                    datetext = "On {} ({} days left)".format(
                        datefrom.strftime("%d %b %Y"), -delta.days)
                return datetext

            def switch(id, titles=None):
                if titles is not None:
                    id = titles[id]
                self.choice.clear()
                self.optionsWindow(id)

            def dataUpdate(id):
                database = self.getDatabase()
                try:
                    data = self.api.anime(id)
                except requests.exceptions.ConnectionError as e:
                    self.log(
                        'NETWORK', "No internet connection, skipping schedule")
                    return
                except APIException as e:
                    if e.status_code == 429:
                        self.log(
                            'NETWORK', "[ERROR] - Status code 429, skipping schedule")
                    else:
                        raise e
                    return
                except requests.exceptions.ReadTimeout as e:
                    self.log("NETWORK", "Timed out!")
                    return
                except simplejson.errors.JSONDecodeError as e:
                    self.log("SCHEDULE", e)
                    raise e

                database(id=id, table="anime").set(data)
                if 'status' in data.keys() and anime.status != 'UPDATE':
                    self.choice.after(1, lambda id=id: self.reload(id))

        # Window init - Fancy corners - Main frame
        if True:
            anime = self.database(id=id, table="anime").get()

            if not self.database(id=id, table="anime").exist(
            ) or anime.status == 'UPDATE':
                threading.Thread(target=dataUpdate, args=(id,)).start()
                anime.title = "Loading..."

            if self.choice is None or not self.choice.winfo_exists():
                size = (self.infoWindowMinWidth, self.infoWindowMinHeight)
                self.choice = utils.RoundTopLevel(
                    self.fen, title=anime.title, minsize=size, bg=self.colors['Gray2'], fg=self.colors['Gray3'])
                self.choice.titleLbl.configure(
                    fg=self.colors[self.tagcolors[self.database(id=id, table='tag')['tag']]])
            else:
                self.choice.clear()
                self.choice.titleLbl.configure(text=anime.title, bg=self.colors['Gray2'], fg=self.colors[self.tagcolors[self.database(
                    id=id, table='tag')['tag']]], font=("Source Code Pro Medium", 15))

        # Title - File buttons
        if True:
            titleFrame = Frame(self.choice, bg=self.colors['Gray2'])

            if 'hash' in self.choice.__dict__.keys():
                offRow = 1
                bar = Progressbar(
                    titleFrame, orient=HORIZONTAL, mode='determinate')
                bar.grid(row=0, column=0, columnspan=2,
                         sticky="nsew", padx=2, pady=2)
                text = Label(titleFrame, text="0%", bg=self.colors['Gray2'], fg=self.colors['Gray4'], font=(
                    "Source Code Pro Medium", 15))
                text.grid(row=0, column=2, padx=10)

                # self.choice.hash = torrent['hash']
                updateLoadingBar(id, bar, text)
            else:
                offRow = 0
            b = Button(titleFrame, text="Download torrents", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                       activebackground=self.colors['Gray2'], activeforeground=self.colors[
                           'White'], bg=self.colors['Gray3'], fg=self.colors['White'],
                       command=lambda id=id: self.ddlWindow(id)
                       )
            b.bind("<Button-3>", lambda e, id=id: ddlFromUrl(id))
            b.grid(row=1 + offRow, column=0, sticky="nsew", padx=2, pady=2)

            Button(titleFrame, text="Locate torrents", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'White'], bg=self.colors['Gray3'], fg=self.colors['White'],
                   command=lambda id=id: importTorrent(id)
                   ).grid(row=1 + offRow, column=1, sticky="nsew", padx=2, pady=2)

            offCol = 0
            folder = self.getFolder(id)
            showFolderButtons = folder is not None and os.path.isdir(
                os.path.join(self.animePath, folder))
            if showFolderButtons:
                Button(titleFrame, text="Open folder", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                       activebackground=self.colors['Gray2'], activeforeground=self.colors[
                           'White'], bg=self.colors['Gray3'], fg=self.colors['White'],
                       command=lambda folder=folder: os.system('explorer "{}"'.format(
                           os.path.normpath(os.path.join(self.animePath, folder))))
                       ).grid(row=2 + offRow, column=0, sticky="nsew", padx=2, pady=2)

                eps = getEpisodes(folder)
                if len(eps) >= 1 and list(eps)[0] is not None:
                    titles = [e['title'] for e in eps]
                    state = "normal"
                else:
                    titles = (None,)
                    state = "disabled"

                var = StringVar()
                var.set("Watch")
                epsList = OptionMenu(
                    titleFrame, var, *titles, command=lambda e, var=var: watch(e, eps, var))
                epsList.configure(state=state, indicatoron=False, highlightthickness=0, borderwidth=0, font=("Source Code Pro Medium", 13),
                                  activebackground=self.colors['Gray3'], activeforeground=self.colors['White'], bg=self.colors['Gray3'], fg=self.colors['White'])
                epsList["menu"].configure(bd=0, borderwidth=0, activeborderwidth=0, font=("Source Code Pro Medium", 13),
                                          activebackground=self.colors['Gray3'], activeforeground=self.colors['White'], bg=self.colors['Gray2'], fg=self.colors['White'],)
                epsList.grid(row=2 + offRow, column=1,
                             sticky="nsew", padx=2, pady=2)
                epsList.bind("<Button-3>", lambda e,
                             var=var: openEps(e, eps, var))

                last_seen = anime.last_seen
                if len(eps) >= 1 and list(eps)[0] is not None:
                    pathList = [os.path.normpath(i['path']) for i in eps]
                else:
                    pathList = []
                if last_seen is not None and os.path.normpath(
                        last_seen) in pathList:
                    for i in range(pathList.index(
                            os.path.normpath(last_seen)) + 1):
                        epsList['menu'].entryconfig(
                            i, foreground=self.colors['Green'])

            [titleFrame.grid_columnconfigure(i, weight=1) for i in range(2)]

            if self.database(id=id, table='like').exist() and bool(
                    self.database(id=id, table='like')['like']):
                im = Image.open(os.path.join(self.iconPath, "heart.png"))
            else:
                im = Image.open(os.path.join(self.iconPath, "heart(1).png"))
            iconSize = (50, 50) if showFolderButtons else (30, 30)
            im = im.resize(iconSize)
            image = ImageTk.PhotoImage(im)
            likeButton = Button(titleFrame, image=image, bd=0, relief='solid',
                                activebackground=self.colors['Gray2'], activeforeground=self.colors[
                                    'White'], bg=self.colors['Gray2'], fg=self.colors['White'],
                                )
            likeButton.configure(command=lambda id=id,
                                 b=likeButton: like(id, b))
            likeButton.image = image
            likeButton.grid(row=1 + offRow, column=2,
                            rowspan=2, sticky="nsew", padx=5)
            titleFrame.grid(row=0, column=0, sticky="nsew")

        # Tags
        if True:
            tags = Frame(self.choice, bg=self.colors['Gray2'])
            Label(tags, text="Tag as:", bg=self.colors['Gray2'], fg=self.colors['Gray4'], font=(
                "Source Code Pro Medium", 15)).grid(row=0, column=0, pady=10)
            Button(tags, text="Seen", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'Green'], bg=self.colors['Gray2'], fg=self.colors['Green'],
                   command=lambda id=id: tag(id, 'SEEN')
                   ).grid(row=0, column=1, sticky="nsew", padx=5)
            Button(tags, text="Watching", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'Orange'], bg=self.colors['Gray2'], fg=self.colors['Orange'],
                   command=lambda id=id: tag(id, 'WATCHING')
                   ).grid(row=0, column=2, sticky="nsew", padx=5)
            Button(tags, text="To the Watchlist", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'White'], bg=self.colors['Gray2'], fg=self.colors['Blue'],
                   command=lambda id=id: tag(id, 'WATCHLIST')
                   ).grid(row=0, column=3, sticky="nsew", padx=5)
            Button(tags, text="None", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'White'], bg=self.colors['Gray2'], fg=self.colors['White'],
                   command=lambda id=id: tag(id, 'NONE')
                   ).grid(row=0, column=4, sticky="nsew", padx=5)
            if anime.trailer is not None:
                Label(tags, text="-", bg=self.colors['Gray2'], fg=self.colors['Gray4'], font=(
                    "Source Code Pro Medium", 13)).grid(row=0, column=5, pady=5)
                Button(tags, text="Watch trailer", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                       activebackground=self.colors['Gray2'], activeforeground=self.colors[
                           'White'], bg=self.colors['Gray2'], fg=self.colors['White'],
                       command=lambda id=id: trailer(id)
                       ).grid(row=0, column=6, sticky="nsew", padx=5)
            tags.grid(row=3, column=0)

        # Synopsis
        if True:
            if anime.synopsis not in ('', None):
                synopsis = Label(self.choice, text=anime.synopsis, wraplength=900, font=(
                    "Source Code Pro Medium", 10), bg=self.colors['Gray2'], fg=self.colors['White'])
            else:
                synopsis = Label(self.choice, text="No synopsis", wraplength=900, font=(
                    "Source Code Pro Medium", 10), bg=self.colors['Gray2'], fg=self.colors['White'])
            synopsis.grid(row=4, column=0)

        # Secondary infos
        if True:
            secondInfos = Frame(self.choice, bg=self.colors['Gray2'])
            if anime.episodes is not None:
                text = str(anime.episodes) + \
                    " episode{}".format("s" if anime.episodes > 1 else "")
                episodes = Label(secondInfos, text=text, font=(
                    "Source Code Pro Medium", 10), bg=self.colors['Gray2'], fg=self.colors['White'])
            else:
                episodes = Label(secondInfos, text="No episodes", font=(
                    "Source Code Pro Medium", 10), bg=self.colors['Gray2'], fg=self.colors['White'])
            if anime.rating is not None and anime.rating != 'None':
                rating = Label(secondInfos, text="Rating: " + anime.rating, font=(
                    "Source Code Pro Medium", 10), bg=self.colors['Gray2'], fg=self.colors['White'])
            else:
                rating = Label(secondInfos, text="No rating", font=(
                    "Source Code Pro Medium", 10), bg=self.colors['Gray2'], fg=self.colors['White'])
            if not anime.duration in (None, 'None', 'Unknown'):
                text = "(" + str(anime.duration) + " min{})".format(
                    " each" if anime.episodes is not None and anime.episodes > 1 else "")
                duration = Label(secondInfos, text=text, font=(
                    "Source Code Pro Medium", 10), bg=self.colors['Gray2'], fg=self.colors['White'])
            else:
                duration = Label(secondInfos, text="(Unknown duration)", font=(
                    "Source Code Pro Medium", 10), bg=self.colors['Gray2'], fg=self.colors['White'])

            rating.grid(row=0, column=0)
            Label(secondInfos, text="-", font=("Source Code Pro Medium", 10),
                  bg=self.colors['Gray2'], fg=self.colors['White']).grid(row=0, column=1)
            episodes.grid(row=0, column=2)
            duration.grid(row=0, column=3)
            secondInfos.grid(row=5, column=0)

        # Genres
        if True:
            genresFrame = Frame(self.choice, bg=self.colors['Gray2'])
            genres = anime.genres
            if genres is not None:
                genres = json.loads(anime.genres)
            else:
                genres = []

            for genre_id in genres:
                # values = self.database.sql("SELECT name FROM genres WHERE id=?",(genre_id,))
                # if len(values) >= 1:
                # 	txt = values[0][0]
                # else:
                # 	txt = "Unknown"
                # 	self.log("DB_ERROR","Unknown genre for id",genre_id,"on key",key)
                txt = self.database(id=genre_id, table="genres")["name"]
                if txt == "NONE":
                    txt = "Unknown"
                Label(genresFrame, text=txt, bd=0, height=1, font=("Source Code Pro Medium", 13),
                      bg=self.colors['Gray2'], fg=self.colors['Gray'],).pack(side="left")
                lbl = Label(genresFrame, text=" - ", bd=0, height=1, font=("Source Code Pro Medium", 13),
                            bg=self.colors['Gray2'], fg=self.colors['Gray'],)
                lbl.pack(side="left")
            if len(genres) >= 1:
                lbl.pack_forget()
            genresFrame.grid(row=6, column=0, pady=10)

        # Relations
        if True:
            relationsFrame = Frame(self.choice, bg=self.colors['Gray2'])
            relations = self.database.sql(
                "SELECT * FROM related WHERE id=?", (id,))
            column = 0
            relations.sort(key=itemgetter(1))
            for relation in relations:
                rel_ids = json.loads(relation[2])
                sql = "SELECT title,id FROM anime WHERE id IN (?" + ",?" * (
                    len(rel_ids) - 1) + ");"
                # sql = sql.format()
                titles = dict(self.database.sql(sql, rel_ids, iterate=True))
                text = relation[1].capitalize().replace("_", " ")
                if len(titles) == 1:
                    Button(relationsFrame, text=text, bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                           activebackground=self.colors['Gray2'], activeforeground=self.colors['Red'], bg=self.colors['Gray2'],
                           fg=self.colors[self.tagcolors[self.database(
                               id=rel_ids[0]).setTable('tag')['tag']]],
                           command=lambda ids=rel_ids: switch(ids[0])
                           ).grid(row=0, column=column)
                elif len(titles) > 1:
                    var = StringVar()
                    var.set(text)
                    # if len(titles) == 1:
                    epsList = OptionMenu(
                        relationsFrame, var, *titles.keys(), command=lambda e, titles=titles: switch(e, titles))
                    epsList.configure(indicatoron=False, highlightthickness=0, borderwidth=0, font=("Source Code Pro Medium", 13),
                                      activebackground=self.colors['Gray2'], activeforeground=self.colors['White'], bg=self.colors['Gray2'], fg=self.colors['White'])
                    epsList["menu"].configure(bd=0, borderwidth=0, activeborderwidth=0, font=("Source Code Pro Medium", 13),
                                              activebackground=self.colors['Gray3'], activeforeground=self.colors['White'], bg=self.colors['Gray2'], fg=self.colors['White'],)
                    epsList.grid(row=0, column=column)

                    for i, rel_id in enumerate(rel_ids):
                        epsList['menu'].entryconfig(
                            i, foreground=self.colors[self.tagcolors[self.database(id=rel_id).setTable('tag')['tag']]])
                else:
                    self.log("ERROR", "id:{}, rel_ids:{}, titles:{}".format(
                        str(id), str(rel_ids), str(titles)))
                    # raise Exception("ERROR - id:{}, rel_ids:{}, titles:{}".format(str(id),str(rel_ids),str(titles)))

                if len(titles) > 0:
                    column += 1
                    lbl = Label(relationsFrame, text="-", bd=0, height=1, font=("Source Code Pro Medium", 13),
                                bg=self.colors['Gray2'], fg=self.colors['Gray'],)
                    lbl.grid(row=0, column=column)
                    column += 1

            if column > 0:
                lbl.grid_forget()

            relationsFrame.grid(row=7, column=0)

        # State
        if True:
            state = Frame(self.choice, bg=self.colors['Gray2'])
            datefrom, dateto = anime.date_from, anime.date_to
            if datefrom is not None:
                datefrom = date.fromisoformat(datefrom)
            if dateto is not None:
                dateto = date.fromisoformat(dateto)

            status = self.getStatus(anime)
            Label(state, text="Status:", bg=self.colors['Gray2'], fg=self.colors['Gray4'], font=(
                "Source Code Pro Medium", 15)).grid(row=0, column=0, sticky="e")
            statusLbl = Label(state, text=self.dateStates[status]['text'], bg=self.colors['Gray2'],
                              fg=self.colors[self.dateStates[status]['color']], font=("Source Code Pro Medium", 13))
            statusLbl.grid(row=0, column=1, sticky="w")
            dateLbl = Label(state, text="", bg=self.colors['Gray2'], fg=self.colors[self.dateStates[status]['color']], font=(
                "Source Code Pro Medium", 13))
            if status != 'UNKNOWN' and datefrom is not None:
                dateLbl['text'] = getDateText(
                    datefrom, dateto, anime.broadcast)
                dateLbl.grid(row=1, column=0, columnspan=2)
            state.grid(row=8, column=0)

        # Actions
        if True:
            actions = Frame(self.choice, bg=self.colors['Gray2'])
            for i, data in enumerate(self.actionButtons):
                Button(actions, text=data['text'], bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                       activebackground=self.colors['Gray2'], activeforeground=self.colors[data['color']
                                                                                           ], bg=self.colors['Gray2'], fg=self.colors[data['color']],
                       command=lambda c=data['command'], id=id: c(id)
                       ).grid(row=0, column=i * 2)
                if i < len(self.actionButtons) - 1:
                    Label(actions, text="-", bd=0, height=1, font=("Source Code Pro Medium", 13),
                          bg=self.colors['Gray2'], fg=self.colors['Gray'],
                          ).grid(row=0, column=i * 2 + 1)

            actions.grid(row=9, column=0)

        self.choice.update()
        if not 'hash' in self.choice.__dict__.keys():
            threading.Thread(target=findTorrent, args=(id,)).start()

    def ddlWindow(self, id):
        # Window init - Fancy corners - Main frame - Events
        if True:
            size = (self.publisherDDLWindowMinWidth,
                    self.publisherDDLWindowMinHeight)
            if self.publisherChooser is None or not self.publisherChooser.winfo_exists():
                self.publisherChooser = utils.RoundTopLevel(
                    self.choice, title="Loading...", minsize=size, bg=self.colors['Gray3'], fg=self.colors['Gray2'])
            else:
                self.publisherChooser.clear()
                self.publisherChooser.titleLbl.configure(
                    text="Loading...", bg=self.colors['Gray3'], fg=self.colors['Gray2'], font=("Source Code Pro Medium", 18))

            table = utils.ScrollableFrame(
                self.publisherChooser, bg=self.colors['Gray3'])
            table.grid_columnconfigure(0, weight=1)
            table.grid()

            self.publisherChooser.update()
            if not self.publisherChooser.winfo_exists():
                return

        # Torrent publisher list
        if True:
            self.log("FILE_SEARCH", "Looking files for id:", id)
            titles = self.searchTorrents(id)
            # titles = self.getTorrentFiles(title)
            rowHeight = 25
            empty = True

            for i, data in enumerate(titles):
                if empty:
                    empty = False
                publisher, data = data
                marked = ('dual', 'dub')
                for title in [d['filename'] for d in data]:
                    fg = self.getTorrentColor(title)
                    if fg != self.colors['White']:
                        break
                bg = (self.colors['Gray2'], self.colors['Gray3'])[i % 2]
                if publisher is None:
                    publisher = 'None'
                if not self.publisherChooser.winfo_exists():
                    return
                Button(table, text=publisher, bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                       activebackground=self.colors['Gray3'], activeforeground=fg, bg=bg, fg=fg,
                       command=lambda a=data, b=id: self.ddlFileListWindow(
                           a, b)
                       ).grid(row=i, column=0, sticky="nsew")

            try:
                if empty:
                    self.publisherChooser.titleLbl['text'] = "No files\nfound!"
                else:
                    self.publisherChooser.titleLbl['text'] = "Publisher:"
            except _tkinter.TclError:
                pass

            table.update()
            # self.publisherChooser.update()

    def ddlFileListWindow(self, data, id):
        # Function
        def startDownload(labels, url, id):
            self.downloadFile(id, url=url)
            for label in labels:
                try:
                    label.configure(fg=self.colors['Blue'])
                except BaseException:
                    pass

        # Window init - Fancy corners - Main frame - Events
        if True:
            size = (self.torrentDDLWindowMinWidth,
                    self.torrentDDLWindowMinHeight)
            if self.fileChooser is None or not self.fileChooser.winfo_exists():
                self.fileChooser = utils.RoundTopLevel(
                    self.publisherChooser, title="Torrents:", minsize=size, bg=self.colors['Gray2'], fg=self.colors['Gray3'])
            else:
                self.fileChooser.clear()
                # self.fileChooser.titleLbl.configure(text="Torrents:", bg= self.colors['Gray3'], fg= self.colors['Gray2'], font=("Source Code Pro Medium",18))

            table = utils.ScrollableFrame(
                self.fileChooser, bg=self.colors['Gray2'])
            table.pack(expand=True, fill="both", padx=20)

            table.grid_columnconfigure(0, weight=1)

            self.fileChooser.update()

        # Torrent list
        if True:
            maxTitleLength = len(
                sorted((d['filename'] for d in data), key=len, reverse=True)[0])
            maxSizeLength = len(
                str(sorted((d['file_size'] for d in data), reverse=True)[0]))

            for row, d in enumerate(data):
                title = d['filename']
                fg = self.getTorrentColor(title)
                # title = d['name'].ljust(maxLength) + "-" + d['size']
                bg = (self.colors['Gray3'], self.colors['Gray2'])[row % 2]
                titleLbl = Label(table, text=title.ljust(maxTitleLength), font=("Source Code Pro Medium", 13), bg=bg, fg=fg
                                 )
                titleLbl.grid(row=row, column=0, sticky="nsew")

                seedsLbl = Label(table, text=(str(d['seeds']) + "▲").rjust(5) + "   ", font=("Source Code Pro Medium", 13), bg=bg, fg=fg
                                 )
                seedsLbl.grid(row=row, column=1, sticky="nsew")
                leechsLbl = Label(table, text=(str(d['leechs']) + "▼").rjust(5) + "   ", font=("Source Code Pro Medium", 13), bg=bg, fg=fg
                                  )
                leechsLbl.grid(row=row, column=2, sticky="nsew")
                sizeLbl = Label(table, text=str(d['file_size']).rjust(maxSizeLength), font=("Source Code Pro Medium", 13), bg=bg, fg=fg
                                )
                sizeLbl.grid(row=row, column=3, sticky="nsew")

                command = lambda e, labels=(
                    titleLbl, sizeLbl, seedsLbl, leechsLbl), url=d['torrent_url'], id=id: startDownload(labels, url, id)
                titleLbl.bind("<Button-1>", command)
                seedsLbl.bind("<Button-1>", command)
                leechsLbl.bind("<Button-1>", command)
                sizeLbl.bind("<Button-1>", command)
                # Label(table, text=d['seeders'], font=("Source Code Pro Medium",13), bg=bg, fg=self.colors['White']
                # 	).grid(row=row,column=2,sticky="nsew")
            table.update()
            self.fileChooser.update()

    def textPopupWindow(self, parent, title, callback, fentype="TEXT"):
        # Main window
        if True:
            self.popupWindow = utils.RoundTopLevel(parent, title=title, minsize=(
                750, 150), bg=self.colors['Gray2'], fg=self.colors['Gray3'])
            # self.popupWindow.titleLbl.configure(text=title, bg= self.colors['Gray2'], fg= self.colors['Gray3'], font=("Source Code Pro Medium",18))
            self.popupWindow.fen.attributes('-topmost', 'true')

        if fentype == "TEXT":
            var = StringVar()
            e = Entry(self.popupWindow, textvariable=var, highlightthickness=0,
                      borderwidth=0, font=("Source Code Pro Medium", 13), bg=self.colors['Gray3'], fg=self.colors['White'])
            e.bind("<Return>", lambda e, var=var: callback(var))
            e.grid(row=0, column=0, sticky="nsew", padx=5, pady=(0, 20))
            self.popupWindow.handles.append(e)
            Button(self.popupWindow, text="Ok", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'Gray3'], bg=self.colors['Gray3'], fg=self.colors['Gray2'],
                   command=lambda var=var: callback(var)).grid(row=0, column=1, sticky="nsew", pady=(0, 20))
        else:
            self.log("ERROR", "Unknown window type", fentype)
            raise Exception

    def seasonSelector(self):
        # Window init
        if True:
            size = (self.seasonChooserMinWidth, self.seasonChooserMinHeight)
            self.seasonChooser = utils.RoundTopLevel(
                self.fen, title="Season selector", minsize=size, bg=self.colors['Gray3'], fg=self.colors['Gray2'])
            self.seasonChooser.titleLbl.configure(
                text="Season selector", bg=self.colors['Gray3'], fg=self.colors['Gray2'], font=("Source Code Pro Medium", 18))
            self.season_ids = []

            table = utils.ScrollableFrame(
                self.seasonChooser, bg=self.colors['Gray2'])
            table.pack(expand=True, fill="both", padx=20)

            [table.grid_columnconfigure(i, weight=1) for i in range(5)]
            # table.grid_columnconfigure(0,weight=1)

            self.seasonChooser.update()

        # Table init
        if True:
            today = date.today()
            currentYear, currentMonth = today.year, today.month
            startYear = currentYear + 5
            stopYear = 1920
            for i, year in enumerate(range(startYear, stopYear, -1)):
                fg = self.colors['White' if year <= currentYear else 'Blue']
                bg = self.colors['Gray2' if i % 2 == 0 else 'Gray3']
                Label(table, text=str(year), bg=bg, fg=fg, font=("Source Code Pro Medium", 18)
                      ).grid(row=i, column=0, sticky="nsew")
                for j, season in enumerate(self.seasons.keys()):
                    if year == currentYear:
                        if self.seasons[season]['start'] > currentMonth:
                            fg = self.colors['Blue']
                        else:
                            fg = self.colors['White']

                    cell = Button(table, text=season.capitalize(), bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 15),
                                  activebackground=self.colors['Gray2'], activeforeground=self.colors['White'], bg=bg, fg=fg,
                                  command=lambda y=year, s=season: self.getSeason(y, s))
                    cell.grid(row=i, column=j + 1, sticky="nsew")

        table.update()
        self.seasonChooser.update()

    def characterListWindow(self, id, update=True):
        # Functions
        if True:
            def characterCell(character, index, queue):
                if threading.main_thread() == threading.current_thread():
                    database = self.database
                else:
                    database = db(self.dbPath)

                size = (225, 310)
                cell = Frame(self.characterListTable, bg=self.colors['Gray3'])
                cell.grid_rowconfigure(0, weight=1)
                cell.grid_columnconfigure(0, weight=1)

                can = Canvas(
                    cell, width=size[0], height=size[1], highlightthickness=0, bg=self.colors['Gray3'])
                can.grid(row=0, column=0, sticky="ns")
                can.bind("<Button-1>", lambda e,
                         a=character: self.characterWindow(a))

                filename = os.path.join(
                    self.cache, "c" + str(character['id']) + ".jpg")

                if "c" + str(character['id']) + \
                        ".jpg" in os.listdir(self.cache):
                    im = Image.open(filename)
                    loadImg = False
                else:
                    im = Image.new('RGB', (225, 310), self.colors['Gray'])
                    loadImg = True
                    self.log('DISK_ERROR', "[ERROR] - Can't open image for character",
                             character['name'], "id", character['id'])

                # im.resize(size)
                image = ImageTk.PhotoImage(im)
                can.create_image(size[0] / 2, size[1] / 2,
                                 image=image, anchor='center')
                can.image = image

                title = character['name']
                if len(title) >= 20:
                    title = title[:15] + "..."
                if database(id=character['id'], table='characters').exist() and bool(
                        database['like']):
                    title += " ❤"
                color = 'Blue' if character['role'] == 'main' else 'White'
                b = Button(cell, text=title, bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                           activebackground=self.colors['Gray2'], activeforeground=self.colors[
                               color], bg=self.colors['Gray3'], fg=self.colors[color],
                           command=lambda a=character: self.characterWindow(a))
                b.name = character['id']
                b.grid(row=1, column=0, sticky="nsew")

                x, y = index // self.animePerRow, index % self.animePerRow
                cell.grid(row=x, column=y, sticky="nsew", pady=2, padx=2)

                if loadImg:
                    queue.put((filename, character, can))
                    # threading.Thread(target=downloadPic,args=(filename,character,can)).start()

            def getImages(queue):
                def downloadPic(filename, character, can):
                    if character['picture'] is None:
                        return
                    self.log("NETWORK", "Requesting picture for character id",
                             character['id'], "name", character["name"])
                    raw_data = requests.get(character['picture']).content
                    im = Image.open(io.BytesIO(raw_data))
                    im = im.resize((225, 310))
                    if im.mode != 'RGB':
                        im = im.convert('RGB')
                    im.save(filename)

                    image = ImageTk.PhotoImage(im, master=self.characterList)
                    try:
                        can.create_image(0, 0, image=image, anchor='nw')
                        can.image = image
                    except BaseException:
                        pass

                while True:
                    if queue.empty():
                        time.sleep(0.01)
                    else:
                        args = queue.get()
                        if args == "STOP":
                            break
                        downloadPic(*args)

            def getCharacters(id):
                database = self.getDatabase()
                if id == "LIKED":
                    characters = database.sql("""
						SELECT * FROM characters
						WHERE like = 1
						GROUP BY id
						ORDER BY anime_id;""")
                else:
                    characters = database.sql(
                        "SELECT * FROM characters WHERE anime_id=?;", (id,))
                return characters

            def reload(id, c):
                if getCharacters(id) != c:
                    self.characterList.after(
                        1, lambda id=id: self.characterListWindow(id, False))

            def update(id):
                self.getCharactersData(id)
                parent.after(1, lambda id=id: characterListWindow(id))

        # Main window - Fancy corners - Events
        if True:
            size = (self.characterListWindowMinWidth,
                    self.characterListWindowMinHeight)
            if self.choice is not None and self.choice.winfo_exists():
                parent = self.choice
            else:
                parent = self.fen

            if self.characterList is None or not self.characterList.winfo_exists():
                self.characterList = utils.RoundTopLevel(
                    parent, title="Characters", minsize=size, bg=self.colors['Gray3'], fg=self.colors['Gray2'])
            else:
                self.characterList.clear()
            # self.characterList.titleLbl.configure(text="Characters", bg= self.colors['Gray3'], fg= self.colors['Gray2'], font=("Source Code Pro Medium",18))

            self.characterListTable = utils.ScrollableFrame(
                self.characterList, bg=self.colors['Gray3'])
            self.characterListTable.pack(expand=True, fill="both")

            self.characterListTable.grid_columnconfigure(0, weight=1)

            self.characterList.update()

        # Data check
        if True:
            sql = "SELECT EXISTS(SELECT 1 FROM characters WHERE anime_id = ?);"
            empty = not bool(self.database.sql(sql, (id,))[0][0])
            if id != "LIKED" and empty:
                loadLbl = Label(self.characterListTable, text="Loading data...",
                                bg=self.colors['Gray3'], fg=self.colors['Gray2'], font=("Source Code Pro Medium", 18))
                loadLbl.pack(fill="both", expand=True, pady=10, side=BOTTOM)
                thread = threading.Thread(
                    target=self.getCharactersData, args=(id,))
                thread.start()
                while thread.is_alive():
                    self.root.update()
                    time.sleep(0.01)
                loadLbl.destroy()

        # Characters list
        if True:
            characters = getCharacters(id)

            # if update:
            # 	thread = threading.Thread(target=self.getCharactersData, args=(id,lambda id=id,c=characters:reload(id,c)))
            # 	thread.start()

            maxX = len(characters) // self.animePerRow
            [self.characterListTable.grid_rowconfigure(
                x, weight=1) for x in range(maxX)]
            # [self.characterListTable.grid_columnconfigure(y,weight=1) for y in range(max(len(characters),self.animePerRow))]

            for x in range(min(len(characters), self.animePerRow)):
                self.characterListTable.grid_columnconfigure(x, weight=1)
                # Frame(self.characterListTable,bg=self.colors['Gray3']).grid(row=0,column=x,sticky="nsew")

            que = queue.Queue()
            keys = ('id', 'anime_id', 'name', 'role', 'picture', 'desc')

            thread = threading.Thread(target=getImages, args=(que,))
            thread.start()

            for index, data in enumerate(characters):
                if self.characterList is None:
                    break

                character = dict(zip(keys, data))
                try:
                    characterCell(character, index, que)
                    self.characterListTable.update()
                except BaseException:
                    pass

            que.put("STOP")
            while not que.empty() and self.characterList is not None and self.characterList.winfo_exists():
                self.characterList.update()
                time.sleep(0.01)

            if self.characterListTable.winfo_exists():
                self.characterListTable.grid_columnconfigure(0, weight=1)
                if len(characters) == 0:
                    Label(self.characterListTable, text="No characters", font=("Source Code Pro Medium", 13), bg=self.colors['Gray3'], fg=self.colors['Red'],
                          ).grid(row=0, column=0, sticky="nsew", pady=2, padx=2)
                self.characterListTable.update()

    def characterWindow(self, character, update=True):
        # Functions
        if True:
            def like(id, b):
                d = self.database(id=id, table='characters')
                liked = d.exist() and bool(d['like'])
                d.set({'id': id, 'like': not liked})

                if not liked:
                    im = Image.open(os.path.join(self.iconPath, "heart.png"))
                else:
                    im = Image.open(os.path.join(
                        self.iconPath, "heart(1).png"))

                iconSize = (30, 30)
                im = im.resize(iconSize)
                image = ImageTk.PhotoImage(im)
                b.configure(image=image)
                b.image = image
                b.update()

                for but in self.characterListTable.winfo_children():
                    if but.winfo_class() == 'Button' and but.name == id:
                        text = but.cget("text").replace(" ❤", "")
                        if not liked:
                            text += " ❤"
                        but['text'] = text
                        but.update()
                        break

            def switchAnime(id):
                try:
                    self.characterInfo.exit()
                except BaseException:
                    pass
                try:
                    self.characterList.exit()
                except BaseException:
                    pass
                try:
                    self.reload(id, False)
                except BaseException:
                    self.optionsWindow(id)

            def update(c):
                c = self.getCharacterData(c['id'])
                try:
                    self.characterInfo.after(
                        1, lambda c=c: self.characterWindow(c, update=False))
                except BaseException:
                    pass

        # Main window - Fancy corners - Events
        if True:
            size = (self.characterInfoWindowMinWidth,
                    self.characterInfoWindowMinHeight)
            if self.characterInfo is None or not self.characterInfo.winfo_exists():
                self.characterInfo = utils.RoundTopLevel(
                    self.characterList, title="Loading data...", minsize=size, bg=self.colors['Gray2'], fg=self.colors['Gray3'])
            else:
                self.characterInfo.clear()
            self.characterInfo.grid_rowconfigure(1, weight=1)
            self.characterInfo.grid_columnconfigure(1, minsize=250, weight=1)

        # Data check
        if True:
            if not 'desc' in character.keys() or character['desc'] is None:
                # self.characterInfo.titleLbl.configure(text="Loading data...", bg= self.colors['Gray2'], fg= self.colors['Gray3'], font=("Source Code Pro Medium",18))

                # thread = threading.Thread(target=self.getCharacterData, args=(character['id'],))
                # thread.start()
                # while thread.is_alive():
                # 	self.characterInfo.update()
                # 	time.sleep(0.01)

                if update:
                    thread = threading.Thread(target=update, args=(character,))
                    thread.start()

                data = self.database.sql(
                    "SELECT * FROM characters WHERE anime_id=? AND id=?;", (character['anime_id'], character['id']))[0]
                keys = ('id', 'anime_id', 'name', 'role', 'picture', 'desc')
                # character = {key:(json.loads(data[i]) if type(data[i]) == str else data[i]) for i,key in enumerate(keys)}
                character['desc'] = data[5]

        # Picture
        if True:
            filename = os.path.join(
                self.cache, "c" + str(character['id']) + ".jpg")

            if "c" + str(character['id']) + ".jpg" in os.listdir(self.cache):
                im = Image.open(filename)
            else:
                raw_data = requests.get(character['picture']).content
                im = Image.open(io.BytesIO(raw_data))
                im = im.resize((225, 310))
                if im.mode != 'RGB':
                    im = im.convert('RGB')
                im.save(filename)

            image = ImageTk.PhotoImage(im)

            try:
                can = Canvas(self.characterInfo, width=225, height=310,
                             highlightthickness=0, bg=self.colors['Gray3'])
                can.grid(row=0, column=0, rowspan=2)
                can.create_image(0, 0, image=image, anchor='nw')
                can.image = image
            except BaseException:
                try:
                    self.characterInfo.exit()
                except BaseException:
                    pass

        # Title panel
        if True:
            self.characterInfo.titleFrame.destroy()
            titleFrame = Frame(self.characterInfo, bg=self.colors['Gray2'])
            titleFrame.grid_columnconfigure(0, weight=1)

            titleLbl = Label(titleFrame, text=character['name'], wraplength=500, bg=self.colors['Gray2'], font=("Source Code Pro Medium", 18),
                             fg=self.colors['Blue' if character['role'] == "Main" else 'White'])
            titleLbl.grid(row=0, column=0, sticky="nsew", columnspan=2)
            self.characterInfo.titleLbl = titleLbl
            self.characterInfo.handles = [titleLbl]
            self.characterInfo.update()

            if self.database(id=character['id'], table='characters').exist() and bool(
                    self.database['like']):
                im = Image.open(os.path.join(self.iconPath, "heart.png"))
            else:
                im = Image.open(os.path.join(self.iconPath, "heart(1).png"))
            iconSize = (30, 30)
            im = im.resize(iconSize)
            image = ImageTk.PhotoImage(im)

            Button(titleFrame, text="Go to anime", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'White'], bg=self.colors['Gray3'], fg=self.colors['White'],
                   command=lambda id=character['anime_id']: switchAnime(id)
                   ).grid(row=1, column=0, sticky="nsew", padx=(20, 0))

            likeButton = Button(titleFrame, image=image, bd=0, relief='solid',
                                activebackground=self.colors['Gray2'], activeforeground=self.colors['White'], bg=self.colors['Gray2'], fg=self.colors['White'],)
            likeButton.configure(
                command=lambda id=character['id'], b=likeButton: like(id, b))
            likeButton.image = image
            likeButton.grid(row=1, column=1, sticky="nsew", padx=5)

            titleFrame.grid(row=0, column=1, sticky="nsew")

        # Info panel
        if True:
            infoFrame = Frame(self.characterInfo, bg=self.colors['Gray2'])

            if 'desc' in character.keys() and character['desc'] is not None:
                desc = "\n".join(re.findall(
                    r'([^\n]{1,40}\S+)|[\n]+', character['desc'], re.M))
                lines = len(desc.split("\n"))
                if lines > 50:
                    Label(infoFrame, text="\n".join(desc.split("\n")[:lines // 2]), wraplength=800, font=("Source Code Pro Medium", 10), bg=self.colors['Gray2'],
                          fg=self.colors['White']).grid(row=0, column=0, sticky="n")
                    Frame(infoFrame, width=2, bg=self.colors['Gray4']).grid(
                        row=0, column=1, sticky="ns", padx=10)
                    Label(infoFrame, text="\n".join(desc.split("\n")[lines // 2:]), wraplength=800, font=("Source Code Pro Medium", 10), bg=self.colors['Gray2'],
                          fg=self.colors['White']).grid(row=0, column=2, sticky="n")
                else:
                    Label(infoFrame, text=desc, wraplength=500, font=("Source Code Pro Medium", 10), bg=self.colors['Gray2'],
                          fg=self.colors['White']).grid(row=0, column=0)
            else:
                if update:
                    Label(infoFrame, text="Loading...", font=("Source Code Pro Medium", 10), bg=self.colors['Gray2'],
                          fg=self.colors['White']).grid(row=0, column=0)

                else:
                    Label(infoFrame, text="No description", font=("Source Code Pro Medium", 10), bg=self.colors['Gray2'],
                          fg=self.colors['White']).grid(row=0, column=0)
            # desc
            # infoFrame.grid_rowconfigure(0,weight=1)
            infoFrame.grid_columnconfigure(0, weight=1)
            infoFrame.grid(row=1, column=1, sticky="nsew",
                           padx=(20, 0), pady=(10, 0))

            self.characterInfo.update()

    def loadingWindow(self):
        if self.root is None:
            self.loadfen = Tk()
        else:
            self.loadfen = Toplevel(self.root)

        self.loadfen.geometry("920x500+{}+{}".format(100, 100))
        self.loadfen.configure(bg=self.colors['Gray3'])
        self.loadfen.title("Nyaa.si - Custom Browser - Loading...")
        self.loadfen.wm_iconphoto(False, ImageTk.PhotoImage(Image.open(
            os.path.join(self.iconPath, 'favicon.png')), master=self.loadfen))

        main = Frame(self.loadfen, width=920, bg=self.colors['Gray2'])
        for i in range(2):
            main.grid_rowconfigure(i, weight=1)
        main.grid_columnconfigure(0, weight=1)

        Label(main, text="Loading...", bg=self.colors['Gray2'], fg=self.colors['Gray4'], font=(
            "Source Code Pro Medium", 20)).grid(row=0, column=0, sticky="s")
        self.loadLabel = Label(
            main, text="-/-, -:-", bg=self.colors['Gray2'], fg=self.colors['Gray4'], font=("Source Code Pro Medium", 20))
        self.loadLabel.grid(row=1, column=0, sticky="n")
        main.pack(fill="both", expand=True)

        self.loadProgress = Progressbar(
            self.loadfen, orient=HORIZONTAL, length=500, mode='determinate')
        self.loadProgress.pack(side="bottom", padx=10, pady=10)

        self.loadfen.update()

    def diskWindow(self):
        # Functions
        if True:
            def getFiles(folder):
                files, folders = [], []
                for f in os.listdir(folder):
                    if os.path.isfile(folder + "/" + f):
                        files.append(f)
                    else:
                        if f != "Torrents":
                            folders.append(f)
                            a, b = getFiles(folder + "/" + f)
                            files += a
                            folders += b
                return files, folders

            def exit(e=None):
                self.diskfen.destroy()

        # Window init - Fancy corners - Events
        if True:
            disk = self.animePath.split("/")[0]
            if self.diskfen is None or not self.diskfen.winfo_exists():
                size = (self.diskWindowMinWidth, self.diskWindowMinHeight)
                self.diskfen = utils.RoundTopLevel(
                    self.fen, title="Disk " + disk, minsize=size, bg=self.colors['Gray2'], fg=self.colors['Gray4'])
            else:
                self.diskfen.clear()
                self.diskfen.focus()

        # Bars
        if True:
            barFrame = Frame(self.diskfen, bg=self.colors['Gray2'])
            length = 500
            radius = 25
            usageColors = {75: 'Green', 90: 'Orange', 100: 'Red'}
            total, used, free = shutil.disk_usage(disk)
            usedSize = length * used / total
            usedPrct = used / total * 100
            for p, c in list(usageColors.items())[::-1]:
                if usedPrct < p:
                    color = c

            # self.diskfen.titleLbl.configure(text="Disk "+disk, font=("Source Code Pro Medium",20),
            # 		bg= self.colors['Gray2'], fg= self.colors['Gray4'],)

            bar = Canvas(
                barFrame, bg=self.colors['Gray2'], width=length, height=radius * 2, highlightthickness=0,)
            bar.create_line(radius, radius, length - radius, radius,
                            capstyle='round', fill=self.colors['Gray4'], width=radius)
            bar.create_line(radius, radius, usedSize - radius, radius,
                            capstyle='round', fill=self.colors[color], width=radius)
            bar.grid(row=1, column=0, columnspan=3)
            Label(barFrame, text="%d GB used" % (used // (2**30)), wraplength=900, font=("Source Code Pro Medium", 12), bg=self.colors['Gray2'], fg=self.colors['Gray4']
                  ).grid(row=2, column=0)
            Label(barFrame, text="%d GB total" % (total // (2**30)), wraplength=900, font=("Source Code Pro Medium", 12), bg=self.colors['Gray2'], fg=self.colors['Gray4']
                  ).grid(row=2, column=1)
            Label(barFrame, text="%d GB free" % (free // (2**30)), wraplength=900, font=("Source Code Pro Medium", 12), bg=self.colors['Gray2'], fg=self.colors['Gray4']
                  ).grid(row=2, column=2)
            barFrame.grid_columnconfigure(1, weight=1)
            barFrame.pack(pady=20)

        # Stats info
        if True:
            fileFrame = Frame(self.diskfen, bg=self.colors['Gray2'])
            t = Label(fileFrame, text="Animes folder:", wraplength=900, font=(
                "Source Code Pro Medium", 20), bg=self.colors['Gray2'], fg=self.colors['Gray4'])
            t.grid(row=0, column=0, columnspan=2)
            files, folders = getFiles(self.animePath)
            Label(fileFrame, text="%d files - %d folders" % (len(files), len(folders)), wraplength=900, font=("Source Code Pro Medium", 15), bg=self.colors['Gray2'], fg=self.colors['Gray4']
                  ).grid(row=1, column=0, sticky="nsew")
            # [fileFrame.grid_columnconfigure(i,weight=1) for i in range(2)]
            fileFrame.pack(pady=20)

        self.diskfen.update()

    def settingsWindow(self):
        # Functions
        if True:
            def exit(e=None):
                # Placeholder for code folding
                self.settings.destroy()
                self.settings = None
                self.fen.focus_force()

            def getDir(title, var, file=False):
                if not file:
                    path = askdirectory(
                        parent=self.root, title=title, initialdir=getattr(self, var))
                else:
                    path = askopenfilename(parent=self.root, title=title, initialdir=os.path.dirname(
                        getattr(self, var)), filetypes=[("Database", (".db"))])
                if path != "":
                    self.setSettings({var: path})
                    self.start = time.time()
                    self.initWindow()
                try:
                    self.settingsWindow()
                except BaseException:
                    pass

            def checkboxHandler(value, var):
                self.setSettings({var: bool(value.get())})
                self.settings.update()
                self.start = time.time()
                self.initWindow()

            def drawLogs(parent):
                for w in parent.winfo_children():
                    w.destroy()

                columns = 3
                [parent.grid_columnconfigure(i, weight=1)
                 for i in range(columns)]
                allLogs = sorted(
                    self.logs) + sorted((l for l in self.allLogs if l not in self.logs))
                for ind, log in enumerate(allLogs):
                    if log in self.logs:
                        color = "Green"
                    else:
                        color = "Red"
                    column = ind % columns
                    Button(parent, text=log, bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                           activebackground=self.colors['Gray2'], activeforeground=self.colors[
                               'White'], bg=self.colors['Gray3'], fg=self.colors[color],
                           command=lambda log=log, parent=parent: toggleLog(
                               log, parent)
                           ).grid(row=ind // columns, column=column, sticky="nsew", pady=2, padx=2)

            def toggleLog(log, parent):
                if log in self.logs:
                    self.logs.remove(log)
                else:
                    self.logs.append(log)

                self.setSettings({"logs": self.logs})
                drawLogs(parent)

            def updateServer(*values):
                for var, field in values:
                    value = var.get()
                    if field == "ADDRESS":
                        self.setSettings({"hostName": value})
                    elif field == "PORT":
                        self.setSettings({"serverPort": int(value)})
                    else:
                        raise Exception

                if self.enableServer:
                    utils.stopServer(self.server, self)
                    self.server = utils.startServer(
                        self.hostName, self.serverPort, self.dbPath, self)

            def updateTorrent(*values, entries=None):
                for var, field in values:
                    value = var.get()
                    if field == "ADDRESS":
                        self.setSettings({"torrentApiAddress": value})
                    elif field == "LOGIN":
                        self.setSettings({"torrentApiLogin": value})
                    elif field == "PASSWORD":
                        self.setSettings({"torrentApiPassword": value})
                    else:
                        raise Exception

                auth = self.getQB(reconnect=True)
                if entries is not None:
                    if auth == "ADDRESS":
                        colA, colC = 'Red', 'White'
                    elif auth == "CREDENTIALS":
                        colA, colC = 'Green', 'Red'
                    elif auth == "OK":
                        colA, colC = 'Green', 'Green'
                    entries['address'].configure(fg=colA)
                    entries['login'].configure(fg=colC)
                    entries['password'].configure(fg=colC)

        # Main window - Events - Fancy corners - Title
        if True:
            try:
                exist = self.settings.winfo_exists() and self.fen.winfo_exists()
            except BaseException:
                exist = False
            if self.settings is None or not exist:
                size = (self.settingsWindowMinWidth,
                        self.settingsWindowMinHeight)
                self.settings = utils.RoundTopLevel(
                    self.fen, title="Settings", minsize=size, bg=self.colors['Gray2'], fg=self.colors['Gray4'])
            else:
                self.settings.clear()
                self.settings.focus()
            # self.settings.titleLbl.configure(text="Settings", font=("Source Code Pro Medium",20),
            # 		bg= self.colors['Gray2'], fg= self.colors['Gray4'],)

        # Path update frame "iconPath","cache","path","torrentPath","dbPath"
        if True:
            pathFrame = Frame(self.settings, bg=self.colors['Gray2'])
            Button(pathFrame, text="Change anime folder", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'White'], bg=self.colors['Gray3'], fg=self.colors['White'],
                   command=lambda id=id: getDir(
                       "Choose anime folder", "animePath")
                   ).grid(row=0, column=0, sticky="nsew", pady=2, padx=2)

            Button(pathFrame, text="Change torrents folder", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'White'], bg=self.colors['Gray3'], fg=self.colors['White'],
                   command=lambda id=id: getDir(
                       "Choose torrents folder", "torrentPath")
                   ).grid(row=1, column=0, sticky="nsew", pady=2, padx=2)

            Button(pathFrame, text="Change cache folder", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'White'], bg=self.colors['Gray3'], fg=self.colors['White'],
                   command=lambda id=id: getDir("Choose cache folder", "cache")
                   ).grid(row=0, column=1, sticky="nsew", pady=2, padx=2)

            Button(pathFrame, text="Change database path", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'White'], bg=self.colors['Gray3'], fg=self.colors['White'],
                   command=lambda id=id: getDir(
                       "Choose database file", "dbPath", True)
                   ).grid(row=1, column=1, sticky="nsew", pady=2, padx=2)
            pathFrame.grid(row=1, column=0)
            [pathFrame.grid_columnconfigure(i, weight=1) for i in range(2)]

        # Checkboxe "hideRated"
        if True:
            checkboxFrame = Frame(self.settings, bg=self.colors['Gray2'])
            iconSize = (20, 20)
            no_check = self.getImage('./icons/no_check.png', iconSize)
            check = self.getImage('./icons/check.png', iconSize)
            ratedVar = IntVar()
            ratedVar.set(self.hideRated)
            ratedCB = Checkbutton(checkboxFrame, text=" Hide rated anime (R+/Rx)", bd=0, relief='solid',
                                  indicatoron=False, image=no_check, compound='left', selectimage=check, font=("Source Code Pro Medium", 13),
                                  activebackground=self.colors['Gray3'], activeforeground=self.colors[
                                      'White'], bg=self.colors['Gray2'], fg=self.colors['White'],
                                  selectcolor=self.colors['Gray2'], variable=ratedVar, command=lambda: checkboxHandler(ratedVar, "hideRated"))
            ratedCB.no_check = no_check
            ratedCB.check = check
            ratedCB.grid(row=0, column=0, sticky="nsew", pady=10)

            # [checkboxFrame.grid_rowconfigure(i,weight=1) for i in range(2)]
            checkboxFrame.grid(row=2, column=0)

        Frame(self.settings, bg=self.colors['Gray'], height=2).grid(
            row=5, column=0, pady=10, sticky="ew")  # Separator

        # Server entries
        if True:
            serverFrame = Frame(self.settings, bg=self.colors['Gray2'])

            Label(serverFrame, text="Mobile App Server (BETA)", justify="center", font=("Source Code Pro Medium", 13),
                  bg=self.colors['Gray2'], fg=self.colors['White']
                  ).grid(row=0, column=0, columnspan=4, sticky="nsew", pady=(0, 7))

            serverVar = IntVar()
            serverVar.set(self.enableServer)
            serverCB = Checkbutton(serverFrame, text=" Enable server", bd=0, relief='solid',
                                   indicatoron=False, image=no_check, compound='left', selectimage=check, font=("Source Code Pro Medium", 13),
                                   activebackground=self.colors['Gray3'], activeforeground=self.colors[
                                       'White'], bg=self.colors['Gray2'], fg=self.colors['White'],
                                   selectcolor=self.colors['Gray2'], variable=serverVar, command=lambda: checkboxHandler(serverVar, "enableServer"))
            serverCB.no_check = no_check
            serverCB.check = check
            serverCB.grid(row=1, column=0, columnspan=4,
                          sticky="nsew", pady=(0, 7))

            serverAddress = StringVar()
            serverAddress.set(self.hostName)
            serverEntry = Entry(serverFrame, textvariable=serverAddress, highlightthickness=0, width=15, justify="center",
                                borderwidth=0, font=("Source Code Pro Medium", 13), bg=self.colors['Gray3'], fg=self.colors['White'])
            serverEntry.bind("<Return>", lambda e,
                             var=serverAddress: updateServer((var, "ADDRESS")))
            serverEntry.grid(row=2, column=0, sticky="nsew")
            self.settings.handles.append(serverEntry)

            tmp = Frame(serverFrame, bg=self.colors['Gray3'])
            Label(tmp, text=":", font=("Source Code Pro Medium", 13), bg=self.colors['Gray3'], fg=self.colors['White']
                  ).grid(row=0, column=0, pady=(2, 0))
            tmp.grid(row=2, column=1, sticky="nsew")

            serverPort = StringVar()
            serverPort.set(self.serverPort)
            serverPortEntry = Entry(serverFrame, textvariable=serverPort, highlightthickness=0, width=5, justify="center",
                                    borderwidth=0, font=("Source Code Pro Medium", 13), bg=self.colors['Gray3'], fg=self.colors['White'])
            serverPortEntry.bind("<Return>", lambda e,
                                 var=serverPort: updateServer((var, "PORT")))
            serverPortEntry.grid(row=2, column=2, sticky="nsew")
            self.settings.handles.append(serverPortEntry)

            Button(serverFrame, text="Restart server", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground=self.colors['Gray2'], activeforeground=self.colors[
                       'White'], bg=self.colors['Gray3'], fg=self.colors['White'],
                   command=lambda address=serverAddress, port=serverPort: updateServer(
                       (address, "ADDRESS"), (port, "PORT"))
                   ).grid(row=2, column=3, sticky="nsew", padx=4)

            serverFrame.grid_columnconfigure(0, weight=1)
            serverFrame.grid_columnconfigure(1, weight=1)
            serverFrame.grid(row=6, column=0, padx=2)

        Frame(self.settings, bg=self.colors['Gray'], height=2).grid(
            row=7, column=0, pady=10, sticky="ew")  # Separator

        # Qbittorent entries
        if True:
            torrentFrame = Frame(self.settings, bg=self.colors['Gray2'])
            entries = {}
            auth = self.getQB()
            if auth == "ADDRESS":
                colA, colC = 'Red', 'White'
            elif auth == "CREDENTIALS":
                colA, colC = 'Green', 'Red'
            elif auth == "OK":
                colA, colC = 'Green', 'Green'

            Label(torrentFrame, text="qBittorrent Client", justify="center", font=("Source Code Pro Medium", 13),
                  bg=self.colors['Gray2'], fg=self.colors['White']
                  ).grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 7))
            Label(torrentFrame, text="Address:", justify="right", font=("Source Code Pro Medium", 13),
                  bg=self.colors['Gray2'], fg=self.colors['White']
                  ).grid(row=1, column=0, pady=3)
            torrentApiAddress = StringVar()
            torrentApiAddress.set(self.torrentApiAddress)
            entries['address'] = Entry(torrentFrame, textvariable=torrentApiAddress, highlightthickness=0, width=40, justify="center",
                                       borderwidth=0, font=("Source Code Pro Medium", 13), bg=self.colors['Gray3'], fg=self.colors[colA])
            entries['address'].bind(
                "<Return>", lambda e, var=torrentApiAddress: updateTorrent((var, "ADDRESS")))
            entries['address'].grid(row=1, column=1, sticky="nsew", pady=3)

            Label(torrentFrame, text="Login:", justify="right", font=("Source Code Pro Medium", 13),
                  bg=self.colors['Gray2'], fg=self.colors['White']
                  ).grid(row=2, column=0, pady=3)
            torrentApiLogin = StringVar()
            torrentApiLogin.set(self.torrentApiLogin)
            entries['login'] = Entry(torrentFrame, textvariable=torrentApiLogin, highlightthickness=0, justify="center",
                                     borderwidth=0, font=("Source Code Pro Medium", 13), bg=self.colors['Gray3'], fg=self.colors[colC])
            entries['login'].bind(
                "<Return>", lambda e, var=torrentApiLogin: updateTorrent((var, "LOGIN")))
            entries['login'].grid(row=2, column=1, sticky="nsew", pady=3)

            Label(torrentFrame, text="Password:", justify="right", font=("Source Code Pro Medium", 13),
                  bg=self.colors['Gray2'], fg=self.colors['White']
                  ).grid(row=3, column=0, pady=3)
            torrentPwd = StringVar()
            torrentPwd.set(self.torrentApiPassword)
            entries['password'] = Entry(torrentFrame, textvariable=torrentPwd, highlightthickness=0, justify="center",
                                        borderwidth=0, font=("Source Code Pro Medium", 13), bg=self.colors['Gray3'], fg=self.colors[colC])
            entries['password'].bind(
                "<Return>", lambda e, var=torrentPwd: updateTorrent((var, "LOGIN")))
            entries['password'].grid(row=3, column=1, sticky="nsew", pady=3)

            b = Button(torrentFrame, text="Connect", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                       activebackground=self.colors['Gray'], activeforeground=self.colors['White'], bg=self.colors['Gray3'], fg=self.colors['White'],)
            b.configure(command=lambda address=torrentApiAddress, login=torrentApiLogin, pwd=torrentPwd,
                        b=entries: updateTorrent((address, "ADDRESS"), (login, "LOGIN"), (pwd, "PASSWORD"), entries=b))
            b.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=3)

            self.settings.handles += list(entries.values())
            torrentFrame.grid_columnconfigure(1, weight=1)
            torrentFrame.grid(row=8, column=0, padx=2)

        Frame(self.settings, bg=self.colors['Gray'], height=2).grid(
            row=9, column=0, pady=10, sticky="ew")  # Separator

        # Logs frame
        if True:
            logsFrame = Frame(self.settings, bg=self.colors['Gray2'])
            Label(logsFrame, text="Logs", justify="center", font=("Source Code Pro Medium", 13),
                  bg=self.colors['Gray2'], fg=self.colors['White']
                  ).grid(row=0, column=0, sticky="nsew", pady=(0, 7))
            logsParentFrame = Frame(logsFrame, bg=self.colors['Gray2'])
            drawLogs(logsParentFrame)
            logsParentFrame.grid(row=1, column=0, sticky="nsew")
            logsFrame.grid_rowconfigure(1, weight=1)
            logsFrame.grid_columnconfigure(0, weight=1)
            logsFrame.grid(row=10, column=0, sticky="nsew")

        self.settings.update()

    def updateCache(self):
        c = 0
        maxDate = timedelta(days=7)
        for f in os.listdir(self.cache):
            path = os.path.join(self.cache, f)
            t = os.path.getmtime(path)
            date = datetime.fromtimestamp(t)
            delta = datetime.today() - date
            if delta > maxDate:
                c += 1
                os.unlink(path)
        self.log("DB_UPDATE", "Updated cache, {} image{} deleted.".format(
            c if c > 0 else "no", "s" if c >= 2 else ""))

    def updateDirs(self):
        modified = False
        for f in os.listdir(self.animePath):
            path = os.path.join(self.animePath, f)
            if os.path.isdir(path) and len(os.listdir(path)) == 0:
                self.log("DB_UPDATE", os.path.normpath(path), 'is empty!')
                os.rmdir(path)
                modified = True
        if not modified:
            self.log("DB_UPDATE", "No empty directory to remove.")

    def updateTag(self):
        self.log("DB_UPDATE", "Updating tags")
        database = self.getDatabase()
        # files = [file for file in os.listdir(self.animePath)]
        toWatch = []
        toSeen = []

        torrentDb = database.sql(
            'SELECT anime.id,tag.tag,anime.torrent FROM anime LEFT JOIN tag on tag.id = anime.id')
        self.animeFolder = os.listdir(self.animePath)
        c = 0
        for id, tag, torrent in torrentDb:
            folder = self.getFolder(id)
            if folder is not None and os.path.isdir(
                    os.path.join(self.animePath, folder)):
                if tag != 'WATCHING':
                    self.log('DB_UPDATE', "Folder '" + folder +
                             "' id", id, "exists, but tag is", tag)
                    toWatch.append(id)
                    c += 1
            else:
                if tag == 'WATCHING' and torrent is not None:
                    self.log('DB_UPDATE', "Folder '" + folder +
                             "' doesn't have a folder, but tag is", tag)
                    toSeen.append(id)
                    c += 1

        try:
            if len(toWatch) >= 1:
                database.sql("UPDATE tag SET tag = 'WATCHING' WHERE id IN(?" +
                             ",?" * (len(toWatch) - 1) + ");", toWatch)
            if len(toSeen) >= 1:
                database.sql(
                    "UPDATE tag SET tag = 'SEEN' WHERE id IN(?" + ",?" * (len(toSeen) - 1) + ");", toSeen)
        except sqlite3.OperationalError:
            self.log('DB_UPDATE', 'Error while updating tags')

        database.save()
        if c >= 1:
            self.log('DB_UPDATE', "{} tags updated!".format(c))
        else:
            self.log('DB_UPDATE', "No tags to update.")

    def updateTitles(self):
        database = self.getDatabase()

        sql = "SELECT id,title_synonyms FROM anime WHERE id NOT IN(SELECT id FROM searchTitles) AND title_synonyms IS NOT null;"
        sqlData = database.sql(sql)

        if len(sqlData) == 0:
            self.log('DB_UPDATE', "No titles to update.")
            return

        # titles = database.sql("SELECT title FROM searchTitles;")
        needSave = False
        c = 0
        for data in sqlData:
            id = data[0]
            if data[1] is None:
                titles = []
            else:
                titles = json.loads(data[1])
            for title in titles:
                title = "".join([c for c in title if c.isalnum()]
                                ).lower() if title is not None else ""

                sql = "SELECT EXISTS(SELECT 1 FROM searchTitles WHERE title = ? AND id = ?);"
                if not bool(database.sql(sql, (title, id))[0][0]):
                    self.log('DB_UPDATE', id, "- title not in db:", title)
                    c += 1
                    database(id=id, table='searchTitles').insert(
                        {"id": id, 'title': title}, save=False)
                    needSave = True

        if needSave:
            database.save()

        self.log('DB_UPDATE', "{} titles updated!".format(c))

    def getSchedule(self):
        timer = utils.Timer("schedule")
        database = self.getDatabase()

        data = self.api.schedule(limit=self.maxTrendingAnime)

        c = None
        try:
            for c, anime in enumerate(data):
                id = anime['id']
                # not id in dbKeys:
                if not database(id=id, table="indexList").exist():
                    title = anime['title']
                    database(table="anime").set(anime)
                    self.log('SCHEDULE', "Added anime",
                             id, title, "from schedule")
        except requests.exceptions.ConnectionError as e:
            self.log('NETWORK', "No internet connection, skipping schedule")
            return
        except APIException as e:
            if e.status_code == 429:
                self.log(
                    'NETWORK', "[ERROR] - Status code 429, skipping schedule")
            else:
                raise e
            return
        except requests.exceptions.ReadTimeout as e:
            self.log("NETWORK", "Timed out!")
            return
        except simplejson.errors.JSONDecodeError as e:
            self.log("SCHEDULE", e)
            raise e
        if c is None:
            self.log('DB_UPDATE', "No new animes from schedule")
        else:
            self.log(
                'DB_UPDATE',
                "Updated {} new animes from schedule".format(
                    c + 1))

    def getRelations(self):
        # Not used
        if len(self.relationIds) == 0:
            self.log('DB_UPDATE', "No relation to update.")
            return

        database = self.getDatabase()

        self.log('DB_UPDATE', "Updating relations, at least",
                 len(self.relationIds), "ids")
        dbAllkeys = database.allkeys()
        database.table = "anime"
        c = 0
        while len(self.relationIds) > 0:
            id = self.relationIds.pop()
            while len(self.relationIds) > 0 and id in database.allkeys(
                    'related') and id != 0:
                id = self.relationIds.pop()
            if id in database.allkeys('related'):
                break
            database.id = id
            c += 1

            data = self.api.anime(id)
            if data == {}:
                return {}
            related = anime.related

            for rel_id, relation in related.items():
                updated = database.addRelated(id, relation, rel_id)
                self.relationIds.append(rel_id)
            del anime.related
            database(table="anime").set(data)
        if c >= 1:
            database.save()
        self.log('DB_UPDATE', c, "new relations updated!")

    def getAnimeDataThread(self, title):
        def saveTitles(out):
            database = db(self.dbPath)
            for anime in out:
                id = anime.id
                database.id = id
                if id != -1:
                    # self.log('NETWORK',newData['title'])
                    database(table="anime").set(anime, save=False)
                    titles = json.loads(anime.title_synonyms)
                    for title in titles:
                        if title is not None:
                            title = "".join(
                                [c for c in title if c.isalnum()]).lower()
                            sql = "SELECT EXISTS(SELECT 1 FROM searchTitles WHERE title = ?);"
                            if not bool(database.sql(sql, (title,))[0][0]):
                                self.log('DB_UPDATE', id,
                                         "- title not in db:", title)
                                database(id=id, table='searchTitles').insert(
                                    {'id': id, 'title': title}, save=False)
            database.save()

        def handler(self):
            # self.animeListReady = True
            out = []
            elems = []
            que = queue.Queue()
            threading.Thread(target=self.getImgThread, args=(que,)).start()
            self.fen.after(10, self.getElemImages)

            while len(self.searchQueue) >= 1 and not self.stopSearch:
                title, results = self.searchQueue.pop(0)
                self.log('NETWORK', "Length:", len(
                    self.searchQueue), "Starting", str(title))
                rep = self.getAnimeData(title, results)

                while len(elems) > 0:
                    e = elems.pop()
                    self.fen.after_cancel(e)
                for child in self.scrollable_frame.winfo_children():
                    child.destroy()
                self.scrollable_frame.canvas.yview_moveto(0)

                # self.animeList = rep
                # e = self.fen.after(0,lambda:self.createList("",(0,1000)))
                # elems.append(e)
                for i, data in enumerate(rep):
                    out.append(data)
                    elems.append(self.fen.after(
                        0, lambda a=i, b=data, c=que: self.createElem(a, b, c)))

                    if len(self.searchQueue) >= 1:
                        break

            if self.stopSearch:
                while len(elems) > 0:
                    e = elems.pop()
                    self.fen.after_cancel(e)
                self.log('NETWORK', "Thread interrupted")
                return

            if len(out) == 0:
                self.animeListReady = True
                self.createList("")
                self.lastSearch = None
                Label(self.scrollable_frame, text="No results", font=("Source Code Pro Medium", 20),
                      bg=self.colors['Gray2'], fg=self.colors['Gray4'],
                      ).grid(columnspan=4, row=0, pady=50)
            elif len(self.searchQueue) == 0:
                que.put("STOP")

                e = next(self.animeList, None)
                if e is not None:
                    self.loadMoreButton(i + 1, (0, 50), None)

                self.scrollable_frame.update()

                # self.fen.after(1,self.createList,"")
            threading.Thread(target=saveTitles, args=(out,)).start()
            self.log('NETWORK', "Thread done!")

        if title != "":
            self.searchQueue.append((title, self.animePerSearch))
            self.searchQueue.sort(key=len)
            for a in self.searchQueue:
                for b in self.searchQueue:
                    if a[0] != b[0]:
                        if a[0] in b[0]:
                            self.searchQueue.remove(a)
                        elif b[0] in a[0]:
                            self.searchQueue.remove(b)

        if self.searchThread is None or not self.searchThread.is_alive():
            self.stopSearch = False
            self.log('NETWORK', "Starting search thread!")
            self.searchThread = threading.Thread(target=handler, args=(self,))
            self.searchThread.start()
            self.loading()

    def getAnimeData(self, name, results=50):
        search = name + "   " if len(name) < 3 else name
        que = queue.Queue()

        def func(que, search, results): return que.put(
            self.api.searchAnime(search, limit=results))
        thread = threading.Thread(target=func, args=(que, name, results))
        thread.start()
        searchResults = que.get()

        if searchResults == False:
            return
        self.log('NETWORK', "Data received")
        # self.animeList = []
        for data in searchResults:
            yield data
            # if anime.id not in (k for k in self.animeList):
            # 	self.animeList.append(data)
            if self.stopSearch:
                break

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
        self.createList("", (0, 1000))

    def getCharactersData(self, id, callback=None):
        database = self.getDatabase()

        self.log('NETWORK_DATA', "Requesting characters data for id", id)
        characters = []

        keys = database(id=id, table="indexList").get()

        try:
            data = self.api.animeCharacters(id)
        except APIException as e:
            if e.status_code == 429:
                self.log('NETWORK', "Status code 429")
            else:
                self.log(
                    'DB_ERROR',
                    "Can't get characters data, id: " +
                    str(id))
            return
        except requests.exceptions.ConnectionError as e:
            self.log('NETWORK', "[ERROR] - No internet connection!")
            return

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
                sql = "INSERT INTO characters(" + "{}," * (
                    len(character.keys()) - 1) + "{}) VALUES (" + "?," * (len(character.keys()) - 1) + "?);"
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
        character = None
        try:
            character = self.api.character(id)
        except APIException as e:
            if e.status_code == 429:
                time.sleep(5)
                self.getCharacterData(id)
            return
        except requests.exceptions.ConnectionError as e:
            self.log('NETWORK', "[ERROR] - No internet connection!")
            return
        except requests.exceptions.ReadTimeout as e:
            self.log("NETWORK", "Timed out!")
            return {}

        sql = "SELECT role FROM characters WHERE id = ? AND role IS NOT NULL;"
        roleData = database.sql(sql, (character['id'],))
        if len(roleData) >= 1:
            character['role'] = roleData[0][0]

        if 'animeography' in character.keys():
            animes = character.pop('animeography')
            self.log("CHARACTER", "Adding character with id", id,
                     "name", character['name'], "to", len(animes), "animes.")
            # for anime in animes: TODO
            # 	character['anime_id'] = database.getId(api_key,anime['mal_id'])
            # 	sql = "SELECT EXISTS(SELECT 1 FROM characters WHERE id = ? AND anime_id = ?);"
            # 	values = list(character.values())
            # 	if bool(database.sql(sql,(character['id'],character['anime_id']))[0][0]):
            # 		sql = "UPDATE characters SET " + "{} = ?,"*(len(character)-1) + "{} = ? WHERE id = ? AND anime_id = ?;"
            # 		sql = sql.format(*character.keys())
            # 		values += [character['id'],character['anime_id']]
            # 	else:
            # 		sql = "INSERT INTO characters(" + "{},"*(len(character)-1) + "{}) VALUES(" + "?,"*(len(character)-1)+"?);"
            # 		sql = sql.format(*character.keys())
            # 	try:
            # 		database.sql(sql,values,save=True)
            # 	except Exception as e:
            # 		raise e

        return character


if __name__ == '__main__':
    m = Manager()
