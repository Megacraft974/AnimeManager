import sqlite3
import json
import os
import traceback
import threading
from classes import Anime, Character
from logger import log


class db():
    '''Database manager using sqlite3'''

    def __init__(self, path):
        self.path = path
        if not os.path.exists(self.path):
            self.createNewDb()
        self.con = sqlite3.connect(path, check_same_thread=False)
        # self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        self.table = "anime"
        self.alltable_keys = {}
        # self.updateKeys()

    def createNewDb(self):
        open(self.path, "w")
        self.con = sqlite3.connect(self.path)
        # self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        commands = ('''CREATE TABLE "anime" (
                    "id"    INTEGER NOT NULL UNIQUE,
                    "title"    TEXT,
                    "title_synonyms",
                    "picture"    TEXT,
                    "date_from"    TEXT,
                    "date_to"    TEXT,
                    "synopsis"    TEXT,
                    "episodes"    INTEGER,
                    "duration"    INTEGER,
                    "rating"    TEXT,
                    "status"    TEXT,
                    "torrent"    TEXT,
                    "broadcast"    TEXT,
                    "last_seen"    INTEGER,
                    "trailer"    TEXT,
                    "genres",
                    PRIMARY KEY("id")
                    )''',
                    '''CREATE TABLE "indexList" (
                    "id"    INTEGER NOT NULL UNIQUE,
                    "mal_id"    INTEGER UNIQUE,
                    "kitsu_id"    INTEGER UNIQUE,
                    "anilist_id"    INTEGER UNIQUE,
                    "anidb_id"    INTEGER UNIQUE,
                    PRIMARY KEY("id" AUTOINCREMENT)
                    )''',
                    '''CREATE TABLE "charactersIndex" (
                    "id"    INTEGER NOT NULL UNIQUE,
                    "mal_id"    INTEGER UNIQUE,
                    "kitsu_id"    INTEGER UNIQUE,
                    PRIMARY KEY("id" AUTOINCREMENT)
                    )''',
                    '''CREATE TABLE "characters" (
                    "id"    INTEGER NOT NULL,
                    "anime_id"    INTEGER NOT NULL,
                    "name"    TEXT NOT NULL,
                    "role"    TEXT,
                    "picture"    TEXT,
                    "desc"    TEXT,
                    "like"    INTEGER
                    )''',
                    '''CREATE TABLE "like" (
                    "id"    INTEGER NOT NULL UNIQUE,
                    "like"    INTEGER
                    )''',
                    '''CREATE TABLE "related" (
                    "id"    INTEGER NOT NULL,
                    "relation"    TEXT NOT NULL,
                    "rel_id"    INTEGER NOT NULL
                    )''',
                    '''CREATE TABLE "searchTitles" (
                    "id"    INTEGER,
                    "title"    TEXT
                    )''',
                    '''CREATE TABLE "tag" (
                    "id"    INTEGER NOT NULL UNIQUE,
                    "tag"    TEXT
                    )''',
                    '''CREATE TABLE "genres" (
                    "id"    INTEGER NOT NULL UNIQUE,
                    "mal_id"    INTEGER,
                    "kitsu_id"    INTEGER,
                    "name"    INTEGER,
                    PRIMARY KEY("id" AUTOINCREMENT)
                    )''')
        for c in commands:
            self.cur.execute(c)
        self.con.commit()
        # self.createGenres()

    def close(self):
        self.save()
        self.con.close()

    def updateKeys(self):
        if self.table not in self.alltable_keys:
            self.tablekeys = list(d[1] for d in self.sql(
                "PRAGMA table_info({});".format(self.table)))
            self.alltable_keys[self.table] = self.tablekeys
        else:
            self.tablekeys = self.alltable_keys[self.table]

    def __call__(self, id=None, table=None):
        if id is not None:
            self.id = id
        if table is not None:
            self.table = table
        return self

    def __setitem__(self, key, data):
        self.update(key, data)

    def __getitem__(self, key):
        sql = "SELECT {} FROM {} WHERE id=?".format(key, self.table)
        try:
            e = self.sql(sql, (self.id,))
            if len(e) == 0:
                return "NONE"
            else:
                return e[0][0]
        except BaseException:
            log("", "\nError on id", self.id,
                "table", self.table, "sql", sql)
            raise Exception
        # rows = self.cur.fetchall()

    def __len__(self):
        return len(self.__repr__())

    def __contains__(self, item):
        return item in self.__repr__()

    def __iter__(self):
        self.updateKeys()
        for k in self.tablekeys:
            yield k

    def __delitem__(self, key):
        self.remove(key)

    def __str__(self):
        return str(self.__repr__())

    def __del__(self):
        log("Deleting db instance")
        self.cur.close()

    def keys(self):
        self.updateKeys()
        return self.tablekeys

    def values(self):
        cur = self.con.cursor()
        cur.execute("SELECT * FROM " + self.table + " WHERE id=?", (str(self.id),))
        rows = cur.fetchall()
        if len(rows) >= 1:
            return rows[0]
        else:
            return []

    def items(self):
        self.updateKeys()
        return [(self.tablekeys[i], v) for i, v in enumerate(self.values())]

    def exist(self, key='id', value=None, table=None, release_lock=True):
        lock = self.get_lock()
        try:
            if table is None:
                table = self.table
            if value is None:
                value = self.id
            sql = "SELECT EXISTS(SELECT 1 FROM " + table + \
                " WHERE {}=?);".format(key)
            self.execute(sql, (value,), release_lock=False)
            return bool(self.cur.fetchall()[0][0])
        finally:
            if release_lock:
                lock.release()

    def get(self):
        sql = "SELECT * FROM {} WHERE id=?".format(self.table)
        try:
            rows = self.sql(sql, (self.id,))
        except Exception as e:
            log("", "\nError on id:", self.id,
                "- table:", self.table, "- sql:", sql)
            raise e
        if len(rows) == 0:
            out = {}  # Not found
        else:
            row = rows[0]
            keys = self.keys()
            out = dict(zip(keys, row))
        if self.table == "anime":
            return Anime(out)
        elif self.table == "characters":
            return Character(out)
        else:
            return out

    def getId(self, apiKey, apiId, table="anime"):
        if table == "anime":
            index = "indexList"
        elif table == "characters":
            index = "charactersIndex"
        sql = "SELECT id FROM {} WHERE {}=?;".format(index, apiKey)
        ids = self.sql(sql, (apiId,))
        if len(ids) > 0:
            return ids[0][0]
        else:
            isql = "INSERT INTO {}({}) VALUES(?)".format(index, apiKey)
            try:
                self.execute(isql, (apiId,))
            except sqlite3.IntegrityError as e:
                sql = "SELECT id FROM {} WHERE {}=?;".format(index, apiKey)
                ids = self.sql(sql, (apiId,))
                return ids[0][0]
            self.save()
            ids = self.sql(sql, (apiId,))
            return ids[0][0]

    def update(self, key, data, save=True):
        sql = "UPDATE " + self.table + " SET {} = ? WHERE id = ?".format(key)
        cur = self.con.cursor()
        cur.execute(sql, (data, self.id))
        if save:
            self.con.commit()

    def get_lock(self):
        if 'db_lock' not in globals().keys():
            lock = threading.Lock()
            globals()['db_lock'] = lock
            return lock
        else:
            return globals()['db_lock']

    def execute(self, sql, *args, release_lock=True, ignore_lock=False):
        lock = self.get_lock()
        try:
            if not ignore_lock:
                lock.acquire(True)
            self.cur.execute(sql, *args)
        except sqlite3.OperationalError as e:
            if e.args == ('database is locked',):
                log("[ERROR] - Database is locked!")
                raise e
            else:
                log(e, sql, args)
                raise e
        except sqlite3.InterfaceError as e:
            log(e, sql, *args)
            raise e
        finally:
            if release_lock:
                lock.release()

    def set(self, data, save=True):
        if len(data) == 0:
            return
        keys = []
        values = []
        self.updateKeys()
        for k, v in data.items():
            if (self.table != "anime" or k in self.tablekeys):
                keys.append(k)
                if type(v) in (dict, list):
                    values.append(json.dumps(v))
                elif isinstance(v, bool):
                    values.append(int(v))
                else:
                    values.append(v)

        if self.exist("id", data["id"], release_lock=False):
            sql = "UPDATE " + self.table + " SET " + \
                "{} = ?," * (len(keys) - 1) + "{} = ? WHERE {} = ?"
            sql = sql.format(*keys, "id")
            self.execute(sql, (*values, data["id"]), release_lock=False, ignore_lock=True)
        else:
            sql = "INSERT INTO " + self.table + \
                "(" + "{}," * (len(keys) - 1) + \
                  "{}) VALUES(" + "?," * (len(keys) - 1) + "?)"
            sql = sql.format(*keys)
            try:
                self.execute(sql, (*values,), release_lock=False, ignore_lock=True)
            except Exception as e:
                log(sql)
                for v in values:
                    log(v)
                raise e
        if save:
            self.con.commit()
        lock = self.get_lock()
        lock.release()

    def insert(self, data, save=True):
        keys = ['id']
        values = [self.id]
        for k, v in data.items():
            if k != 'id':
                keys.append(k)
                if type(v) in (dict, list):
                    values.append(json.dumps(v))
                elif isinstance(v, bool):
                    values.append(int(v))
                else:
                    values.append(v)

        sql = "INSERT INTO " + self.table + \
            "(" + "{}," * (len(keys) - 1) + \
              "{}) VALUES(" + "?," * (len(keys) - 1) + "?)"
        sql = sql.format(*keys)
        self.execute(sql, (*values,))
        if save:
            self.con.commit()

    # TODO
    def addRelated(self, id, relation, rel_id):
        sql = "SELECT rel_id FROM related WHERE id=? AND relation=?"
        self.execute(sql, (str(id), relation))
        out = self.cur.fetchall()
        rel_ids = [rel_id]
        if len(out) >= 1:
            for comp_ids in out:
                comp_ids = json.loads(comp_ids[0])
                if rel_id in comp_ids:
                    rel_ids = comp_ids
                else:
                    rel_ids += comp_ids
            sql = "UPDATE related SET rel_id = ? WHERE id = ? AND relation=?"
        else:
            sql = "INSERT INTO related(rel_id,id,relation) VALUES(?,?,?)"
        self.execute(sql, (json.dumps(rel_ids), str(id), relation))
        self.save()
        return len(out) == 0

    def remove(self, key=None, save=True):
        cur = self.con.cursor()
        if key is None:
            sql = "DELETE FROM anime WHERE id=?"
            cur.execute(sql, (self.id,))
            sql = "DELETE FROM searchTitles WHERE id=?"
            cur.execute(sql, (self.id,))
            sql = "DELETE FROM indexList WHERE id=?"
            cur.execute(sql, (self.id,))
        else:
            self.update(key, None)
        if save:
            self.con.commit()

    def filter(self, table=None, sort="",
               range=(0, 50), order=None, filter=None):
        if table is not None:
            self.table = table
        limit = "\nLIMIT {start},{stop}".format(
            start=range[0], stop=range[1]) if range else ""
        filter = "\nWHERE {filter}".format(filter=filter) if filter else ""
        if order is None:
            sort = "DESC" if sort is None else sort
            order = "anime.date_from"
        sql = """SELECT anime.*,tag.tag,like.like FROM anime LEFT JOIN tag using(id) LEFT JOIN like using(id) {filter} \nORDER BY {order} {sort} {limit};""".format(
            filter=filter, order=order, sort=sort, limit=limit)
        self.updateKeys()
        lock = self.get_lock()
        try:
            self.execute(sql, release_lock=False)
            data_list = self.cur.fetchall()
        finally:
            lock.release()
        keys = list(self.tablekeys) + ['tag', 'like']
        for data in data_list:
            yield Anime(dict(zip(keys, data)))

    def sql(self, sql, values=[], save=False, iterate=False):
        def sql_iterate(cur):
            for row in cur:
                yield row
        if not isinstance(values, list):
            values = list(values)

        lock = self.get_lock()
        try:
            self.execute(sql, values, release_lock=False)
        except sqlite3.ProgrammingError as e:
            log(sql, values, list(map(type, values)))
            raise e
        else:
            if save:
                self.save()
            else:
                if iterate:
                    return sql_iterate(self.cur)
                else:
                    return self.cur.fetchall()
        finally:
            lock.release()

    def save(self):
        self.con.commit()


if __name__ == "__main__":
    from animeManager import Manager
    m = Manager()
