from datetime import date
import requests
import sys
import os
import re

sys.path.append(os.path.abspath("../"))
try:
    from dbManager import db
    from classes import Anime, Character
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
        self.database = self.getDatabase()

    def getStatus(self, data, reverse=True):
        if data['date_from'] is None:
            status = 'UNKNOWN'
        else:
            if not re.search(r'^\d{4}-(0?[1-9]|1[0-2])-(0?[1-9]|[12][0-9]|3[01])$', data['date_from']):
                status = 'UPDATE'
            elif date.fromisoformat(data['date_from']) > date.today():
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
        database = self.getDatabase()
        api_id = self.database.sql(
            "SELECT {} FROM {} WHERE id=?".format(self.apiKey, index), (id,))
        if api_id == []:
            log("Key not found!", "SELECT {} FROM {} WHERE id={}".format(
                self.apiKey, index, id))
            return None
            # raise Exception("Wrong api")
        return api_id[0][0]


class EnhancedSession(requests.Session):
    def __init__(self, timeout=(3.05, 4)):
        self.timeout = timeout
        return super().__init__()

    def request(self, method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        return super().request(method, url, **kwargs)
