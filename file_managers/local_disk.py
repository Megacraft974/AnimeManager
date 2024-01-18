import os
import sys
from tkinter.filedialog import askdirectory

try:
    from .base import BaseFileManager
except ImportError:
    from base import BaseFileManager

class LocalFileManager(BaseFileManager):
    name = 'Local'

    def open(self, path, mode):
        return open(path, mode)
    
    def mkdir(self, path):
        os.mkdir(path)
    
    def list(self, path):
        try:
            return os.listdir(path)
        except NotADirectoryError:
            return []

    def exists(self, path):
        return os.path.exists(path)
    
    def isdir(self, path):
        return os.path.isdir(path)

    def change_path(self, settings):
        root = settings.get('dataPath', None)

        if sys.platform == 'linux' and 'DISPLAY' not in os.environ:
            # Running headless
            
            # Actually, there most likely won't even be a terminal so why bother

            raise Exception('No input folder??')
            path = input('Please input the path of your data folder: ')
        else:
            path = askdirectory(
                title='Choose data folder',
                initialdir=root
            )

        self.settings = {'dataPath': path}

if __name__ == "__main__":
    settings = {}

    fm = LocalFileManager(settings)
    print(fm.list('C:\\Users\\William'))

    path = 'D:\\willi\\Documents\\Python\\fichier\\test.txt'

    print(fm.exists(path))
    print(fm.exists('/home/pi/root.txt'))

    out = fm.open(path, mode='r')
    data = out.read()
    print(data)

    with fm.open(path, mode='w') as f:
        f.write('Hello World!')
    pass