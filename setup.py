from distutils.core import setup
import py2exe
import sys
import os

sys.argv.append('py2exe')

setup(
    options={'py2exe': {
                'bundle_files': 1,
                'compressed': True,
                'packages': [
                    "lxml",
                    "qbittorrentapi",
                    "bs4"
                ],
                'includes': [
                    "lxml._elementpath",
                    "lxml.etree",
                ],
                'excludes': [
                    'pkg_resources', 'doctest', 'pdb', 'calendar', 'optparse', 'jsonschema', 'tornado', 'setuptools', 'distutils', 'matplotlib', 'zmq'
                ]
                }
            },
    windows=[{'script': "animeManager.py"}],
    zipfile=None,
)
