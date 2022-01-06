import auto_launch

import queue
import threading
import time
import traceback
import requests

from logger import log


class Item(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(self)
        if "data_keys" not in self.__dict__.keys():
            self.data_keys = ()
        if "metadata_keys" not in self.__dict__.keys():
            self.metadata_keys = ()
        self.__add__(*args, **kwargs)

    def __getattr__(self, key):
        if key in ("data_keys", "metadata_keys"):
            return self.__dict__[key]
        if key in self.data_keys:
            if key not in self.keys():
                return None
            else:
                if key in self.metadata_keys and callable(self[key]):
                    data = self[key]()
                    self[key] = data
                return self[key]

    def __setattr__(self, key, value):
        if key in ("data_keys", "metadata_keys"):
            self.__dict__[key] = value
            return
        if key in self.data_keys:
            self[key] = value
        else:
            log(type(self), "has not key", key, "value", value)

    def __add__(self, *args, **kwargs):
        data = None
        if len(args) == 0 and len(kwargs) == 0:
            return
        elif len(args) == 1:
            args = args[0]
            if hasattr(args, "items"):  # Item(dict(data))
                data = args.items()
            else:
                try:
                    iter(args)
                except TypeError:
                    raise TypeError("Cannot merge data, type: {} - {}".format(type(args[0])), args[0])
                else:
                    if isinstance(args[0], tuple):  # Item([(key, value), (key, value), ...])
                        data = args
        elif len(args) == 0:
            if "keys" in kwargs.keys() and "values" in kwargs.keys():  # Item(keys=[...], values=[...])
                data = zip(kwargs["keys"], kwargs["values"])

        if data is None:
            raise TypeError("Cannot merge '{}' with data: {} and {}".format(
                type(self).__name__, args, kwargs))

        for k, v in data:
            if k not in self.keys() or self[k] is None:
                self[k] = v
            elif v is not None:
                if not isinstance(v, type(self[k])):
                    raise TypeError("On key {} - types do not match: {}:{} / {}:{}".format(k, v, type(v), self[k], type(self[k])))
                if hasattr(v, "__len__"):
                    if len(v) > len(self[k]):
                        self[k] = v
                elif v > self[k]:
                    self[k] = v
        return self

    def __contains__(self, e):
        return e in self.keys()

    def save_format(self):
        data, meta = {}, {}
        for key, value in self.items():
            if key in self.data_keys:
                if key in self.metadata_keys:
                    meta[key] = value
                else:
                    data[key] = value
            else:
                log(type(self), "Key not in data_keys:", key, value)
        return data, meta


class Anime(Item):
    def __init__(self, *args, **kwargs):
        self.data_keys = (
            'broadcast',
            'date_from',
            'date_to',
            'duration',
            'episodes',
            'genres',
            'id',
            'last_seen',
            'like',
            'picture',
            'rating',
            'status',
            'synopsis',
            'tag',
            'title',
            'title_synonyms',
            'trailer',
            'torrents')
        self.metadata_keys = ('title_synonyms', 'genres', 'torrents')
        super().__init__(*args, **kwargs)


class Torrent(Item):
    def __init__(self, *args, **kwargs):
        self.data_keys = ('filename', 'torrent_url',
                          'seeds', 'leechs', 'file_size')
        super().__init__(*args, **kwargs)


class Character(Item):
    def __init__(self, *args, **kwargs):
        self.data_keys = ('id', 'anime_id', 'role', 'name',
                          'picture', 'desc', 'animeography')
        super().__init__(*args, **kwargs)


class ItemList(queue.Queue):
    def __init__(self, *sources):
        self.list = []

        self.stop = False
        self.new_elem_event = {"enabled": False, "event": threading.Event()}

        self.sources = []
        self.sourceThreads = []
        self.ids = []
        self.callbacks = []

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
                if self.new_elem_event["enabled"]:
                    self.new_elem_event["event"].set()
                    self.new_elem_event["enabled"] = False
                break
            except requests.exceptions.ConnectionError:
                log("Error on ItemList iterator: No internet connection!")
                self.sources.remove(s)
                break
            except requests.exceptions.ReadTimeout:
                log("Error on ItemList iterator: Timed out!")
                self.sources.remove(s)
                break
            except Exception as e:
                log("Error on ItemList iterator", s, iterator, "\n", traceback.format_exc())
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
                    for cb in self.callbacks:
                        cb(e)

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
        if isinstance(source, tuple) and isinstance(source[0], queue.Queue):  # Add a tuple like (data_queue, data_threads)
            t = threading.Thread(target=self.queueListener, args=source, daemon=True)
            t.start()
            self.sourceThreads.append(t)
        else:
            self.sources.append(source)
            t = threading.Thread(target=self.sourceListener, args=(source,), daemon=True)
            t.start()
            self.sourceThreads.append(t)

    def add_callback(self, cb):
        """Call a function when a new element is added - Useful for saving"""
        self.callbacks.append(cb)

    def del_callback(self, cb):
        if cb in self.callbacks:
            self.callbacks.remove(cb)

    def get(self, timeout=None, default=None):
        if len(self.list) > 0:
            e = self.list.pop(0)
            return e
        else:
            if self.empty():
                return default
            else:
                return self.get_from_sources(timeout, default)

    def get_from_sources(self, timeout=None, default=None):
        self.new_elem_event["enabled"] = True
        if self.new_elem_event["event"].wait(timeout=timeout):
            if len(self.list) > 0:
                e = self.list.pop(0)
                return e
            elif len(self.sources) == 0:
                return default
        else:
            log("Error on ItemList iterator: Timed out")
            return default  # Timed out

    def empty(self):
        return len(self.sources) == 0 and len(self.list) == 0

    def is_ready(self):
        return len(self.list) > 0 or len(self.sources) == 0


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


class DefaultDict(dict):
    """A dict with a default value instead of raising a KeyError"""

    def __init__(self, default, *args, **kwargs):
        self.default = default
        super().__init__(*args, **kwargs)

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            self.__setitem__(key, self.default)
            return super().__getitem__(key)


class NoneDict(DefaultDict):
    """A dict, which return "NONE" instead of raising a KeyError and allow to initialize with keys and values as kwargs"""

    def __init__(self, *args, **kwargs):
        if len(args) == 0 and "keys" in kwargs.keys() and "values" in kwargs.keys():
            keys, values = kwargs["keys"], kwargs["values"]
            for k, v in zip(keys, values):
                self[k] = v
        else:
            super().__init__("NONE", *args, **kwargs)


class RegroupList(list):
    """A list of dict, wich regroup values based on a PK, creating a sub-list if values are different"""

    def __init__(self, pk, merge_keys, *args):
        super().__init__()
        self.pk = pk
        self.merge_keys = merge_keys
        self.keys = {}
        for sub in args:
            if not isinstance(dict, sub):
                raise TypeError("Elements must be dicts")
            self.add_element(sub)

    def add_element(sub, index=None):
        sub_id = sub[self.pk]
        if sub_id in self.keys:
            for t in self:
                if sub_id == t[self.pk]:
                    for k, v in sub.items():
                        if k in t:
                            if v != t[k]:
                                if isinstance(t[k], list):
                                    t[k].append(v)
                                else:
                                    t[k] = [t[k], v]
                        else:
                            t[k] = v
                    break
        else:
            if index is None:
                super().append(sub)
            else:
                super().insert(index, sub)
            self.keys.add(sub_id)

    def append(self, sub):
        self.add_element(sub)

    def extend(self, subs):
        for sub in subs:
            self.add_element(sub)

    def insert(self, i, sub):
        self.add_element(sub, i)


class SortedList(list):
    def __init__(self, keys=None):
        if keys is None:  # Keys must be either None or a list of tuples containing the key and a "reverse" bool
            self.keys = ((lambda e: e, False),)
        else:
            self.keys = keys

    def append(self, e):
        length = len(self)
        if length == 0:
            super().append(e)
        else:
            self.binary_insert(e, 0, length)
        return self

    def extend(self, e):
        for sub in e:
            self.append(sub)
        return self

    def __contains__(self, e):
        length = len(self)
        if length == 0:
            return False
        else:
            return self.binary_search(e, 0, length) is not False

    def compare(self, a, b):
        """ Return True if a > b, False if a < b, and None if a == b """
        for key, reverse in self.keys:
            try:
                k_a, k_b = key(a), key(b)
            except Exception:
                # Loop
                continue
            if k_a > k_b:
                return not reverse
            elif k_a < k_b:
                return reverse
            # Loop if a == b
        return None

    def binary_insert(self, e, start, stop):
        middle = (stop + start) // 2
        if self.compare(e, self[middle]):  # Hacky - see reverse truth table
            if middle == start:
                self.insert(start + 1, e)
                return start + 1
            else:
                return self.binary_insert(e, middle, stop)
        else:
            if middle == stop:
                self.insert(stop, e)
                return stop
            else:
                return self.binary_insert(e, start, middle)

    def binary_search(self, e, start, stop):
        middle = (stop + start) // 2
        comp = self.compare(e, self[middle])
        if comp is None:  # e == self.middle
            return middle
        elif comp:
            if middle == start:
                return False
            else:
                return self.binary_search(e, middle, stop)
        else:
            if middle == stop:
                return False
            else:
                return self.binary_search(e, start, middle)


class SortedDict():
    """Actually a sorted list of tuples, but behave like a dict"""

    def __init__(self, keys=None, reverse=False):
        super().__init__()
        if keys is None:  # Keys must be either None or a list of tuples containing the key and a "reverse" bool
            self._keys = ((lambda e: e[0], False),)
        else:
            self._keys = keys
        self.data_list = SortedList(keys=self._keys)
        self.reverse = reverse
        # self.data_list.compare = self.compare

    def __contains__(self, key):
        return key in self.keys()

    def __repr__(self):
        return "{" + ", ".join(":".join(map(str, item)) for item in self.data_list) + "}"

    def __getitem__(self, key):
        i = self.search_key(key)
        if i is not False:
            return self.data_list[i][1]
        raise KeyError(key)

    def __setitem__(self, key, value):
        i = self.search_key(key)
        if i is not False:
            self.data_list[i] = (key, value)
            return
        self.data_list.append((key, value))

    def keys(self):
        return tuple(e[0] for e in self.data_list)

    def values(self):
        return tuple(e[1] for e in self.data_list)

    def items(self):
        return self.data_list

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def search_key(self, key):
        length = len(self.data_list)
        if length == 0:
            return False
        else:
            match = self.binary_search(key, 0, length)
            if key == match:
                return match
            else:
                for i, e in enumerate(self.data_list):
                    if e[0] == key:
                        return i
                return False

    def compare(self, a, b):
        """ Return True if a > b, False if a < b, and None if a == b """
        a = (a, None)
        for key, reverse in self._keys:
            try:
                k_a, k_b = key(a), key(b)
            except Exception:
                # Loop
                pass
            else:
                if k_a > k_b:
                    return not reverse
                elif k_a < k_b:
                    return reverse
                # Loop if a == b
        return None

    def binary_search(self, e, start, stop):
        middle = (stop + start) // 2
        comp = self.compare(e, self.data_list[middle])
        if comp is None:  # e == self.middle
            return middle
        elif comp:  # Hacky - see reverse truth table
            if middle == start:
                return False
            else:
                return self.binary_search(e, middle, stop)
        else:
            if middle == stop:
                return False
            else:
                return self.binary_search(e, start, middle)


class ReturnThread(threading.Thread):
    def __init__(self, target=None, args=(), kwargs={}, daemon=True):
        super().__init__(daemon=daemon)
        self.target = target
        self.args = args
        self.kwargs = kwargs
        self.output = queue.Queue()

        self.start()

    def run(self):
        try:
            out = self.target(*self.args, **self.kwargs)
        except BaseException:
            self.output.put(None)
        else:
            self.output.put(out)

    def get(self, *args, **kwargs):
        return self.output.get(*args, **kwargs)

    def empty(self):
        return self.output.empty()

    def ready(self):
        return not self.empty()


class LockWrapper():
    """A lock wrapper, useful for logging or callbacks"""

    def __init__(self, lock):
        self.lock = lock

    def __enter__(self, *args, **kwargs):
        # print("Acquired lock")
        return self.lock.__enter__(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        # print("Released lock")
        return self.lock.__exit__(*args, **kwargs)

    def __getattr__(self, *args, **kwargs):
        return self.lock.__getattr__(*args, **kwargs)


if __name__ == "__main__":
    import random
    sl = SortedList(reverse=True)

    for i in random.sample(list(range(100)), 100):
        sl.append(i)

    sd = SortedDict()

    for i in range(100):
        sd[random.randint(0, 100)] = random.randint(0, 100)

    # def slow_iter(msg, t=1, length=10):
    #     for i in range(length):
    #         time.sleep(t)
    #         # log(msg+str(i))
    #         yield msg + str(i)
    # items = ItemList(range(5), ('a', 'b', 'c'), slow_iter(
    #     "haha", 1, 3), slow_iter("hehe", 5, 2))
    # for e in items:
    #     log(e)

    # a = Anime()
    # log(a.title)
    # a.title = "jujutsu"
    # a["synopsis"] = "salut"
    # log(a.title,a.synopsis)
