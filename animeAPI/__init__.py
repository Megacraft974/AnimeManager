from logger import log
from classes import Anime, AnimeList, Character, CharacterList
import os
import threading
import queue
import sys
import traceback
sys.path.append(os.path.abspath("../"))


class AnimeAPI():
    def __init__(self, apis='all', *args, **kwargs):
        self.apis = []
        self.init_thread = threading.Thread(
            target=self.load_apis, args=(apis, *args), kwargs=kwargs)
        self.init_thread.start()

    def __getattr__(self, name):
        def f(*args, **kwargs):
            return self.wrapper(name, *args, **kwargs)
        return f

    def load_apis(self, apis='all', *args, **kwargs):
        if apis == 'all':
            ignore = ('__init__.py', 'APIUtils.py')
            root = os.path.dirname(__file__)
            sys.path.append(root)
            for f in os.listdir(root):
                if f not in ignore and f[-3:] == ".py":
                    name = f[:-3]
                    try:
                        exec('from {n} import {n}Wrapper'.format(n=name))
                    except ImportError as e:
                        log(name, e)
                    else:
                        try:
                            f = locals()[name + "Wrapper"](*args, **kwargs)
                        except Exception as e:
                            log("Error while loading {} API wrapper: {}".format(
                                name, traceback.format_exc()))
                        else:
                            self.apis.append(f)
        else:
            for name in apis:
                try:
                    exec('from {n} import {n}'.format(n=name))
                    self.apis.append(api(*args, **kwargs))
                except BaseException:
                    pass
        if len(self.apis) == 0:
            log("No apis found!")

    def wrapper(self, name, *args, **kwargs):
        def handler(api, name, que, *args, **kwargs):
            try:
                r = getattr(api, name)(*args, **kwargs)
            except Exception as e:
                apiName = str(api).split(".")[0].split(" ")[-1]
                log(
                    "Error on API - handler",
                    apiName,
                    traceback.format_exc())
            else:
                if r is not None:
                    que.put(r)
                else:
                    apiName = str(api).split(".")[1].split(" ")[0]
                    log("{}.{}() not found!".format(apiName, name))

        def iterator(que, threads):  # Not used
            results = [que.get()]
            c = 0
            while len(results) > 0:
                if not que.empty():
                    results.append(que.get())
                for r in results:
                    try:
                        e = next(r)
                    except StopIteration:
                        results.remove(r)
                    except Exception as e:
                        apiName = str(r).split(".")[0].split(" ")[-1]
                        log(
                            "Error on API - iterator",
                            apiName,
                            traceback.format_exc(),
                            flush=True)
                    else:
                        if e is not None:
                            yield e

        if self.init_thread is not None:
            self.init_thread.join()
            self.init_thread = None
        threads = []
        que = queue.Queue()
        for api in self.apis:
            t = threading.Thread(target=handler, args=(
                api, name, que, *args), kwargs=kwargs)
            t.start()
            threads.append(t)

        if name in ('anime', 'character'):
            if name == 'anime':
                out = Anime()
            else:
                out = Character()
            # out = {}
            r = None
            while not que.empty() or any(t.is_alive() for t in threads):
                try:
                    r = que.get(timeout=0.01)
                except queue.Empty:
                    pass
                else:
                    out += r
                    # for k,v in r.items():
                    #     if k not in out.keys():
                    #         out[k] = v
            return out
        else:
            if name in ('schedule', 'searchAnime'):
                return AnimeList((que, threads))
            elif name in ('animeCharacters',):
                return CharacterList((que, threads))
            # return iterator(que,threads)
        return ()


# TODO - Add more APIs:
# anilist.co
# nautiljon.com
# anisearch.com

if __name__ == "__main__":
    appdata = os.path.join(os.getenv('APPDATA'), "AnimeManager")
    dbPath = os.path.join(appdata, "animeData.db")
    api = AnimeAPI('all', dbPath)
    s = api.searchAnime("boku")
    c = 0
    for e in s:
        log(c, e['title'])
        c += 1
    for k, v in api.anime(10).items():
        log(k, v)
