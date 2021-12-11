import auto_launch

from datetime import date, datetime, timedelta
import os
import utils
import json
import threading
from sqlite3 import OperationalError

from classes import Anime


class UpdateUtils:
    def updateAll(self, schedule=True):
        self.updateCache()
        self.updateDirs()
        self.updateTag()
        self.regroupFiles()
        self.updateTitles()
        if schedule:
            self.getSchedule()

    def updateAllProgression(self, schedule=False):
        def wrapper(f):
            try:
                f()
            except BaseException as e:
                self.log("MAIN_STATE", "[ERROR] - On update function:", str(e))
                raise
        reloadFunc = {
            self.updateCache: "Updating cache",
            self.updateDirs: "Updating directories",
            self.updateTag: "Updating tags",
            self.regroupFiles: "Regrouping files",
            self.updateTitles: "Updating titles",
        }
        yield len(reloadFunc)

        for f, text in reloadFunc.items():
            thread = threading.Thread(target=wrapper, args=(f,))
            thread.start()
            yield thread, text
            thread.join()

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
                os.remove(path)
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
        statusUpdate = []

        keys = list(database.keys(table="anime")) + ['tag']
        anime_db = database.sql(
            'SELECT anime.*,tag.tag FROM anime LEFT JOIN tag using(id)', iterate=True)
        # anime_db = list(anime_db)
        # print(anime_db)
        self.animeFolder = os.listdir(self.animePath)
        c = 0
        for data in anime_db:
            anime = Anime(keys=keys, values=data)
            id, tag, torrent = anime.id, anime.tag, anime.torrent
            self.log("DB UPDATE", "Id:", id)
            folder = self.getFolder(id, anime=anime)
            if folder is not None and os.path.isdir(os.path.join(self.animePath, folder)):
                if tag != 'WATCHING':
                    self.log('DB_UPDATE', "Folder '" + folder + "' id", id, "exists, but tag is", tag)
                    toWatch.append(id)
                    c += 1
            else:
                if tag == 'WATCHING' and torrent is not None:
                    self.log('DB_UPDATE', "Folder '" + folder + "' doesn't have a folder, but tag is", tag)
                    toSeen.append(id)
                    c += 1
            if anime.status == "UPCOMING" and anime.date_from is not None:
                delta = date.today() - date.fromisoformat(anime.date_from)
                if delta >= timedelta():  # timedelta() == 0
                    statusUpdate.append(anime)
                    c += 1

        for anime in statusUpdate:
            old_status = anime.status
            anime.status = None
            anime.status = self.getStatus(anime)
            database.set(anime, table="anime")
            self.log('DB_UPDATE', "Updated status for anime: {}, from {} to {}".format(anime.title, old_status, anime.status))

        try:
            if len(toWatch) >= 1:
                database.sql("UPDATE tag SET tag = 'WATCHING' WHERE id IN(?" + ",?" * (len(toWatch) - 1) + ");", toWatch)
            if len(toSeen) >= 1:
                database.sql("UPDATE tag SET tag = 'SEEN' WHERE id IN(?" + ",?" * (len(toSeen) - 1) + ");", toSeen)
        except OperationalError:
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
                    database.insert(
                        {"id": id, 'title': title}, table='searchTitles', save=False)
                    needSave = True

        if needSave:
            database.save()

        self.log('DB_UPDATE', "{} titles updated!".format(c))

    def getSchedule(self):
        timer = utils.Timer("schedule")
        database = self.getDatabase()

        data = self.api.schedule(limit=self.maxTrendingAnime)

        c = 0
        for anime in data:
            id = anime['id']
            # not id in dbKeys:
            if not database.exist(id=id, table="indexList"):
                c += 1
                title = anime['title']
                database.set(anime, table="anime")
                self.log('SCHEDULE', "Added anime",
                         id, title, "from schedule")

        if c == 0:
            self.log('DB_UPDATE', "No new animes from schedule")
        else:
            self.log(
                'DB_UPDATE',
                "Updated {} new animes from schedule".format(c))
