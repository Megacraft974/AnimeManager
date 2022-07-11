from datetime import date
import requests
import sys
import os
import re

sys.path.append(os.path.abspath("../"))
try:
    from classes import Anime, Character, NoIdFound
    from logger import Logger
    from getters import Getters
except ModuleNotFoundError as e:
    print("Module not found:", e)


class APIUtils(Logger, Getters):
    def __init__(self, dbPath):
        Logger.__init__(self, logs="ALL")
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
            raise NoIdFound(id)
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

        sql = ("SELECT * FROM genresIndex WHERE name IN(" +
               ",".join("?" * len(ids)) + ");").format(api_key=self.apiKey)
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
                self.database.executemany("INSERT INTO genresIndex({},name) VALUES(?,?);".format(
                    self.apiKey), ((id, ids[id]) for id in new), get_output=False)
            if update:
                self.database.executemany("UPDATE genresIndex SET {}=? WHERE id=?;".format(
                    self.apiKey), update, get_output=False)
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
                    rel["rel_id"], meta = self.database.getId(
                        self.apiKey, rel["rel_id"], add_meta=True)
                    anime = rel.pop("anime")

                    exists = any((
                        (
                            all(e[k] == rel[k]
                                for k in ('id', 'type', 'name'))
                            and rel['rel_id'] in e['rel_id']
                        ) for e in db_rels)
                    )
                    if not exists:
                        sql = "INSERT INTO relations (" + ", ".join(
                            rel.keys()) + ") VALUES (" + ", ".join("?" * len(rel)) + ");"
                        self.database.sql(sql, rel.values(), get_output=False)
                    if not meta['exists']:
                        anime["id"] = rel["rel_id"]
                        anime["status"] = "UPDATE"
                        self.database.set(
                            anime, table="anime", get_output=False)
            self.database.save(get_output=False)

    def save_mapped(self, org_api_key, org_id, mapped):
        # mapped must be a list of dicts, each containing two fields: 'api_key' and 'api_id'
        if len(mapped) == 0:
            return
        with self.database.get_lock():
            for m in mapped:  # Iterate over each external anime
                api_key, api_ip = m['api_key'], m['api_id']

                sql = f"SELECT id, {org_api_key} FROM indexList WHERE {api_key}=?"

                # Get the currently associated org id with the key
                associated = self.database.sql(sql, (api_ip,))
                if len(associated) == 0:
                    associated = [None, None]
                else:
                    associated = associated[0]

                # Update or insert the new id
                if associated[1] != org_id:
                    if associated[0] is not None and associated[1] is None:
                        # Remove old key if it exists
                        self.database.remove(None, id=associated[0],
                                             get_output=False)

                    # Merge both keys
                    self.database.sql(
                        f"UPDATE indexList SET {api_key} = ? WHERE {org_api_key}=?",
                        (api_ip, org_id),
                        get_output=False
                    )

            self.database.save(get_output=False)
        return

    def save_pictures(self, id, pictures):
        # pictures must be a list of dicts, each containing three fields: 'url', 'size'
        valid_sizes = ('small', 'medium', 'large', 'original')
        with self.database.get_lock():
            saved_pics = self.getAnimePictures(id)
            saved_pics = {p['size']: p for p in saved_pics}

            for pic in pictures:
                if pic['size'] not in valid_sizes or pic['url'] is None:
                    continue

                elif pic['size'] in saved_pics:
                    sql = "UPDATE pictures SET url=:url WHERE id=:id AND size=:size"

                else:
                    sql = "INSERT INTO pictures(id, url, size) VALUES (:id, :url, :size)"

                pic['id'] = id

                self.database.sql(sql, pic, get_output=False)

            self.database.save(get_output=False)


class EnhancedSession(requests.Session):
    def __init__(self, timeout=(3.05, 4)):
        self.timeout = timeout
        return super().__init__()

    def request(self, method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        return super().request(method, url, **kwargs)
