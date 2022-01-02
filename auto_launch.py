""" Simple script to launch the app from any file """

import sys
import os

if 'auto_launch_initialized' not in globals().keys():
    globals()['auto_launch_initialized'] = os.getpid()
    from animeManager import Manager

    Manager()
    sys.exit()
