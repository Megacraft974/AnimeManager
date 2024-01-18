from ..logger import Logger


try:
    from ..utils import LoginDialog
except ImportError:
    import sys, os
    sys.path.append(os.path.abspath('./'))
    from utils import LoginDialog

class BaseFileManager(Logger):
    name = ''
    def __init__(self, settings={}, update=False):
        self.settings = settings
        
        Logger.__init__(self)

        if update or self.settings.get('dataPath', '') == '':
            self.change_path(settings)
        else:
            self.initialize()

    def initialize(self):
        """Optional, called right after __init__"""
        pass

    def open(self, path, mode="r", **kwargs):
        """Return a file object depending on mode, creating file and folders if necessary"""
        raise NotImplementedError()
    
    def mkdir(self, path):
        """Create a directory"""
        raise NotImplementedError()

    def list(self, path):
        """List all files in a directory"""
        raise NotImplementedError()

    def exists(self, path):
        """Check if path is valid and exists"""
        raise NotImplementedError()

    def isdir(self, path):
        """Check if path is a directory"""
        return NotImplementedError()
    
    def isfile(self, path):
        """Check if path is a file"""
        # By default, will assume that anything that isn't a directory is a file
        return not self.isdir(path)

    def delete(self, path):
        """Delete a file or folder"""
        raise NotImplementedError()
    
    def change_path(self, root):
        """Update cwd, and sometimes login infos as well"""
        raise NotImplementedError()
    

