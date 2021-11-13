from datetime import datetime, timedelta
import os
import utils


class UpdateUtils:
    def updateAll(self, schedule=True):
        self.updateCache()
        self.updateDirs()
        self.updateTag()
        self.regroupFiles()
        self.updateTitles()
        if schedule:
            self.getSchedule()

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
                    self.log('DB_UPDATE', "Folder '" + folder + "' id", id, "exists, but tag is", tag)
                    toWatch.append(id)
                    c += 1
            else:
                if tag == 'WATCHING' and torrent is not None:
                    self.log('DB_UPDATE', "Folder '" + folder + "' doesn't have a folder, but tag is", tag)
                    toSeen.append(id)
                    c += 1

        try:
            if len(toWatch) >= 1:
                database.sql("UPDATE tag SET tag = 'WATCHING' WHERE id IN(?" + ",?" * (len(toWatch) - 1) + ");", toWatch)
            if len(toSeen) >= 1:
                database.sql("UPDATE tag SET tag = 'SEEN' WHERE id IN(?" + ",?" * (len(toSeen) - 1) + ");", toSeen)
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

        c = 0
        for anime in data:
            id = anime['id']
            # not id in dbKeys:
            if not database(id=id, table="indexList").exist():
                c += 1
                title = anime['title']
                database(table="anime").set(anime)
                self.log('SCHEDULE', "Added anime",
                         id, title, "from schedule")

        if c == 0:
            self.log('DB_UPDATE', "No new animes from schedule")
        else:
            self.log(
                'DB_UPDATE',
                "Updated {} new animes from schedule".format(c))
