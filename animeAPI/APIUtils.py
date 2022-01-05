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

    @property
    def __name__(self):
        return str(self.__class__).split("'")[1].split('.')[-1]

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
        with self.database.get_lock():
            api_id = self.database.sql(
                "SELECT {} FROM {} WHERE id=?".format(self.apiKey, index), (id,))
        if api_id == []:
            log("Key not found!", "SELECT {} FROM {} WHERE id={}".format(
                self.apiKey, index, id))
            return None
            # raise Exception("Wrong api")
        return api_id[0][0]

    def getGenres(self, genres):
        # Genres must be an iterable of dicts, each one containing two fields: 'id' and 'name'
        if len(genres) == 0:
            return []
        try:
            ids = {}
            for g in genres:
                ids[g['id']] = g['name']
        except KeyError:
            log("KeyError while parsing genres:", genres, dir(genres[0]))
            raise

        sql = ("SELECT * FROM genresIndex WHERE name IN(" + ",".join("?" * len(ids)) + ");").format(api_key=self.apiKey)
        data = self.database.sql(sql, ids.values(), to_dict=True)
        new = set()
        update = set()
        for g_id, g_name in ids.items():
            matches = [m for m in data if m['name'] == g_name]
            if matches:
                match = matches[0]
                if match[self.apiKey] is None:
                    update.add((g_id, match['id']))
            else:
                new.add(g_id)

        if new or update:
            if new:
                self.database.executemany("INSERT INTO genresIndex({},name) VALUES(?,?);".format(self.apiKey), ((id, ids[id]) for id in new))
            if update:
                self.database.executemany("UPDATE genresIndex SET {}=? WHERE id=?;".format(self.apiKey), update)
            data = self.database.sql(sql, ids.keys(), to_dict=True)
        return list(g['id'] for g in data)

    def saveRelations(self, id, api_key, relations):
        ids = []
        for rel in relations:
            if rel["type"] == "anime":  # TODO - Handle non-anime relations
                ids.append((rel["api_key"], rel["rel_id"]))
        sql = "SELECT R.id, R.rel_id, I.id, I.{api_key} FROM related AS R LEFT JOIN indexList AS I ON R.rel_id = I.id \
               WHERE R.id = ? AND I.{api_key} IN(" + ",".join("?" * len(ids)) + ");"
        sql.format(self.apiKey)
        data = self.database.sql(sql, (id, rel_id))

class EnhancedSession(requests.Session):
    def __init__(self, timeout=(3.05, 4)):
        self.timeout = timeout
        return super().__init__()

    def request(self, method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        return super().request(method, url, **kwargs)
