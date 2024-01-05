import ctypes
import os
import socket
import shutil
import locale
import json


class Constants:
    def __init__(self):
        self.logs = ['DB_ERROR', 'DB_UPDATE', 'MAIN_STATE',
                     'NETWORK', 'SERVER', 'SETTINGS', 'TIME']

        appid = 'megacraft.anime.manager.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)
        locale.setlocale(locale.LC_ALL, '')
        # 181915 - 282923 - 373734 - F8F8C4 - 98E22B(G) - E79622(O)

        cwd = os.path.dirname(os.path.abspath(__file__))
        self.iconPath = os.path.join(cwd, "icons")

        appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
        self.dbPath = os.path.join(appdata, "animeData.db")
        self.settingsPath = os.path.join(appdata, "settings.json")
        self.cache = os.path.join(appdata, "cache")
        self.logsPath = os.path.join(appdata, "logs")
        if not os.path.exists(appdata):
            os.mkdir(appdata)
        self.qbCache = os.path.join(os.path.expanduser("~"), "AppData\\Local\\qBittorrent\\BT_backup")

        # self.dataPath = os.path.expanduser('~\\Documents\\AnimeManager')
        # if not os.path.exists(self.dataPath):
        #     os.mkdir(self.dataPath)
        # self.animePath = os.path.join(self.dataPath, "Animes")
        self.animePath = None

        self.hideRated = True
        self.enableServer = True
        self.server = None
        self.fm = None
        self.tm = None

        self.hostName = "0.0.0.0"
        self.serverPort = 8081

        # TODO - Move to settings file
        self.players_order = ['mpv_player', 'vlc_player', 'ff_player']

        self.RPC_client_id = '930139147803459695'  # TODO - Put somewhere else? I'm pretty sure it's mostly safe but well...

        self.allLogs = [
            'ANIME_LIST',
            'ANIME_SEARCH',
            'CHARACTER',
            'CONFIG',
            'DB_MAIN',
            'DB_ERROR',
            'DB_UPDATE',
            'DISK_ERROR',
            'FILE_SEARCH',
            'MAIN_STATE',
            'NETWORK',
            'NETWORK_DATA',
            'PICTURE',
            'RELATED',
            'SCHEDULE',
            'SERVER',
            'SETTINGS',
            'THREAD',
            'TIME']
        self.pathSettings = [
            "iconPath", "cache",
            "dbPath", "logsPath"]
        self.websitesViewUrls = {
            "mal_id": "https://myanimeList.net/anime/{}",
            "kitsu_id": "https://kitsu.io/anime/{}",
            "anilist_id": "https://anilist.co/anime/{}",
            "anidb_id": "https://anidb.net/anime/{}"}
        self.seasons = {
            'winter': {'start': 1, 'end': 3},
            'spring': {'start': 4, 'end': 6},
            'summer': {'start': 7, 'end': 9},
            'fall': {'start': 10, 'end': 12}}
        self.filterOptions = {
            'Liked': {'color': 'Red', 'filter': 'LIKED'},
            'Seen': {'color': 'Green', 'filter': 'SEEN'},
            'Watching': {'color': 'Orange', 'filter': 'WATCHING'},
            'Watchlist': {'color': 'Blue', 'filter': 'WATCHLIST'},
            'Finished': {'color': 'Green', 'filter': 'FINISHED'},
            'Airing': {'color': 'Orange', 'filter': 'AIRING'},
            'Upcoming': {'color': 'Blue', 'filter': 'UPCOMING'},
            'Rated': {'color': 'Red', 'filter': 'RATED'},
            'By season': {'color': 'Blue', 'filter': 'SEASON'},
            'Random': {'color': 'Green', 'filter': 'RANDOM'},
            'No tags': {'color': 'White', 'filter': 'NONE'},
            'No filter': {'color': 'Gray', 'filter': 'DEFAULT'}}
        self.status = {
            'airing': 'AIRING',
            'Currently Airing': 'AIRING',
            'completed': 'FINISHED',
            'complete': 'FINISHED',
            'Finished Airing': 'FINISHED',
            'to_be_aired': 'UPCOMING',
            'tba': 'UPCOMING',
            'upcoming': 'UPCOMING',
            'Not yet aired': 'UPCOMING',
            'NONE': 'UNKNOWN',
            'UPDATE': 'UNKNOWN'}
        self.tag_options = {
            'Seen': {'color': 'Green', 'filter': 'SEEN'},
            'Watching': {'color': 'Orange', 'filter': 'WATCHING'},
            'Watchlist': {'color': 'Blue', 'filter': 'WATCHLIST'},
            'No tag': {'color': 'White', 'filter': 'NONE'},
        }

        self.checkSettings()

    def checkSettings(self):
        self.initLogs()
        self.log('CONFIG', "Settings:")
        if not os.path.exists(self.settingsPath):
            shutil.copyfile("settings.json", self.settingsPath)
        with open(self.settingsPath, 'r') as f:
            try:
                self.settings = json.load(f)
            except json.JSONDecodeError:
                # Settings file is corrupted
                self.log('MAIN_STATE', "[ERROR] - Can't open settings file, archiving it and recreating a new one")
                newpath = os.path.join(os.path.dirname(self.settingsPath), 'settings.json.old')
                try:
                    shutil.move(self.settingsPath, newpath)
                except Exception as e:
                    self.log('MAIN_STATE', f"[ERROR] - Can't archive settings file, overwriting it\n  - Error: {str(e)}")
                

                # Infinite loop if settings template is corrupted, but whatever
                return self.checkSettings()

        update = False
        for cat, values in self.settings.items():
            for var, value in values.items():
                if var in self.pathSettings:
                    # Check if path exists
                    if value == "" or not os.path.exists(value):
                        value = getattr(self, var)
                        # updatedSettings[var] = value
                        for cat, values in self.settings.items():
                            if var in values.keys():
                                self.settings[cat][var] = value
                                update = True
                                break
                    if var != "dbPath" and not os.path.exists(value):
                        try:
                            os.mkdir(value)
                        except FileNotFoundError:
                            self.log('CONFIG', 'Settings file corrupted: path does not exists!')
                setattr(self, var, value)
                self.log('CONFIG', " ", var.ljust(30), '-', value)
        if update:
            with open(self.settingsPath, 'w') as f:
                json.dump(self.settings, f, sort_keys=True, indent=4)
