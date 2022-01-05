import auto_launch

import sqlite3
import json
import os
import traceback
import threading
import queue
import time
from classes import Anime, Character, NoneDict, AnimeList, Item, LockWrapper
from logger import log, Logger


class db():
    '''Database manager using sqlite3'''

    def __init__(self, path):
        self.path = path
        self.remote_lock = LockWrapper(threading.RLock())
        if not os.path.exists(self.path):
            self.createNewDb()
        self.con = sqlite3.connect(path)
        # self.con.row_factory = sqlite3.Row
        sqlite3.register_adapter(bool, int)
        sqlite3.register_converter("BOOLEAN", lambda v: bool(int(v)))
        self.cur = self.con.cursor()
        table = "anime"
        self.alltable_keys = {}
        self.log_commands = False

    def createNewDb(self):
        open(self.path, "w")
        self.con = sqlite3.connect(self.path)
        # self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        commands = ('''CREATE TABLE "anime" (
                        "id"    INTEGER NOT NULL UNIQUE,
                        "title" TEXT,
                        "picture"   TEXT,
                        "date_from" TEXT,
                        "date_to"   TEXT,
                        "synopsis"  TEXT,
                        "episodes"  INTEGER,
                        "duration"  INTEGER,
                        "rating"    TEXT,
                        "status"    TEXT,
                        "broadcast" TEXT,
                        "last_seen" INTEGER,
                        "trailer"   TEXT,
                        "like"  INTEGER,
                        "tag"   TEXT,
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
                    '''CREATE TABLE "genresIndex" (
                        "id"    INTEGER NOT NULL UNIQUE,
                        "mal_id"    INTEGER,
                        "kitsu_id"  INTEGER,
                        "name"  INTEGER,
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
                    '''CREATE TABLE "tag" (
                        "id"    INTEGER NOT NULL UNIQUE,
                        "tag"    TEXT
                    )''',
                    '''CREATE TABLE "genres" (
                        "id"    INTEGER NOT NULL,
                        "value" INTEGER NOT NULL
                    )''',
                    '''CREATE TABLE "title_synonyms" (
                        "id"    INTEGER NOT NULL,
                        "value" TEXT NOT NULL
                    )''',
                    '''CREATE TABLE "torrents" (
                        "id"    INTEGER NOT NULL,
                        "value" TEXT NOT NULL
                    )''')
        with self.get_lock():
            for c in commands:
                self.cur.execute(c)
            self.save()
        # self.createGenres()

    def close(self):
        with self.get_lock():
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

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
        return False

    def keys(self, table):
        return self.updateKeys(table)

    def values(self):
        with self.get_lock():
            self.cur.execute("SELECT * FROM " + table + " WHERE id=?", (str(id),))
            rows = cur.fetchall()
        if len(rows) >= 1:
            return rows[0]
        else:
            return []

    def items(self, table):
        self.updateKeys(table)
        return [(self.tablekeys[i], v) for i, v in enumerate(self.values())]

    def exist(self, id, table, key='id'):
        with self.get_lock():
            sql = "SELECT EXISTS(SELECT 1 FROM " + table + \
                " WHERE {}=?);".format(key)
            self.execute(sql, (id,))
            return bool(self.cur.fetchall()[0][0])

    def get(self, id, table):
        sql = "SELECT * FROM {} WHERE id=?".format(table)
        try:
            rows = self.sql(sql, (id,), to_dict=True)
        except Exception:
            log("", "\nError on id:", id,
                "- table:", table, "- sql:", sql)
            raise
        if len(rows) == 0:
            out = {}  # Not found
        else:
            out = rows[0]
            # keys = self.keys(table)
            # out = dict(zip(keys, row))
        if table == "anime":
            return self.get_all_metadata(Anime(out))
        elif table == "characters":
            return self.get_all_metadata(Character(out))
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
            with self.get_lock():
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
        with self.get_lock():
            self.cur.execute(sql, (data, id))
            if save:
                self.save()

    def get_lock(self):
        if 'db_lock' not in globals().keys():
            lock = threading.RLock()
            globals()['db_lock'] = lock
            return lock
        else:
            return globals()['db_lock']

    def execute(self, sql, *args):
        try:
            with self.get_lock():
                if self.log_commands:
                    log(sql, *args)
                self.cur.execute(sql, *args)
        except sqlite3.OperationalError as e:
            if e.args == ('database is locked',):
                log("[ERROR] - Database is locked! - On execute({}{}{})".format(sql, ", " if len(args) > 0 else "", ", ".join(map(str, args))))
                raise
            else:
                log(e, sql, args)
                raise
        except sqlite3.InterfaceError as e:
            log(e, sql, *args)
            raise
        except sqlite3.ProgrammingError as e:
            log(e, sql, *args)
            raise

    def executemany(self, sql, *args):
        with self.get_lock():
            try:
                self.cur.executemany(sql, *args)
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
            except sqlite3.ProgrammingError as e:
                log(e, sql, *args)
                raise

    def set(self, data, table, save=True):
        if len(data) == 0:
            return
        keys = []
        values = []
        with self.get_lock():
            self.updateKeys(table)
            if isinstance(data, Item):
                data, meta = data.save_format()
            else:
                meta = []
            for k, v in data.items():
                if (table not in ("anime", "characters") or k in self.tablekeys):
                    if type(v) in (dict, list):
                        meta[k] = v
                    else:
                        keys.append(k)
                        values.append(v)

            if self.exist(data["id"], table, "id"):
                sql = "UPDATE " + table + " SET " + \
                    ",".join(["{} = ?"] * len(keys)) + " WHERE {} = ?;"
                sql = sql.format(*keys, "id")
                self.execute(sql, (*values, data["id"]))
            else:
                sql = "INSERT INTO " + table + \
                    "(" + ",".join(["{}"] * len(keys)) + \
                      ") VALUES(" + ",".join("?" * len(keys)) + ");"
                sql = sql.format(*keys)
                self.execute(sql, (*values,))

            self.save_metadata(data["id"], meta)
            if save:
                self.save()

    def insert(self, data, table, save=True):
        keys, values, meta = [], [], {}
        for k, v in data.items():
            if type(v) in (dict, list):
                meta[k] = v
            else:
                keys.append(k)
                values.append(v)

        sql = "INSERT INTO " + table + \
            "(" + ",".join(["{}"] * len(keys)) + \
              ") VALUES(" + ",".join("?" * len(keys)) + ");"
        sql = sql.format(*keys)
        with self.get_lock():
            self.execute(sql, (*values,))
            if save:
                self.save()

    def remove(self, key=None, id=None, table=None, save=True):
        with self.get_lock():
            if key is None:
                sql = """
                    DELETE FROM anime WHERE id={id};
                    DELETE FROM title_synonyms WHERE id={id};
                    DELETE FROM torrents WHERE id={id};
                    DELETE FROM genres WHERE id={id};
                    DELETE FROM indexList WHERE id={id};
                    DELETE FROM characters WHERE anime_id={id};
                """
                # TODO
                self.cur.executescript(sql.format(id=id))
            else:
                # self.update(key, None, id, table)
                self.set({"id": id, key: None}, table, save=False)
            if save:
                self.save()

    def filter(self, table=None, sort=None, range=(0, 50), order=None, filter=None):

        if table is not None:
            table = table

        if range is not None:
            limit = "\nLIMIT {start},{stop}".format(
                start=range[0],
                stop=range[1])
        else:
            limit = ""

        if filter is not None:
            filter = "\nWHERE {filter}".format(filter=filter)
        else:
            filter = ""

        if order is None:
            if sort is None:
                sort = "DESC"
            order = "anime.date_from"

        sql = """
            SELECT anime.*,tag.tag,like.like
            FROM anime LEFT JOIN tag using(id)
            LEFT JOIN like using(id)
            {filter}
            ORDER BY {order}
            {sort} {limit};
        """.format(
            filter=filter,
            order=order,
            sort=sort,
            limit=limit)

        self.updateKeys("anime")
        keys = list(self.tablekeys) + ['tag', 'like']
        with self.get_lock():
            self.updateKeys(table="anime")
            self.execute(sql)
            data_list = self.cur.fetchall()

        return AnimeList([self.get_all_metadata(Anime(keys=keys, values=data)) for data in data_list])
        # return (Anime(keys=keys, values=data) for data in data_list)

    def sql(self, sql, values=[], save=False, to_dict=False, iterate=False):
        def cur_iterator():
            for row in self.cur:
                yield row
        values = list(values)  # dict_keys type raise a ValueError

        with self.get_lock():
            try:
                self.execute(sql, values)
            except sqlite3.ProgrammingError:
                log(sql, list(values), list(map(type, values)))
                raise
            else:
                if save:
                    self.save()
                else:
                    if iterate:
                        return cur_iterator()
                    elif to_dict:
                        keys = (k[0] for k in self.cur.description)
                        out = []
                        for data in self.cur:
                            out.append(NoneDict(keys=(k[0] for k in self.cur.description), values=data))
                        return out
                    else:
                        return self.cur.fetchall()

    def save(self):
        with self.get_lock():
            if self.log_commands:
                log("SAVE animeData.db")
            try:
                self.con.commit()
            except sqlite3.OperationalError as e:
                if e.args == ('database is locked',):
                    log("[ERROR] - Database is locked! - On save()")
                    raise
                else:
                    raise

    def close(self):
        self.cur.close()

    def get_all_metadata(self, item):
        for key in item.metadata_keys:
            item[key] = lambda path=self.path, id=item.id, key=key: thread_safe_db(path).get_metadata(id, key)

        return item

    def get_metadata(self, id, key):
        data = self.sql("SELECT value FROM {} WHERE id=?;".format(key), (id,))
        return [e[0] for e in data]

    def save_metadata(self, id, meta):
        if not meta:
            return
        with self.get_lock():
            c = 0
            for key, values in meta.items():
                if type(values) not in {list, set, tuple}:
                    raise TypeError("Values must be of type list, not", type(values))
                db_values = [e[0] for e in self.sql("SELECT value FROM {} WHERE id=?".format(key), (id,))]
                toUpdate = []
                for v in values:
                    if v:
                        if v not in db_values:
                            toUpdate.append((id, v))
                        else:
                            db_values.remove(v)

                self.executemany("INSERT INTO {}(id, value) VALUES (?,?)".format(key), toUpdate)
                self.executemany("DELETE FROM {} WHERE id=? AND value=?".format(key), ((id, value) for value in db_values))
                c += len(toUpdate) + len(db_values)
            return c


class thread_safe_db(Logger):
    def __init__(self, path):
        super().__init__()
        if 'database_main_tasks_queue' in globals().keys():
            main = globals()['database_main_thread']
            self.db = main.db
            self.lock = main.lock
            self.tasks = main.tasks
            self.db_thread = main.db_thread
        else:
            self.tasks = queue.LifoQueue()
            self.ready_flag = threading.Event()
            self.db_thread = threading.Thread(target=self.start_db_thread, args=(path,))
            self.db_thread.start()
            self.ready_flag.wait()
            del self.ready_flag
            globals()['database_main_thread'] = self
            self.log("THREAD", "Started db thread")

    def start_db_thread(self, path):
        self.db = db(path)
        self.ready_flag.set()
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
        try:
            self.db.close()
        except Exception as e:
            self.log("THREAD", "[ERROR] - While closing db:", e)
        self.log("THREAD", "Stopped db thread")

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

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
        return False

    def get_lock(self):
        try:
            return self.db.remote_lock
        except:
            log("[ERROR] - No lock found!", self.db, dir(self.db))
            raise

    def close(self):
        self.tasks.put("STOP")
        self.db_thread.join()

    def task_planner(self, name, *args, **kwargs):
        with self.get_lock():
            output = queue.Queue()
            if False:  # Used for logging
                log("sql req: db.{}({}{}{})".format(
                    name,
                    ", ".join(map(str, args)),
                    ", " if len(args) > 0 and len(kwargs) > 0 else "",
                    ", ".join(map(
                        lambda e: "{}={}".format(
                            e[0],
                            str(e[1])
                        ),
                        kwargs.items()
                    ))
                ))
            self.tasks.put((output, name, args, kwargs))
            out = output.get()
            if isinstance(out, Exception):
                raise out
            else:
                return out