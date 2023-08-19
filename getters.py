if __name__ == "__main__":
    import auto_launch

import base64
import codecs
import io
import json
import os
import queue
import re
import string
import threading
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone

import requests
from PIL import Image, ImageTk

from constants import Constants
from classes import Anime, RegroupList, ReturnThread, Torrent
from dbManager import thread_safe_db
import file_managers
import torrent_managers

if 'database_threads' not in globals().keys():
    globals()['database_threads'] = {}


class Getters:
    def getDatabase(self=None):
        if self is None:
            self = type('EmptyObject', (), {})()
        if threading.main_thread() == threading.current_thread() and hasattr(self, "database") and isinstance(self.database, thread_safe_db):
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

    def getFileManager(self, manager, update=False):
        fm = file_managers.managers.get(manager, None)
        if fm is None:
            raise ModuleNotFoundError(f'File manager {manager} was not found')

        args = self.settings['file_managers'].get(manager, {})
        self.fm = fm(args, update)
        if not hasattr(self.fm, 'settings'):
            raise AttributeError('All file managers should have a "settings" attribute')
        
        args = self.fm.settings
        self.setSettings({manager: args})
        
        dataPath = args.get('dataPath', None)
        if dataPath is not None:
            self.dataPath = dataPath
            # Otherwise keep default value

        self.animePath = os.path.join(self.dataPath, "Animes")

    def getTorrentManager(self, manager, update=False):
        tm = torrent_managers.managers.get(manager, None)
        if tm is None:
            raise ModuleNotFoundError(f'Torrent manager {manager} was not found')

        args = self.settings['torrent_managers'].get(manager, {})
        self.tm = tm(args, update)
        if not hasattr(self.tm, 'settings'):
            raise AttributeError('All torrent managers should have a "settings" attribute')
        
        args = self.tm.settings
        self.setSettings({manager: args})

    def getImage(self, path, size=None):
        if (isinstance(path, str) and os.path.isfile(path)) or isinstance(path, io.IOBase):
            img = Image.open(path)
            if size is not None:
                img = img.resize(size, Image.LANCZOS)
        else:
            img = Image.new('RGB', (10, 10) if size is None else size, self.colors['Gray'])
        return ImageTk.PhotoImage(img, master=self.root)

    @staticmethod
    def getStatus(anime):
        if anime.status is not None:
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
        with self.fm.open(file, 'rb') as f:
            m = re.findall(rb"name\d+:(.*?)\d+:piece length", f.read())
        if len(m) != 0:
            return m[0].decode()
        else:
            return None

    def getTorrentHash(self, path):
        objTorrentFile = self.fm.open(path, "rb")

        t = torrent_managers.Torrent.from_torrent(objTorrentFile)
        info_hash = t.hash

        return info_hash

    @staticmethod
    def getMagnetHash(url):
        m = re.findall(r'magnet:\?xt=urn:btih:([a-zA-Z0-9]+)', url)
        if len(m) > 0:
            m_hash = m[0]
            if not all(c in string.hexdigits for c in m_hash):
                m_bytes = base64.b32decode(m_hash.encode(), casefold=True)
                m_hash = codecs.encode(m_bytes, 'hex').decode()
            return m_hash
        else:
            raise ValueError("Hash not found for magnet link:", url)

    def getTorrentColor(self, title):
        def fileFormat(f):
            # Format filename to increase matches
            return f.rsplit(".torrent", 1)[0].replace(' ','').lower()

        timeNow = time.time()
        folderUpdateDelay = 30 # Parse the torrent folder at most every x seconds

        # Cached data

        # Check if title has already been matched before
        if hasattr(Constants, 'getTorrentColor_title_cache'):
            # If title is in cache, skips everything and immediately return the result
            title_cache = Constants.getTorrentColor_title_cache
            fg = title_cache.get(title)
            if fg:
                return fg
        else:
            # Create empty cache
            title_cache = {}
            Constants.getTorrentColor_title_cache = title_cache

        # self.formattedTorrentFiles = (lastUpdate, files) -> Avoid parsing the entire torrent 
        # folder at each call (faster)
        if hasattr(self, 'formattedTorrentFiles') and timeNow - self.formattedTorrentFiles[0] < folderUpdateDelay:
            files = self.formattedTorrentFiles[1]
        else:
            files = set()
            torrents = self.getTorrents()
            for torrent in torrents:
                if torrent.name is None:
                    continue

                formatted = fileFormat(torrent.name)
                if len(formatted) > 5: # Ignore names that are too short
                    files.add(formatted)
            self.formattedTorrentFiles = (timeNow, files)

        # Precompile all regex patterns for markers (from settings)
        if hasattr(Constants, 'getTorrentColor_pat_cache'):
            # A bit hacky, but it's useless to compile the patterns every time
            pat_cache = Constants.getTorrentColor_pat_cache
        else:
            pat_cache = {re.compile(pat, re.I): col for col, pats in self.fileMarkers.items() for pat in pats}
            Constants.getTorrentColor_pat_cache = pat_cache
        
        # Try to get previous match results
        if hasattr(Constants, 'getTorrentColor_matchs_cache'):
            # A bit hacky, but it's useless to compile the patterns every time
            matchs_cache = Constants.getTorrentColor_matchs_cache
        else:
            matchs_cache = {}
            Constants.getTorrentColor_matchs_cache = matchs_cache

        t = fileFormat(title)
        fg = None
        for f in files:
            if t in f or f in t: # TODO
                # The torrent already exists
                fg = self.colors['Blue']
            else:
                for pat, color in pat_cache.items():
                    match_id = pat.pattern + '-' + t # Should be unique for each pair
                    match = matchs_cache.get(match_id)

                    if match is None:
                        # First time on this title, check if 
                        # there's a match and save it to cache
                        match = re.match(pat, title) is not None
                        matchs_cache[match_id] = match

                    if match:
                        # The torrent contain a marker
                        fg = self.colors[color]
                        break
                
            if fg is not None:
                break
        
        if fg is None:
            fg = self.colors['White']
        
        title_cache[title] = fg

        return fg

    def getTorrents(self, id=None):
        database = self.getDatabase()
        
        keys = ('hash', 'name', 'trackers')
        formatted = ', t.'.join(keys)
        if id is not None:
            condition = 'WHERE i.id=?;'
            args = (id, )
        else:
            condition, args = '', []
        torrents = database.sql(f'SELECT t.{formatted} FROM torrents as t JOIN torrentsIndex as i ON i.value = t.hash {condition}', args)
        out = list(map(lambda t: Torrent(**{keys[i]: t[i] for i in range(len(keys))}), torrents))
        return out

    def saveTorrent(self, id, torrent, save=False):
        database = self.getDatabase()
        hash = torrent.hash
        with database.get_lock():
            exists = bool(database.sql("SELECT EXISTS(SELECT 1 FROM torrentsIndex WHERE id=? AND value=?);", (id, hash))[0][0])
            if not exists:
                database.execute("INSERT INTO torrentsIndex(id, value) VALUES (?,?)", (id, hash))
            
            exists = bool(database.sql("SELECT EXISTS(SELECT 1 FROM torrents WHERE hash=?);", (hash, ))[0][0])
            if not exists:
                database.execute(f"INSERT INTO torrents(hash, name, trackers) VALUES (?,?,?)", (hash, torrent.name, json.dumps(torrent.trackers)))

            if save:
                database.save()

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
            self.animeFolder = self.fm.list(self.animePath)
        else:
            if not isinstance(anime, Anime):
                anime = Anime(anime)
            if id is None:
                id = anime.id

        for f in self.animeFolder:
            if not self.fm.isdir(os.path.normpath(os.path.join(self.animePath, f))):
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
                if data in processes:
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

    def getAnimePictures(self, id):
        data = self.database.sql("SELECT url, size FROM pictures WHERE id=?", (id,), to_dict=True)
        # url = self.database.sql("SELECT picture FROM anime WHERE id=?", (id,))[0][0]
        # data = [{'url': url}]
        return data

    def get_relations(self, id, **filters):
        data = self.database.sql("SELECT * FROM animeRelations WHERE id=?", (id,), to_dict=True)
        data = [a for a in data if all(a[k] == v for k, v in filters.items())]
        return RegroupList("id", ["rel_id"], *data) #*list(filter(lambda e: all(e[k] == v for k, v in filters.items()), data)))

    def getBroadcast(self, thread=False):
        if not thread:
            return ReturnThread(target=self.getBroadcast, args=(True,))

        path = os.path.join(self.cache, "broadcasts")
        rss_url = "https://www.livechart.me/feeds/episodes"
        ignore = ('enclosure', '{http://search.yahoo.com/mrss/}thumbnail')

        # try:
        if True:
            if not os.path.exists(path):
                raise FileNotFoundError()
            tree = ET.parse(path)
            root = tree.getroot()[0]
            entries = []
            for child in root:
                if child.tag == "item":
                    c_dict = {c.tag: c.text for c in child if c.tag not in ignore}
                    title, num = c_dict['title'].split(" #")
                    a_id = self.database.sql("SELECT id FROM title_synonyms WHERE value=?;", (title,))
                    if a_id:
                        a_id = a_id[0][0]
                        date = datetime.strptime(c_dict['pubDate'], "%a, %d %b %Y %H:%M:%S %z").astimezone(datetime.now().astimezone().tzinfo)

                        c_dict['pubDate'] = date
                        c_dict['id'] = a_id
                        c_dict['title'] = title
                        c_dict['eps'] = num
                        entries.append(c_dict)
                    else:
                        continue
                elif child.tag == "lastBuildDate":
                    build_date = child.text
                    print(build_date, type(build_date), flush=True)
                    fetch_date = datetime.strptime(build_date, "%a, %d %b %Y %H:%M:%S %z").astimezone(datetime.now().astimezone().tzinfo)
                    print(fetch_date, flush=True)
            delta = datetime.now(timezone.utc).astimezone() - fetch_date
        # except Exception as e:
        #     self.log("MAIN_STATE", "[ERROR] - While fetching broadcasts:", e)
        #     delta = timedelta.max

        if delta > timedelta(hours=1):
            try:
                r = requests.get(rss_url)
            except Exception:
                pass
            else:
                with open(path, 'wb') as f:
                    f.write(r.content)
                print("LOOPING", delta)
                return self.getBroadcast(thread=True)

        print(entries)
        return entries
