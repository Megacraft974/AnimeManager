import auto_launch

import threading
import time
import os

from datetime import date, datetime


class Logger:
    def __init__(self, logs="DEFAULT"):
        # Not necessary if used as class slave

        appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
        self.logsPath = os.path.join(appdata, "logs")
        self.maxLogsSize = 50000
        self.logs = ['DB_ERROR', 'DB_UPDATE', 'MAIN_STATE',
                     'NETWORK', 'SERVER', 'SETTINGS', 'TIME']

        if hasattr(self, 'remote') and self.remote:
            self.log_mode = "NONE"
        elif logs in ("DEFAULT", "ALL", "NONE"):
            self.log_mode = logs
        else:
            self.log_mode = "DEFAULT"

        self.initLogs()

    def initLogs(self):
        if not hasattr(self, "log_mode"):
            self.log_mode = "DEFAULT"
        if not os.path.exists(self.logsPath):
            os.mkdir(self.logsPath)

        logsList = os.listdir(self.logsPath)
        size = sum(os.path.getsize(os.path.join(self.logsPath, f))
                   for f in logsList)

        while size >= self.maxLogsSize and len(logsList) > 1:
            try:
                os.remove(os.path.join(self.logsPath, logsList[0]))
            except FileNotFoundError:
                pass
            logsList = os.listdir(self.logsPath)
            size = sum(os.path.getsize(os.path.join(self.logsPath, f))
                       for f in logsList)

        self.logFile = os.path.normpath(
            os.path.join(
                self.logsPath, "log_{}.txt".format(
                    datetime.today().strftime("%Y-%m-%dT%H.%M.%S"))))
        with open(self.logFile, "w") as f:
            f.write("_" * 10 + date.today().strftime("%d/%m/%y") + "_" * 10 + "\n")

    def log(self, *text, end="\n"):
        if self.log_mode == "NONE":
            return
        elif self.log_mode == "DEFAULT":
            category, text = text[0], text[1:]
            if category in self.logs:
                toLog = "[{}]".format(category.center(13)) + " - "
                toLog += " ".join([str(t) for t in text])
                print(toLog + end, flush=True, end="")
            else:
                return
        elif self.log_mode == "ALL":
            toLog = "[     LOG     ] - " + " ".join([str(t) for t in text])
            print(toLog + end, flush=True, end="")
        else:
            return
        with open(self.logFile, "a", encoding='utf-8') as f:
            timestamp = "[{}]".format(time.strftime("%H:%M:%S"))
            f.write(timestamp + toLog + "\n")


def log(*args, **kwargs):
    if "logger_instance" in globals().keys():
        logger = globals()["logger_instance"]
    else:
        logger = Logger(logs="ALL")
        globals()["logger_instance"] = logger
    logger.log(*args, **kwargs)
