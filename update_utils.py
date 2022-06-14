if __name__ == "__main__":
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
        # self.updateCache()
        # self.updateDirs()
        # self.updateTag()
        # self.updateStatus()
        # self.regroupFiles()
        # if schedule:
        #     self.getSchedule()

        update_iter = self.updateAllProgression(schedule)
        next(update_iter)
        for t, txt in update_iter:
            t.join()

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
            except Exception as e:
                self.log("MAIN_STATE", "[ERROR] - On update function:", str(e))
                raise
        reloadFunc = {
            self.updateCache: "Updating cache",
            self.updateDirs: "Updating directories",
            self.updateTag: "Updating tags",
            self.updateStatus: "Updating status",
            self.regroupFiles: "Regrouping files",
        }
        if schedule:
            reloadFunc |= {
                self.getSchedule: "Updating schedule"
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
            try:
                torrents = self.qb.torrents_info()
            except Exception as e:
                self.log("MAIN_STATE", "[ERROR] - While fetching qb.torrents_info(), disconnecting")
                self.qb = None
                torrents = []
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
        def check_dir_empty(path):
            if os.path.isfile(path):
                return False
            files = os.listdir(path)
            if len(files) == 0:
                return True
            else:
                return all(check_dir_empty(os.path.join(path, f)) for f in files)

        def remove_dir(path):
            if os.path.isfile(path):
                return
            files = os.listdir(path)
            if len(files) > 0:
                for f in files:
                    remove_dir(os.path.join(path, f))

            os.rmdir(path)

        modified = False
        pattern = re.compile(r"^.*? - (\d+)$")
        for f in os.listdir(self.animePath):
            path = os.path.join(self.animePath, f)
            if os.path.isdir(path):
                if check_dir_empty(path):
                    self.log("DB_UPDATE", os.path.normpath(path), 'is empty!')
                    remove_dir(path)
                    modified = True
                match = re.findall(pattern, f)
                if not match or not match[0]:
                    # TODO - Find corresponding torrent
                    pass
            elif os.path.isfile(path):
                pass
                # TODO - Find corresponding anime and put in a directory
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
                c += 1

            for status, ids in status_dict.items():
                database.sql("UPDATE anime SET status=? WHERE id IN({});".format(",".join(map(str, ids))), [status], get_output=False)

            database.save()
        if c >= 1:
            self.log('DB_UPDATE', "{} status updated!".format(c))  # TODO - ORTHOGRAPH (s / sses / ses / ???)
        else:
            self.log('DB_UPDATE', "No status to update.")

    def updateTag(self):
        self.log("DB_UPDATE", "Updating tags")
        pattern = re.compile(r"^.*? - (\d+)$")

        with self.database.get_lock():
            toWatch = set()
            toSeen = {data[0] for data in self.database.sql('SELECT id FROM anime WHERE tag="WATCHING" AND id IN (SELECT id FROM torrents)')}

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

            try:
                if len(toWatch) >= 1:
                    self.log('DB_UPDATE', f'Updating {len(toSeen)} anime tags to Seen')
                    self.database.sql("UPDATE anime SET tag = 'WATCHING' WHERE id IN(" + ",".join("?" * len(toWatch)) + ");", toWatch)
                if len(toSeen) >= 1:
                    self.log('DB_UPDATE', f'Updating {len(toWatch)} anime tags to Watching')
                    self.database.sql("UPDATE anime SET tag = 'SEEN' WHERE id IN(" + ",".join("?" * len(toSeen)) + ");", toSeen)
            except OperationalError:
                self.log('DB_UPDATE', 'Error while updating tags')

        c = len(toSeen) + len(toWatch)
        if c >= 1:
            self.database.save()
            self.log('DB_UPDATE', "{} tags updated!".format(c))
        else:
            self.log('DB_UPDATE', "No tags to update.")

    def getSchedule(self):
        timer = utils.Timer("schedule")
        database = self.getDatabase()

        data = self.api.schedule(limit=self.maxTrendingAnime)

        c = 0
        ids = [anime['id'] for anime in data]
        if len(ids) == 0:
            self.log('DB_UPDATE', 'No animes found from schedule!')
            return
        sql = "SELECT id FROM anime WHERE id IN (" + ", ".join("?" * len(ids)) + ") AND status IS NOT null and status !='UPDATE';"
        exists = {e[0] for e in database.sql(sql, ids)}
        with database.get_lock():
            for anime in data:
                id = anime['id']
                # not id in dbKeys:
                if id not in ids:
                    c += 1
                    title = anime['title']
                    database.set(anime, table="anime", get_output=False)
                    self.log('SCHEDULE', "Added anime",
                             id, title, "from schedule")

        if c == 0:
            self.log('DB_UPDATE', "No new animes from schedule")
        else:
            self.log(
                'DB_UPDATE',
                "Updated {} new animes from schedule".format(c))
