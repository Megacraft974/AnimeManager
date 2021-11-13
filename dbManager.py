import sqlite3
import json
import os
from classes import Anime, Character


class db():
    '''Database manager using sqlite3'''

    def __init__(self, path):
        self.path = path
        if not os.path.exists(self.path):
            self.createNewDb()
        self.con = sqlite3.connect(path, check_same_thread=False)
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        self.table = "anime"
        self.updateKeys()

    def createNewDb(self):
        open(self.path, "w")
        self.con = sqlite3.connect(self.path)
        self.con.row_factory = sqlite3.Row
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

    def setId(self, id):
        self.id = id
        return self

    def setTable(self, table):
        self.table = table
        return self

    def updateKeys(self):
        self.tablekeys = list(d[1] for d in self.sql(
            "PRAGMA table_info({});".format(self.table), iterate=True))

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
            e = next(self.sql(sql, (self.id,), iterate=True), ("NONE",))
            return e[0]
        except BaseException:
            print("", "\nError on id", self.id,
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

    def keys(self):
        self.updateKeys()
        return self.tablekeys

    def values(self):
        cur = self.con.cursor()
        cur.execute("SELECT * FROM " + self.table +
                    " WHERE id=?", (str(self.id),))
        rows = cur.fetchall()
        if len(rows) >= 1:
            return rows[0]
        else:
            return []

    def items(self):
        self.updateKeys()
        return [(self.tablekeys[i], v) for i, v in enumerate(self.values())]

    def new(self):
        # Placeholder
        return db(self.path).setId(self.id).setTable(self.table)

    def exist(self, key='id', value=None, table=None):
        if table is None:
            table = self.table
        if value is None:
            value = self.id
        sql = "SELECT EXISTS(SELECT 1 FROM " + table + \
            " WHERE {}=?);".format(key)
        self.execute(sql, (value,))
        return bool(self.cur.fetchall()[0][0])

    def get(self):
        if not self.exist():
            print(self.id, "doesn't exist in table", self.table)
            return {}
        sql = "SELECT * FROM {} WHERE id=?".format(self.table)
        try:
            row = self.sql(sql, (self.id,))[0]
        except Exception as e:
            print("", "\nError on id", self.id,
                  "table", self.table, "sql", sql)
            raise e
        # rows = self.cur.fetchall()
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
        # e = next(self.sql(sql,(apiId,),iterate=True),None)
        e = self.sql(sql, (apiId,))
        if len(e) == 0:
            e = None
        else:
            e = e[0]
        if e is not None:
            return e[0]
        else:
            isql = "INSERT INTO {}({}) VALUES(?)".format(index, apiKey)
            self.execute(isql, (apiId,))
            self.save()
            e = next(self.sql(sql, (apiId,), iterate=True))[0]
            return e

    def update(self, key, data, save=True):
        sql = "UPDATE " + self.table + " SET {} = ? WHERE id = ?".format(key)
        cur = self.con.cursor()
        cur.execute(sql, (data, self.id))
        if save:
            self.con.commit()

    def execute(self, *args):
        try:
            return self.cur.execute(*args)
        except sqlite3.OperationalError as e:
            if e.args == ('database is locked',):
                print("[ERROR] - Database is locked!", flush=True)
                raise e
            else:
                print(args)
                raise e
        except sqlite3.InterfaceError as e:
            print(*args)
            raise e

    def set(self, data, save=True):
        if len(data) == 0:
            return
        keys = []
        values = []
        for k, v in data.items():
            if (self.table != "anime" or k in self.tablekeys):
                keys.append(k)
                if type(v) in (dict, list):
                    values.append(json.dumps(v))
                elif type(v) == bool:
                    values.append(int(v))
                else:
                    values.append(v)

        if self.exist("id", data["id"]):
            sql = "UPDATE " + self.table + " SET " + \
                "{} = ?," * (len(keys) - 1) + "{} = ? WHERE {} = ?"
            sql = sql.format(*keys, "id")
            self.execute(sql, (*values, data["id"]))
        else:
            sql = "INSERT INTO " + self.table + \
                "(" + "{}," * (len(keys) - 1) + \
                  "{}) VALUES(" + "?," * (len(keys) - 1) + "?)"
            sql = sql.format(*keys)
            try:
                self.execute(sql, (*values,))
            except Exception as e:
                print(sql)
                for v in values:
                    print(v)
                raise e
        if save:
            self.con.commit()

    def insert(self, data, save=True):
        keys = ['id']
        values = [self.id]
        for k, v in data.items():
            if k != 'id':
                keys.append(k)
                if type(v) in (dict, list):
                    values.append(json.dumps(v))
                elif type(v) == bool:
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

    def all(self, table=None, **args):
        if table is not None:
            self.table = table
        return {id: self.setId(id).new() for id in self.allkeys(**args)}

    def allkeys(self, table=None, sort=False,
                range=None, order=None, filter=None):
        if table is not None:
            self.table = table
        if range == True or sort:
            join = "\nJOIN anime on {table}.id = anime.id ".format(
                table=self.table) if self.table != "anime" else ""
            limit = "\nLIMIT {start},{stop}".format(
                start=range[0], stop=range[1]) if range else ""
            filter = "\nWHERE {filter}".format(filter=filter) if filter else ""
            if order is None:
                sort = "DESC" if sort == True else sort
                order = "anime.date_from"
            else:
                sort = ""
            sql = """SELECT {table}.id FROM {table} {join} {filter} \nORDER BY {order} {sort} {limit};""".format(
                table=self.table, join=join, filter=filter, sort=sort, order=order, limit=limit)
            rows = self.sql(sql, iterate=True)
        else:
            rows = self.request('id')
        for id in rows:
            yield id

    def allvalues(self, table=None, **args):
        if table is not None:
            self.table = table
        return (dict(self.setId(id)) for id in self.allkeys(**args))

    def request(self, data, table=None):
        if table is not None:
            self.table = table
        sql = "SELECT {} FROM " + self.table
        sql = sql.format(data)
        self.execute(sql)
        for row in self.cur:
            yield row

    def sql(self, sql, values=[], save=False, iterate=False):
        def sql_iterate(cur):
            for row in cur:
                yield row
        if type(values) != list:
            values = list(values)
        try:
            self.execute(sql, values)
        except sqlite3.ProgrammingError as e:
            print(sql, values, list(map(type, values)))
            raise e
        if save:
            self.save()
        else:
            if iterate:
                return sql_iterate(self.cur)
            else:
                rows = self.cur.fetchall()
                return rows

    def save(self):
        self.con.commit()


if __name__ == "__main__":
    from animeManager import Manager
    m = Manager()
