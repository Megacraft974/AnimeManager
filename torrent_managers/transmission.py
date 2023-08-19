from urllib.parse import urlparse
from transmission_rpc import Client, torrent as transmission_torrent

try:
    from .base import *
except ImportError:
    from base import *

class Transmission(BaseTorrentManager):
    name = 'Transmission'

    def initialize(self):
        url = self.settings.get('url', '')
        if url == '':
            return self.login_dialog()
        
        parsed = urlparse(url)
        self.url = parsed.path
        self.port = parsed.port or 9091 # Default value

        self.login = self.settings.get('login', '') or None
        self.password = self.settings.get('password', '') or None

        self.connect()
    
    def connect(self):
        try:

            self.client = Client(host=self.url, port=self.port, username=self.login, password=self.password, timeout=2)

        except Exception as e:
            self.login_dialog()
            raise
 
    def login_dialog(self):
        fields = {}
        fields_name = {'url': 'url', 'user': 'login', 'password': 'password'}
        for field, name in fields_name.items():
            fields[name] = self.settings.get(field, None)
        validator = lambda r: 1 if r.get('url', '') != '' else "No URL provided"

        dialog = LoginDialog(
            fields = fields, 
            title = 'Login to qBittorent UI', 
            validator = validator
        )
        data = dialog.results

        settings = {}
        for field, name in fields_name.items():
            settings[field] = data.get(name, '')

        self.settings = settings

        self.initialize()

    def add(self, magnets, path=None):
        for magnet in magnets:
            self.client.add_torrent(torrent=magnet, download_dir=path)

    def list(self, filter=None, hashes=None):
        if filter is not None:
            if filter == TorrentListFilter.ALL:
                filter = None
            elif filter == TorrentListFilter.COMPLETED:
                filter = lambda t: t.seeding or t.seed_pending
            elif filter == TorrentListFilter.DOWNLOADING:
                filter = lambda t: t.downloading or t.download_pending
            else:
                filter = None

        torrents = self.client.get_torrents(hashes)

        data = []
        for torrent in torrents:
            if filter is None or filter(torrent):
                data.append(self.convert(torrent))

        return data

    def move(self, path, hashes):
        self.client.move_torrent_data(ids=hashes, location=path)

    def delete(self, hashes):
        self.client.remove_torrent(hashes, delete_data=True)

    def convert(self, data):
        t = Torrent(
            hash=data.hashString,
            name=data.name,
            trackers=data.tracker_list,
            size=data.total_size,
            downloaded=int(data.percent_done * data.total_size),
            path = data.download_dir
        )
        return t

if __name__ == '__main__':
    args = {
        'url': 'localhost',
        'login': 'admin',
        'password': '123456789'
    }
    client = Transmission(args)
    torrents = client.list()
    t = client.list(hashes=[torrents[0].hash])
    pass