if __name__ != "__main__":
    import os
    import sys
    windows = []
    ignore = ('__init__', '__pycache__')
    root = os.path.dirname(__file__)
    for f in os.listdir(root):
        name = f.split(".py")[0]
        if name not in ignore:
            exec("from . import " + name)
            module = globals()[name]
            func = getattr(module, name)
            windows.append(func)
