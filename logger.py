import threading
import time
import os

from datetime import date, datetime


class Logger:
    def __init__(self, logs="DEFAULT"):
        # Not necessary if used as class slave

        if "logger_instance" in globals().keys():
            self.log = globals()["logger_instance"].log
            return
        else:
            print("Created new logger", flush=True)

            globals()["logger_instance"] = self

        appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
        self.logsPath = os.path.join(appdata, "logs")  # TODO
        self.maxLogsSize = 50000
        self.logs = ['DB_ERROR', 'DB_UPDATE', 'MAIN_STATE',
                     'NETWORK', 'SERVER', 'SETTINGS', 'TIME']
        self.loggingCb = None

        if hasattr(self, 'remote') and self.remote is True:
            self.log_mode = "NONE"
        elif logs in ("DEFAULT", "ALL", "NONE"):
            self.log_mode = logs
        else:
            self.log_mode = "DEFAULT"

        self.initLogs()

    def initLogs(self):
        if not hasattr(self, "log_mode"):
            self.log_mode = "DEFAULT"

        if "log_file" in globals().keys():
            self.logFile = globals()['log_file']
            return

        if not os.path.exists(self.logsPath):
            os.makedirs(self.logsPath)

        logsList = os.listdir(self.logsPath)
        size = sum(os.path.getsize(os.path.join(self.logsPath, f))
                   for f in logsList)

        while size >= self.maxLogsSize and len(logsList) > 1:
            try:
                os.remove(os.path.join(self.logsPath, logsList[0]))
            except FileNotFoundError:
                pass
            except PermissionError:
                pass
            else:
                logsList = os.listdir(self.logsPath)
                size = sum(os.path.getsize(os.path.join(self.logsPath, f))
                           for f in logsList)

        self.logFile = os.path.normpath(
            os.path.join(
                self.logsPath, "log_{}.txt".format(
                    datetime.today().strftime("%Y-%m-%dT%H.%M.%S"))))
        globals()['log_file'] = self.logFile
        with open(self.logFile, "w") as f:
            f.write("_" * 10 + date.today().strftime("%d/%m/%y") + "_" * 10 + "\n")

    def log(self, *text, log_mode=None, end="\n"):
        log_mode = log_mode or self.log_mode

        console_log = True
        if log_mode == "NONE":
            # Don't log
            console_log = False

        if (isinstance(text[0], str) and text[0].isupper()) or ('allLogs' in self.__dict__ and text[0] in self.allLogs):
            category, text = text[0], text[1:]
            toLog = "[{}]".format(category.center(13)) + " - "
            toLog += " ".join([str(t) for t in text])
            
            if category not in self.logs:
                # Ignore this log
                console_log = False
        else:
            toLog = "[     LOG     ] - " + " ".join([str(t) for t in text])

        if console_log:
            # Log to console
            print(toLog + end, flush=True, end="")

        # Log to file
        with open(self.logFile, "a", encoding='utf-8') as f:
            timestamp = "[{}]".format(time.strftime("%H:%M:%S"))
            f.write(timestamp + toLog + "\n")

        if self.loggingCb is not None:
            self.loggingCb(timestamp + toLog)


def log(*args, **kwargs):
    if "logger_instance" in globals().keys():
        logger = globals()["logger_instance"]
    else:
        logger = Logger(logs="ALL")
        globals()["logger_instance"] = logger
        logger.log("MAIN_STATE", "Created new logger")
    logger.log(*args, **kwargs)
