import os
import threading
import re
import queue
from logger import log

IGNORE = ['template.py', '__init__.py']


def get_parser_list():
    root = os.path.dirname(__file__)
    for f in os.listdir(root):
        if f not in IGNORE and os.path.isfile(os.path.join(root, f)):
            f = f.split(".py")[0]
            exec("from . import " + f)
            module = globals()[f]
            parser = module.Parser()
            yield parser


def handle_search(titles, limit, que, parser):
    for title in titles:
        title = re.sub(r"[\|]", "", title)
        try:
            for e in parser.search(title, limit):
                for key in ('seeds', 'leechs'):
                    if not isinstance(e[key], int):
                        e[key] = int(e[key])
                que.put(e)
        except Exception as e:
            log("Error on torrent search:", e)


def search(titles, limit=50):
    parsers = get_parser_list()
    threads = []
    que = queue.Queue()
    for p in parsers:
        t = threading.Thread(target=handle_search,
                             args=(titles, limit, que, p),
                             daemon=True)
        threads.append(t)
        t.start()

    while any(map(lambda t: t.is_alive(), threads)) or not que.empty():
        if not que.empty():
            yield que.get()
