import utils
from classes import Anime, AnimeList


class AnimeSearch():
    def searchAnime(self, title):
        def handler(title):
            search = title.ljust(3)
            rep = self.api.searchAnime(search, limit=self.animePerSearch)

            for data in rep:
                yield Anime(data)

            self.stopSearch = True  # For the loading animation

        if title != "":
            return AnimeList(handler(title))

    def saveTitles(self, out):
        database = self.getDatabase()
        for anime in out:
            id = anime.id
            database.id = id
            if id != -1:
                # self.log('NETWORK',newData['title'])
                database.set(anime, table="anime", save=False)
                titles = json.loads(anime.title_synonyms)
                for title in titles:
                    if title is not None:
                        title = "".join(
                            [c for c in title if c.isalnum()]).lower()
                        sql = "SELECT EXISTS(SELECT 1 FROM searchTitles WHERE title = ?);"
                        if not bool(database.sql(sql, (title,))[0][0]):
                            self.log('DB_UPDATE', id,
                                     "- title not in db:", title)
                            database.insert(
                                {'id': id, 'title': title}, table='searchTitles', save=False)
        database.save()
