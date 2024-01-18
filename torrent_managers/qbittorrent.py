import threading
import qbittorrentapi

try:
    from .base import *
except ImportError:
    from base import *

class qBittorrent(BaseTorrentManager):
    name = 'qBittorrent'

    def __init__(self, *args, **kwargs):
        self.qb = None
        super().__init__(*args, **kwargs)

    def initialize(self):
        self.url = self.settings.get('url', '')
        if self.url == '':
            return self.login_dialog()

        self.login = self.settings.get('login', '')
        self.password = self.settings.get('password', '')

        self.timeout = self.settings.get('timeout', 2) # TODO
        self.login_event = threading.Event()
        self.connect()
    
    def connect(self, thread=True):
        if thread is True:
            # Use a different thread to avoid blocking
            threading.Thread(target=self.connect, args=(False,)).start()
            return

        try:
            if self.qb is not None:
                self.qb.auth_log_out()

            self.qb = qbittorrentapi.Client(self.url, REQUESTS_ARGS={'timeout': (2, 2)})
            self.qb.auth_log_in(self.login, self.password)

        except qbittorrentapi.exceptions.NotFound404Error as e:
            # 404 Not Found
            return self.login_dialog(failed=True)
        except qbittorrentapi.exceptions.APIConnectionError as e:
            # Unknown error
            if isinstance(e, qbittorrentapi.LoginFailed) or e.args[0].startswith('Failed to connect to qBittorrent'):
                self.qb = None
                self.login_event = None
                # Can't find client, so just ignore
                print("Couldn't connect to qBittorrent client!")
                return None
            return self.login_dialog(failed=True)
        else:
            if not self.qb.is_logged_in:
                # Probably invalid credentials
                return self.login_dialog(failed=True)
            else:
                args = self.settings.get('qb_settings', None)
                if args:
                    self.qb.app_set_preferences(args)

                self.login_event.set()

    def login_dialog(self, failed=False):
        fields = {}
        fields_name = {'url': 'url', 'user': 'login', 'password': 'password'}
        for field, name in fields_name.items():
            fields[name] = self.settings.get(field, None)
        validator = lambda r: 1 if r.get('url', '') != '' else "No URL provided"

        title = 'Login to qBittorrent UI'
        if failed:
            title = 'An error occured, please try again\n' + title

        dialog = LoginDialog(
            fields = fields, 
            title = title, 
            validator = validator
        )
        data = dialog.results

        settings = {}
        for field, name in fields_name.items():
            settings[field] = data.get(name, '')

        self.settings = settings

        self.initialize()

    @staticmethod
    def wait_connection(func):
        def wrapper(self, *args, **kwargs):
            if self.qb is None or not self.login_event.is_set():
                # Not connected yet
                if self.login_event is None:
                    # Error while connecting
                    raise TorrentException("Couldn't connect to qBittorrent")

                connected = self.login_event.wait(self.timeout)
            
                if not connected or self.qb is None:
                    # Couldn't connect
                    raise TorrentException("Couldn't connect to qBittorrent")
            
            return self.error_wrapper(func)(self, *args, **kwargs)
        return wrapper

    @wait_connection
    def add(self, magnets, path=None):
        self.qb.torrents_add(urls= magnets, save_path=path)

    @wait_connection
    def list(self, filter=None, hashes=None):
        if filter is not None:
            if filter == TorrentListFilter.ALL:
                filter = 'all'
            elif filter == TorrentListFilter.COMPLETED:
                filter = 'completed'
            elif filter == TorrentListFilter.DOWNLOADING:
                filter = 'downloading'
            else:
                filter = None

        if len(hashes) == 0:
            hashes = None


        torrents = self.qb.torrents_info(
			status_filter=filter,
            torrent_hashes=hashes
        )
        data = list(map(self.convert, torrents.data))
        return data

    @wait_connection
    def move(self, path, hashes):
        self.qb.torrents_set_location(
            location=path, 
            torrent_hashes=hashes
        )

    @wait_connection
    def delete(self, hashes):
        self.qb.torrents_delete(
            delete_files=True,
            torrent_hashes=hashes
        )

    def convert(self, data):
        if hasattr(data, 'magnet_uri'):
            t = Torrent.from_magnet(data.magnet_uri)
        # t = Torrent(
        #     hash=data.hash,
        #     name=data.name,
        #     trackers=None,
        #     size=data.size
        # )
        t.size = data.size
        t.downloaded = data.completed
        t.path = data.save_path
        return t

if __name__ == '__main__':
    args = {
        'url': 'localhost:8081',
        'login': 'admin',
        'password': '123456789'
    }
    qb = qBittorrent(args)
    torrents = qb.list()
    t = qb.list(hashes=[torrents[0].hash])
    pass