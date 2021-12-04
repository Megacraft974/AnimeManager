import sqlite3
import json
import os
import traceback
import threading
import queue
import time
from classes import Anime, Character, NoneDict
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
        table = "anime"
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

    def updateKeys(self, table):
        if table not in self.alltable_keys:
            self.tablekeys = list(d[1] for d in self.sql(
                "PRAGMA table_info({});".format(table)))
            self.alltable_keys[table] = self.tablekeys
        else:
            self.tablekeys = self.alltable_keys[table]
        return self.tablekeys

    def __call__(self, id=None, table=None):
        return self.get(id, table)

    def __setitem__(self, key, data):
        self.update(key, data)

    def __len__(self):
        return len(self.__repr__())

    def __contains__(self, item):
        return item in self.__repr__()

    def __iter__(self, table):
        self.updateKeys(table)
        for k in self.tablekeys:
            yield k

    def __str__(self):
        return str(self.__repr__())

    def __del__(self):
        self.cur.close()

    def keys(self, table):
        return self.updateKeys(table)

    def values(self):
        cur = self.con.cursor()
        cur.execute("SELECT * FROM " + table + " WHERE id=?", (str(id),))
        rows = cur.fetchall()
        if len(rows) >= 1:
            return rows[0]
        else:
            return []

    def items(self, table):
        self.updateKeys(table)
        return [(self.tablekeys[i], v) for i, v in enumerate(self.values())]

    def exist(self, id, table, key='id'):
        lock = self.get_lock()
        try:
            lock.acquire(True)
            sql = "SELECT EXISTS(SELECT 1 FROM " + table + \
                " WHERE {}=?);".format(key)
            self.execute(sql, (id,))
            return bool(self.cur.fetchall()[0][0])
        finally:
            lock.release()

    def get(self, id, table):
        sql = "SELECT * FROM {} WHERE id=?".format(table)
        try:
            rows = self.sql(sql, (id,))
        except Exception:
            log("", "\nError on id:", id,
                "- table:", table, "- sql:", sql)
            raise
        if len(rows) == 0:
            out = {}  # Not found
        else:
            row = rows[0]
            keys = self.keys(table)
            out = dict(zip(keys, row))
        if table == "anime":
            return Anime(out)
        elif table == "characters":
            return Character(out)
        else:
            return NoneDict(out)

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

    def update(self, key, data, id, table, save=True):
        sql = "UPDATE " + table + " SET {} = ? WHERE id = ?".format(key)
        cur = self.con.cursor()
        cur.execute(sql, (data, id))
        if save:
            self.con.commit()

    def get_lock(self):
        if 'db_lock' not in globals().keys():
            lock = threading.RLock()
            globals()['db_lock'] = lock
            return lock
        else:
            return globals()['db_lock']

    def execute(self, sql, *args):
        lock = self.get_lock()
        try:
            lock.acquire(True)
            self.cur.execute(sql, *args)
        except sqlite3.OperationalError as e:
            if e.args == ('database is locked',):
                log("[ERROR] - Database is locked!")
                raise
            else:
                log(e, sql, args)
                raise
        except sqlite3.InterfaceError as e:
            log(e, sql, *args)
            raise
        finally:
            lock.release()

    def set(self, data, table, save=True):
        if len(data) == 0:
            return
        keys = []
        values = []
        self.updateKeys(table)
        for k, v in data.items():
            if (table != "anime" or k in self.tablekeys):
                keys.append(k)
                if type(v) in (dict, list):
                    values.append(json.dumps(v))
                elif isinstance(v, bool):
                    values.append(int(v))
                else:
                    values.append(v)
        lock = self.get_lock()
        try:
            lock.acquire(True)
            if self.exist(data["id"], table, "id"):
                sql = "UPDATE " + table + " SET " + \
                    "{} = ?," * (len(keys) - 1) + "{} = ? WHERE {} = ?"
                sql = sql.format(*keys, "id")
                self.execute(sql, (*values, data["id"]))
            else:
                sql = "INSERT INTO " + table + \
                    "(" + "{}," * (len(keys) - 1) + \
                      "{}) VALUES(" + "?," * (len(keys) - 1) + "?)"
                sql = sql.format(*keys)
                try:
                    self.execute(sql, (*values,))
                except Exception:
                    log("Error in db.set() -", sql)
                    for v in values:
                        log("Error in db.set() - values:", v)
                    raise
            if save:
                self.con.commit()
        finally:
            lock.release()

    def insert(self, data, table, save=True):
        keys, values = [], []
        for k, v in data.items():
            keys.append(k)
            if type(v) in (dict, list):
                values.append(json.dumps(v))
            elif isinstance(v, bool):
                values.append(int(v))
            else:
                values.append(v)

        sql = "INSERT INTO " + table + \
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

    def remove(self, key=None, id=None, table=None, save=True):
        cur = self.con.cursor()
        if key is None:
            sql = "DELETE FROM anime WHERE id=?"
            cur.execute(sql, (id,))
            sql = "DELETE FROM searchTitles WHERE id=?"
            cur.execute(sql, (id,))
            sql = "DELETE FROM indexList WHERE id=?"
            cur.execute(sql, (id,))
        else:
            self.update(key, None, id, table)
        if save:
            self.con.commit()

    def filter(self, table=None, sort="",
               range=(0, 50), order=None, filter=None):
        if table is not None:
            table = table
        limit = "\nLIMIT {start},{stop}".format(
            start=range[0], stop=range[1]) if range else ""
        filter = "\nWHERE {filter}".format(filter=filter) if filter else ""
        if order is None:
            sort = "DESC" if sort is None else sort
            order = "anime.date_from"
        sql = """SELECT anime.*,tag.tag,like.like FROM anime LEFT JOIN tag using(id) LEFT JOIN like using(id) {filter} \nORDER BY {order} {sort} {limit};""".format(
            filter=filter, order=order, sort=sort, limit=limit)
        self.updateKeys(table="anime")
        lock = self.get_lock()
        try:
            lock.acquire(True)
            self.execute(sql)
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
            lock.acquire(True)
            self.execute(sql, values)
        except sqlite3.ProgrammingError:
            log(sql, values, list(map(type, values)))
            raise
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


class thread_safe_db():
    def __init__(self, path):
        if 'database_main_tasks_queue' in globals().keys():
            main = globals()['database_main_thread']
            self.db = main.db
            self.tasks = main.tasks
            self.db_thread = main.db_thread
        else:
            self.tasks = queue.LifoQueue()
            globals()['database_main_thread'] = self
            self.db_thread = threading.Thread(target=self.start_db_thread, args=(path,))
            self.db_thread.start()

    def start_db_thread(self, path):
        self.db = db(path)
        task = self.tasks.get()
        while task != "STOP":
            output, name, args, kwargs = task
            try:
                out = getattr(self.db, name)(*args, **kwargs)
            except Exception as e:
                output.put(e)
            else:
                output.put(out)
            task = self.tasks.get()
        print("Stopped!")

    def __getattr__(self, a):
        return lambda *args, **kwargs: self.task_planner(a, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        # self.__dict__['db'].__call__(*args, **kwargs)
        return self.task_planner("__call__", *args, **kwargs)

    def __len__(self, *args, **kwargs):
        return self.task_planner("__len__", *args, **kwargs)

    def __contains__(self, *args, **kwargs):
        return self.task_planner("__contains__", *args, **kwargs)

    def __iter__(self, *args, **kwargs):
        return self.task_planner("__iter__", *args, **kwargs)

    def __str__(self, *args, **kwargs):
        return self.task_planner("__str__", *args, **kwargs)

    def close(self):
        print("Deleted")
        self.tasks.put("STOP")

    def task_planner(self, name, *args, **kwargs):
        # start = time.time()
        output = queue.Queue()
        self.tasks.put((output, name, args, kwargs))
        out = output.get()
        if isinstance(out, Exception):
            raise out
        else:
            # print(str(round(time.time() - start, 5)).ljust(8, "0") + " - " + name.ljust(20) + ("|" * int((time.time() - start) * 1000)) + "\n", end="")
            return out


if __name__ == "__main__":
    # from animeManager import Manager
    # m = Manager()

    appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
    dbPath = os.path.join(appdata, "animeData.db")

    sql = "select 1 from anime;"
    db = db(dbPath)
    data = thread_safe_db(dbPath)

    a = db.execute(sql)
    b = data.execute(sql)
    print(a == b)
    data.close()
