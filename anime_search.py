import auto_launch

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