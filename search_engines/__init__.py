from .nova3.custom_engine import search # TODO - Fix it first

# DEPRECATED:

# import os
# import queue
# import re
# import threading

# from logger import log
# from classes import Magnet

# IGNORE = ['template.py', '__init__.py', 'parserUtils.py']
# PARSERS = []


# def get_parser_list():
#     # DEPRECATED
#     if PARSERS:
#         for parser in PARSERS:
#             yield parser
#         return

#     root = os.path.dirname(__file__)
#     for f in os.listdir(root):
#         if f not in IGNORE and os.path.isfile(os.path.join(root, f)):
#             f = f.split(".py")[0]
#             exec("from . import " + f)
#             module = globals()[f]
#             parser = module.Parser()
#             PARSERS.append(parser)
#             yield parser


# def handle_search(titles, limit, que, parser):
#     # DEPRECATED
#     for title in titles:
#         title = re.sub(r"[\|]", "", title)
#         try:
#             for e in parser.search(title, limit):
#                 if e is False: # Fatal error - Stop search
#                     return

#                 for key in ('seeds', 'leech'):
#                     if not isinstance(e[key], int):
#                         e[key] = int(e[key])
#                 que.put(e)
#         except Exception as e:
#             log("FILE_SEARCH", "Error on torrent search:", e)


# def search(titles, limit=50):
#     # DEPRECATED
#     parsers = get_parser_list()
#     threads = []

#     que = queue.Queue()
#     for p in parsers:
#         t = threading.Thread(target=handle_search,
#                              args=(titles, limit, que, p),
#                              daemon=True)
#         threads.append(t)
#         t.start()

#     while any(map(lambda t: t.is_alive(), threads)) or not que.empty():
#         try:
#             data = que.get(block=True, timeout=1)
#             data['link'] = Magnet(data['link'])
#             yield data
#         except queue.Empty:
#             pass

# # Add serach engines:
# # https://www.shanaproject.com/ -> Require login and following stuff: wayyyy too complicated for now
