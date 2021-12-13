import os
from logger import log

def get_players():  # TODO
    root = os.path.dirname(os.path.realpath(__file__))
    ignore = ("__init__.py", "base_player.py")
    for f in os.listdir():
        path = os.path.join(root, f)
        if f not in ignore and os.path.isfile(path):
            name = f.split(".py")[-1]
            try:
                exec('from {a} import {b}'.format(a=convert_name(name), b=name))
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

def convert_name(name):
    out = ""
    upper = False
    for l in name:
        if l == "_":
            upper = True
        elif upper:
            out += l.upper()
        else:
            out += l
    return out

get_players()