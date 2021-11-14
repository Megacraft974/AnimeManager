import os
import threading
import queue
import traceback

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
        try:
            for e in parser.search(title, limit):
                for key in ('seeds', 'leechs'):
                    if not isinstance(e[key], int):
                        e[key] = int(e[key])

                que.put(e)
        except Exception as e:
            traceback.print_exc()


def search(titles, limit=50):
    parsers = get_parser_list()
    threads = []
    que = queue.Queue()
    for p in parsers:
        t = threading.Thread(target=handle_search,
                             args=(titles, limit, que, p))
        threads.append(t)
        t.start()

    while any(map(lambda t: t.is_alive(), threads)) or not que.empty():
        try:
            yield que.get(timeout=1)
        except queue.Empty:
            pass
