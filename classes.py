import queue
import threading
import time
import traceback
import requests

from logger import log


class Item(dict):
    def __init__(self, data=None):
        super().__init__(self)
        if not hasattr(self, "data_keys"):
            self.data_keys = ()
        if not hasattr(self, "meta_data_keys"):
            self.meta_data_keys = ()
        if data is not None:
            self.__add__(data)

    def __getattr__(self, key):
        if key in ("data_keys", "meta_data_keys"):
            return self.__dict__["data_keys"]
        if key in self.data_keys and key not in self.keys():
            return None
        else:
            return self[key]

    def __setattr__(self, key, value):
        if key in ("data_keys", "meta_data_keys"):
            self.__dict__["data_keys"] = value
            return
        if key in self.data_keys:
            self[key] = value
        else:
            log(type(self), key, value)

    def __add__(self, e):
        if e is None:
            return
        if not hasattr(e, 'items'):
            raise TypeError("Cannot merge '{}' and '{}'".format(
                type(self).__name__, type(e).__name__))
        for k, v in e.items():
            if k not in self.keys():
                self[k] = v
        return self

    def save_format(self):
        main_keys = {}
        meta_data = {}
        for key, value in self.items():
            if key in self.meta_data_keys:
                meta_data[key] = {}
                for e in value:
                    meta_data[key] = {'id': self.id, key: e}
            else:
                main_keys[key] = value
        return main_keys, meta_data


class Anime(Item):
    def __init__(self, data=None):
        self.data_keys = (
            'date_from',
            'date_to',
            'duration',
            'episodes',
            'genres',
            'id',
            'picture',
            'rating',
            'status',
            'synopsis',
            'title',
            'title_synonyms',
            'trailer',
            'torrent')
        self.meta_data_keys = ('title_synonyms', 'genres', 'torrent')
        super().__init__(data)


class Torrent(Item):
    def __init__(self, data=None):
        self.data_keys = ('filename', 'torrent_url',
                          'seeds', 'leechs', 'file_size')
        super().__init__(data)


class Character(Item):
    def __init__(self, data=None):
        self.data_keys = ('id', 'anime_id', 'role', 'name',
                          'picture', 'desc', 'animeography')
        super().__init__(data)


class ItemList(queue.Queue):
    def __init__(self, *sources):
        self.list = []

        self.stop = False
        self.new_elem_event = {"enabled": False, "event": threading.Event()}

        self.sources = []
        self.sourceThreads = []
        self.ids = []

        if not hasattr(self, "identifier"):
            self.identifier = lambda e: e

        for s in sources:
            self.addSource(s)

    def __contains__(self, e):
        return e in self.list

    def __iter__(self, timeout=None):
        while not self.empty():
            e = self.get(timeout)
            if e is not None:
                yield e

    def sourceListener(self, s):
        try:
            iterator = iter(s)
        except TypeError:
            iterator = s
        while not self.stop:
            try:
                e = next(iterator)
                # log("S {},".format(e))
            except StopIteration:
                self.sources.remove(s)
                break
            except requests.exceptions.ConnectionError:
                log("Error on ItemList iterator: No internet connection!")
            except Exception as e:
                log("Error on ItemList iterator", s, traceback.format_exc())
                self.sources.remove(s)
                break
            else:
                id = self.identifier(e)
                if id not in self.ids:
                    self.list.append(e)
                    self.ids.append(id)
                    if self.new_elem_event["enabled"]:
                        self.new_elem_event["event"].set()
                        self.new_elem_event["enabled"] = False

    def queueListener(self, que, threads):
        while not que.empty() or any(t.is_alive() for t in threads):
            try:
                s = que.get(timeout=0.01)
            except queue.Empty:
                pass
            else:
                self.addSource(s)

    def addSource(self, source):
        if isinstance(source, type(self)):
            return
        if isinstance(source, tuple) and isinstance(source[0], queue.Queue):
            # self.sources.append(source)
            t = threading.Thread(target=self.queueListener, args=source)
            t.start()
            self.sourceThreads.append(t)
        else:
            self.sources.append(source)
            t = threading.Thread(target=self.sourceListener, args=(source,))
            t.start()
            self.sourceThreads.append(t)

    def get(self, timeout=None, default=None):
        if len(self.list) > 0:
            e = self.list.pop(0)
            return e
        else:
            return self.get_from_sources(timeout, default)

    def get_from_sources(self, timeout=None, default=None):
        self.new_elem_event["enabled"] = True
        if not self.new_elem_event["event"].wait(timeout=timeout):
            log("Timed out")
            return default  # Timed out

        if len(self.list) > 0:
            e = self.list.pop(0)
            return e

    def empty(self):
        return len(self.sources) == 0 and len(self.list) == 0


class AnimeList(ItemList):
    def __init__(self, sources):
        super().__init__(self, sources)
        self.identifier = lambda a: a["id"]


class TorrentList(ItemList):
    def __init__(self, sources):
        super().__init__(self, sources)
        self.identifier = lambda t: t["torrent_url"]


class CharacterList(ItemList):
    def __init__(self, sources):
        super().__init__(self, sources)
        self.identifier = lambda c: c["id"]


if __name__ == "__main__":
    def slow_iter(msg, t=1, length=10):
        for i in range(length):
            time.sleep(t)
            # log(msg+str(i))
            yield msg + str(i)
    items = ItemList(range(5), ('a', 'b', 'c'), slow_iter(
        "haha", 1, 3), slow_iter("hehe", 5, 2))
    for e in items:
        log(e)

    # a = Anime()
    # log(a.title)
    # a.title = "jujutsu"
    # a["synopsis"] = "salut"
    # log(a.title,a.synopsis)
