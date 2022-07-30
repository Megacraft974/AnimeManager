import os
import sys

def windows():
    windows = []
    ignore = ('__init__', '__pycache__')
    root = os.path.dirname(__file__)
    for f in os.listdir(root):
        name = f.split(".py")[0]
        if name not in ignore:
            try:
                exec("from . import " + name)
            except Exception as e:
                print(f'Error while importing window: {name} - {e}')
                raise
            module = globals()[name]
            func = getattr(module, name)
            windows.append(func)
    
    return windows
