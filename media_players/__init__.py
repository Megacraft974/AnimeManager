import os
from logger import log


class MediaPlayers:
    def __init__(self):
        self.get_players()

    def get_players(self):
        self.media_players = {}
        root = os.path.dirname(__file__)
        ignore = ("__init__.py", "base_player.py")
        for f in os.listdir(root):
            path = os.path.join(root, f)
            if f not in ignore and os.path.isfile(path):
                name = f.rsplit(".py", 1)[0]
                func_name = self.convert_name(name)
                try:
                    exec('from .{a} import {b}'.format(a=name, b=func_name))
                except Exception as e:
                    log("Error while importing media player:", name, '- e:', e)
                else:
                    if func_name in locals().keys():
                        f = locals()[func_name]
                        self.media_players[name] = f

    def convert_name(self, name):  # TODO - Remove self
        out = name[0].upper()
        upper = False
        for letter in name[1:]:
            if letter == "_":
                upper = True
            elif upper:
                out += letter.upper()
                upper = False
            else:
                out += letter
        return out
