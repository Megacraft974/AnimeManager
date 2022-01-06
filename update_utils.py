import auto_launch

from datetime import date, datetime, timedelta
import os
import utils
import json
import re
import threading
from sqlite3 import OperationalError

from classes import Anime


class UpdateUtils:
    def updateAll(self, schedule=True):
        self.updateCache()
        self.updateDirs()
        self.updateTag()
        self.updateStatus()
        self.regroupFiles()
        if schedule:
            self.getSchedule()

    def updateAllProgression(self, schedule=False):
        def wrapper(f):
            try:
                f()
            except OperationalError as e:
                if e.args == ('database is locked',):
                    self.log("MAIN_STATE", "[ERROR] - On update function: Database is locked!")
                else:
                    self.log("MAIN_STATE", "[ERROR] - On update function:", str(e))
                    raise
            except BaseException as e:
                self.log("MAIN_STATE", "[ERROR] - On update function:", str(e))
                raise
        reloadFunc = {
            self.updateCache: "Updating cache",
            self.updateDirs: "Updating directories",
            self.updateTag: "Updating tags",
            self.updateStatus: "Updating status",
            self.regroupFiles: "Regrouping files",
        }
        yield len(reloadFunc)

        for f, text in reloadFunc.items():
            thread = threading.Thread(target=wrapper, args=(f,))
            thread.start()
            yield thread, text
            thread.join()

    def regroupFiles(self, silent=False):
        if not silent:
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
            if not silent:
                self.log("DISK_ERROR", "Torrent folder doesn't exists!")
            return

        c = 0

        torrentDb = database.sql(
            'SELECT id,title FROM anime WHERE id IN (SELECT id FROM torrents)',
            to_dict=True)
        for data in torrentDb:
            anime = Anime(data)
            path = self.getFolder(anime=anime)
            if os.path.isdir(path):
                hashes = []
                anime.torrents = database.get_metadata(anime.id, "torrents")
                for t in anime.torrents:
                    filePath = os.path.join(self.torrentPath, t)
                    if os.path.isfile(filePath):
                        torrent_hash = self.getTorrentHash(filePath)
                        hashes.append(torrent_hash)
                if self.getQB() == "OK":
                    self.qb.torrents_set_location(
                        location=path, torrent_hashes=hashes)

        if not silent:
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
            if len(os.listdir(path)) == 0:
                self.log("DB_UPDATE", os.path.normpath(path), 'is empty!')
                os.rmdir(path)
                modified = True
        if not modified:
            self.log("DB_UPDATE", "No empty directory to remove.")

    def updateStatus(self):
        self.log("DB_UPDATE", "Updating status")
        statusUpdate = []
        database = self.getDatabase()
        with database.get_lock():
            keys = database.keys(table="anime")
            c = 0

            anime_db = database.sql('SELECT * FROM anime WHERE status="UPCOMING" AND date_from is not null ORDER BY date_from ASC;')  # , iterate=True)
            for data in anime_db:
                anime = Anime(keys=keys, values=data)
                delta = date.today() - date.fromisoformat(anime.date_from)
                if delta >= timedelta():  # timedelta() == 0
                    statusUpdate.append(anime)
                else:
                    # Animes are ordered by date_from ASC
                    break

            status_dict = {}
            for anime in statusUpdate:
                old_status = anime.status
                anime.status = None
                status = self.getStatus(anime)
                if status not in status_dict:
                    status_dict[status] = []
                status_dict[status].append(anime.id)
                # data = {"id": anime.id, "status": status}
                # database.set(data, table="anime", save=False)
                # self.log('DB_UPDATE', "Updated status for anime: {}, from {} to {}".format(anime.title, old_status, anime.status))
                c += 1

            for status, ids in status_dict.items():
                database.sql("UPDATE anime SET status=? WHERE id IN({});".format(",".join(map(str, ids))), [status])

            database.save()
        if c >= 1:
            self.log('DB_UPDATE', "{} status updated!".format(c))  # TODO - ORTHOGRAPH (s / sses / ses / ???)
        else:
            self.log('DB_UPDATE', "No status to update.")

    def updateTag(self):
        self.log("DB_UPDATE", "Updating tags")
        database = self.getDatabase()
        with database.get_lock():
            toWatch = set()
            toSeen = {data[0] for data in database.sql('SELECT id FROM tag LEFT JOIN anime using(id) WHERE tag="WATCHING" AND id IN (SELECT id FROM torrents)')}
            toDelete = {data[0] for data in database.sql('SELECT id FROM tag WHERE id NOT IN (SELECT id FROM anime);')}

            pattern = re.compile(r"^.*? - (\d+)$")

            for f in os.listdir(self.animePath):
                path = os.path.join(self.animePath, f)
                if os.path.isdir(path):
                    match = re.findall(pattern, f)
                    if match and match[0]:
                        anime_id = int(match[0])
                        if anime_id in toSeen:
                            toSeen.remove(anime_id)
                        else:
                            toWatch.add(anime_id)

            if len(toSeen) > 0:
                sql = "SELECT id FROM anime WHERE id IN(" + ",".join("?" * (len(toSeen))) + ");"
                existing_ids = {data[0] for data in database.sql(sql, (toSeen))}

                tmp = {id for id in toSeen if id not in existing_ids}
                toDelete.update(tmp)
                toSeen -= tmp

            if len(toWatch) > 0:
                sql = "SELECT id FROM anime WHERE id IN(" + ",".join("?" * (len(toWatch))) + ");"
                existing_ids = {data[0] for data in database.sql(sql, (toWatch))}

                tmp = {id for id in toWatch if id not in existing_ids}
                toDelete.update(tmp)
                toWatch -= tmp

            try:
                if len(toWatch) >= 1:
                    database.sql("UPDATE tag SET tag = 'WATCHING' WHERE id IN(" + ",".join("?" * len(toWatch)) + ");", toWatch)
                if len(toSeen) >= 1:
                    database.sql("UPDATE tag SET tag = 'SEEN' WHERE id IN(" + ",".join("?" * len(toSeen)) + ");", toSeen)
                if len(toDelete) >= 1:
                    database.sql("DELETE FROM tag WHERE id IN(" + ",".join("?" * (len(toDelete))) + ");", toDelete)
            except OperationalError:
                self.log('DB_UPDATE', 'Error while updating tags')

        c = len(toSeen) + len(toWatch) + len(toDelete)
        if c >= 1:
            database.save()
            self.log('DB_UPDATE', "{} tags updated!".format(c))
        else:
            self.log('DB_UPDATE', "No tags to update.")

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
