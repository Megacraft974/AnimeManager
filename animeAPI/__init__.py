
import os
import queue
import sys
import threading
import time
import traceback

import requests
try:
    from logger import Logger, log
    from classes import (Anime, AnimeList, Character, CharacterList, ItemList,
                        NoIdFound)
    from getters import Getters
except ImportError:
    import sys
    sys.path.append(os.path.abspath("."))
    from logger import Logger, log
    from classes import (Anime, AnimeList, Character, CharacterList, ItemList,
                        NoIdFound)
    from getters import Getters


class AnimeAPI(Getters, Logger):
    def __init__(self, apis='all', *args, **kwargs):
        super().__init__()#logs="ALL")
        self.apis = []
        self.init_thread = threading.Thread(
            target=self.load_apis, args=(apis, *args), kwargs=kwargs, daemon=True)
        self.init_thread.start()

    def __getattr__(self, name):
        if name in ('dbPath',):
            return super().__getattr__(name)

        def f(*args, **kwargs):
            return self.wrapper(name, *args, **kwargs)
        return f

    def load_apis(self, apis='all', *args, **kwargs):
        if apis == 'all':
            api_names = []
            ignore = ('__init__.py', 'APIUtils.py')
            root = os.path.dirname(__file__)
            sys.path.append(root)  # TODO - Should use relative import
            for f in os.listdir(root):
                if f not in ignore and f[-3:] == ".py":
                    name = f[:-3]
                    api_names.append(name)
        else:
            api_names = apis

        for name in api_names:
            try:
                exec('from {n} import {n}Wrapper'.format(n=name))
            except ImportError as e:
                self.log("ANIME_SEARCH", name, e)
            else:
                try:
                    f = locals()[name + "Wrapper"](*args, **kwargs)
                except Exception as e:
                    self.log("ANIME_SEARCH", "Error while loading {} API wrapper: \n{}".format(
                        name, traceback.format_exc()))
                else:
                    self.apis.append(f)
        if len(self.apis) == 0:
            self.log("ANIME_SEARCH", "No apis found!")
        else:
            self.log("ANIME_SEARCH", len(self.apis), "apis found")

    def wrapper(self, name, *args, **kwargs):
        def handler(api, name, que, *args, **kwargs):
            try:
                f = getattr(api, name)
            except AttributeError as e:
                self.log("ANIME_SEARCH", "{} has no attribute {}! - Error: \n{}".format(api.__name__, name, e))
                return

            start = time.time()
            r = None
            try:
                r = f(*args, **kwargs)
            except requests.exceptions.ConnectionError as e:
                self.log("ANIME_SEARCH", "Error on API - handler: No internet connection! -", e)
            except requests.exceptions.ReadTimeout as e:
                self.log("ANIME_SEARCH", "Error on API - handler: Timed out! -", e)
            except NoIdFound:
                pass
            except Exception as e:
                self.log(
                    "ANIME_SEARCH", 
                    "Error on API - handler:",
                    api.__name__, "-\n",
                    traceback.format_exc())
            else:
                if r is not None:
                    que.put(r)
                else:
                    self.log("ANIME_SEARCH", "{}.{}() not found!".format(api.__name__, name))
            finally:
                if r:
                    self.log("ANIME_SEARCH", "{}.{}(): {} ms".format(api.__name__, name, int((time.time() - start) * 1000)))

        if self.init_thread is not None:
            self.init_thread.join()
            self.init_thread = None

        threads = []
        que = queue.Queue()
        for api in self.apis:
            t = threading.Thread(target=handler, args=(
                api, name, que, *args), kwargs=kwargs, daemon=True)
            t.start()
            threads.append(t)

        # if 'timeout' in kwargs: # Disabled
        #     delay = max(0, kwargs['timeout']) # Min 0 to loop at least once
        #     timeout = delay + time.time()
        # else:
        #     timeout = None
        #     delay = None

        out = ()
        if name in ('anime', 'character'):
            if name == 'anime':
                out = Anime()
            else:
                out = Character()
            r = None
            while not que.empty() or any(t.is_alive() for t in threads): # or (delay is not None and delay < 0):
                try:
                    r = que.get(block=True, timeout=1) #, timeout=delay)
                except queue.Empty:
                    pass
                else:
                    out += r

                # if timeout is not None:
                #     delay = timeout - time.time()
                # else:
                #     delay = None

            if len(out) == 0:
                self.log("ANIME_SEARCH", "No data - id:" + str(name) + " - args:" + ",".join(map(str, args)))
        else:
            if name in ('schedule', 'searchAnime', 'season'):
                out = AnimeList((que, threads))
            elif name in ('animeCharacters',):
                out = CharacterList((que, threads))
            else:
                out = ItemList((que, threads))
        self.save(out)
        return out

    def save(self, data):
        database = self.getDatabase()
        if not data:
            return
        elif isinstance(data, Anime):
            table = "anime"
            if data.status == "UPDATE" and bool(database.sql("SELECT EXISTS(SELECT 1 FROM anime WHERE id=?);", (data.id,))[0][0]):
                # Anime already have data, avoid overwriting
                return
        elif isinstance(data, Character):
            table = "characters"
        elif isinstance(data, ItemList):
            data.add_callback(self.save)
            return
        else:
            raise TypeError("{} is an invalid type!".format(str(type(data))))

        with database.get_lock():
            database.set(data, table=table, get_output=False)
            database.save(get_output=False)

# TODO - Add more APIs:
# nautiljon.com
# anisearch.com


if __name__ == "__main__":
    appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
    dbPath = os.path.join(appdata, "animeData.db")
    api = AnimeAPI('all', dbPath)
    s = api.searchAnime("boku")
    c = 0
    for e in s:
        log(c, e['title'])
        c += 1
    for k, v in api.anime(10).items():
        log(k, v)
