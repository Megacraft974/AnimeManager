""" Simple script to launch the app from any file """

import sys
import os
from multiprocessing import Process, current_process

if 'auto_launch_initialized' not in globals().keys() and current_process().name == 'MainProcess':
    globals()['auto_launch_initialized'] = True
    try:
        from animeManager import Manager
    except ImportError:
        pass
    else:
        Manager()
        sys.exit()
