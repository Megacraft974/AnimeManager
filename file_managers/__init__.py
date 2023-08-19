from .local_disk import LocalFileManager
from .FTP import FTPFileManager

managers = {}
for m in [LocalFileManager, FTPFileManager]:
    managers[m.name] = m