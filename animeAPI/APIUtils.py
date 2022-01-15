from datetime import date
import requests
import sys
import os
import re

sys.path.append(os.path.abspath("../"))
try:
    from dbManager import db
    from classes import Anime, Character, NoIdFound
    from logger import Logger
    from getters import Getters
except ModuleNotFoundError as e:
    print("Module not found:", e)
    db = None


class APIUtils(Getters, Logger):
    def __init__(self, dbPath):
        super().__init__(logs="ALL")
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
            self.log("Key not found!", "SELECT {} FROM {} WHERE id={}".format(
                self.apiKey, index, id))
            raise NoIdFound()
            # raise Exception("Wrong api")
            # return None
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
            self.log("KeyError while parsing genres:", genres, dir(genres[0]))
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
                self.database.executemany("INSERT INTO genresIndex({},name) VALUES(?,?);".format(self.apiKey), ((id, ids[id]) for id in new), get_output=False)
            if update:
                self.database.executemany("UPDATE genresIndex SET {}=? WHERE id=?;".format(self.apiKey), update, get_output=False)
            data = self.database.sql(sql, ids.keys(), to_dict=True)
        return list(g['id'] for g in data)

    def save_relations(self, id, rels):
        # Rels must be a list of dicts, each containing four fields: 'type', 'name', 'rel_id' and 'anime'
        if len(rels) == 0:
            return
        with self.database.get_lock():
            db_rels = self.get_relations(id)
            for rel in rels:
                if rel["type"] == "anime":
                    rel["id"] = id
                    rel["rel_id"], meta = self.database.getId(self.apiKey, rel["rel_id"], add_meta=True)
                    anime = rel.pop("anime")
                    if not list(filter(lambda e: all(e[k] == v for k, v in rel.items()), db_rels)):
                        sql = "INSERT INTO relations (" + ", ".join(rel.keys()) + ") VALUES (" + ", ".join("?" * len(rel)) + ");"
                        self.database.sql(sql, rel.values(), get_output=False)
                    if not meta['exists']:
                        anime["id"] = rel["rel_id"]
                        anime["status"] = "UPDATE"
                        self.database.set(anime, table="anime", get_output=False)
            self.database.save(get_output=False)


class EnhancedSession(requests.Session):
    def __init__(self, timeout=(3.05, 4)):
        self.timeout = timeout
        return super().__init__()

    def request(self, method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        return super().request(method, url, **kwargs)
