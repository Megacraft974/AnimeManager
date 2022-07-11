import requests
import sys
import os

sys.path.append(os.path.abspath("../"))
try:
    from logger import Logger
    from getters import Getters
except ModuleNotFoundError as e:
    print("Module not found:", e)

exceptions = requests.exceptions

class ParserUtils(Logger, Getters):
    def __init__(self):
        Logger.__init__(self, logs="ALL")
        # self.dbPath = dbPath
        # self.database = self.getDatabase()
        self.session = requests.Session()
    
    def get(self, *args, **kwargs):
        # Wrapper function for HTTP GET requests
        return self.session.get(*args, **kwargs)

    def post(self, *args, **kwargs):
        # Wrapper function for HTTP POST requests
        return self.session.get(*args, **kwargs)