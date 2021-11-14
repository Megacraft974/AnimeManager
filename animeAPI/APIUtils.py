from datetime import date
import requests
import sys
import os
sys.path.append(os.path.abspath("../"))
try:
    from dbManager import db
    from classes import Anime, AnimeList, Character, CharacterList
    from logger import log
    from getters import Getters
except ModuleNotFoundError:
    log("DB module not found!")
    db = None


class APIUtils(Getters):
    def __init__(self, dbPath):
        self.states = {
            'airing': 'AIRING',
            'Currently Airing': 'AIRING',
            'completed': 'FINISHED',
            'complete': 'FINISHED',
            'Finished Airing': 'FINISHED',
            'to_be_aired': 'UPCOMING',
            'tba': 'UPCOMING',
            'upcoming': 'UPCOMING',
            'Not yet aired': 'UPCOMING',
            'NONE': 'UNKNOWN'}
        self.dbPath = dbPath
        self.db = self.getDatabase()()

    def getStatus(self, data, reverse=True):
        if data['date_from'] is None:
            status = 'UNKNOWN'
        else:
            if date.fromisoformat(data['date_from']) > date.today():
                status = 'UPCOMING'
            else:
                if data['date_to'] is None:
                    if data['episodes'] == 1:
                        status = 'FINISHED'
                    else:
                        status = 'AIRING'
                else:
                    if date.fromisoformat(data['date_to']) > date.today():
                        status = 'AIRING'
                    else:
                        status = 'FINISHED'
        return status

    def getId(self, id, table="anime"):
        if table == "anime":
            index = "indexList"
        elif table == "characters":
            index = "charactersIndex"
        database = self.getDatabase()()
        api_id = self.db.sql(
            "SELECT {} FROM {} WHERE id=?".format(self.apiKey, index), (id,))
        if api_id == []:
            log("Key not found!", "SELECT {} FROM {} WHERE id={}".format(
                self.apiKey, index, id))
            return None
            # raise Exception("Wrong api")
        return api_id[0][0]

    def save(self, data):
        if isinstance(data, Anime):
            table = "anime"
        elif isinstance(data, Character):
            table = "characters"
        else:
            raise TypeError("{} is an invalid type!".format(str(type(data))))
        self.db(id=data.id, table=table).set(data)


class EnhancedSession(requests.Session):
    def __init__(self, timeout=(3.05, 4)):
        self.timeout = timeout
        return super().__init__()

    def request(self, method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        return super().request(method, url, **kwargs)
