import requests

try:
    from .base import *
except ImportError:
    from base import *

class Deluge(BaseTorrentManager):
    name = 'Deluge'

    def request(self, method, params=[]):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        if self.session is None:
            raise ConnectionError('Not connected')

        r = self.session.post(self.url + "/json", headers=headers, json={'method': method, 'params': params, 'id': self.id})
        r.raise_for_status()
        data = r.json()

        if data['id'] != self.id:
            raise ValueError('Incorrect ID')

        if data['error'] is not None:
            # Code 2, Unknown method -> not connected to host
            raise APIException(data['error']['message'], code=data['error']['code'])

        return data['result']

    def initialize(self):
        url = self.settings.get('url', '')
        if url == '':
            return self.login_dialog()
        
        self.url = url

        self.daemon = self.settings.get('daemon', '') or None
        self.password = self.settings.get('password', '') or None

        self.session = requests.Session()
        self.id = 1#random.randint(1, 1000)

        self.connect()
    
    def connect(self):
        try:
            r = self.request(method="auth.login", params=[self.password])
            if r is False:
                self.connect()
            r = self.request(method="web.get_hosts")
            hosts = {h[0]: Host(*h) for h in r}

            for host in hosts:
                r = self.request(method="web.get_host_status", params=[host])
                hosts[r[0]].status = r[1]
                hosts[r[0]].version = r[2]

            # TODO - Select host?
            h_id = next(iter(hosts), self.daemon)
            host = hosts[h_id]
            if host.status == 'Offline':
                self.request('web.start_daemon', [host.port])

            r = self.request("web.connect", [host.id])
            # Returns API endpoints, just like self.request('daemon.get_method_list')
        except requests.HTTPError as e:
            self.login_dialog()
            return
        except requests.ConnectionError:
            # Invalid url or server is down
            self.login_dialog()
            return
        except Exception as e:
            self.login_dialog()
            raise
 
    def login_dialog(self):
        fields = {}
        fields_name = {'url': 'url', 'daemon': 'Daemon port', 'password': 'password'}
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
        args = {}
        if path is not None:
            args['download_location']=path
        for magnet in magnets:
            self.request('core.add_torrent_magnet', [magnet, args])

    def list(self, filter=None, hashes=None):
        if filter is not None:
            if filter == TorrentListFilter.ALL:
                filter = {'state': 'All'}
            elif filter == TorrentListFilter.COMPLETED:
                filter = {'state': 'Seeding'}
            elif filter == TorrentListFilter.DOWNLOADING:
                filter = {'state': 'Downloading'}
            else:
                filter = None

        r = self.request('web.update_ui', [[], filter or {}])
        # self.request('core.get_session_state') will list only torrent hashes

        if hashes:
            iterator = (r['torrents'][h] for h in hashes)
        else:
            iterator = r['torrents'].values()

        data = []
        for torrent in iterator:
            data.append(self.convert(torrent))

        return data

    def move(self, path, hashes):
        self.request('core.move_storage', [hashes, path])

    def delete(self, hashes):
        self.request('core.remove_torrents', [hashes, True])

    def convert(self, data):
        t = Torrent(
            hash=data['hash'],
            name=data['name'],
            trackers=list(map(lambda t: t['url'], data['trackers'])),
            size=data['total_size'],
            downloaded=data['total_done'],
            path = data['download_location']
        )
        return t

class Host:
    def __init__(self, id, url, port, name, status=None, version=None) -> None:
        self.id = id
        self.url = url
        self.port = port
        self.name = name
        self.status = status
        self.version = version

    def __repr__(self):
        return f'Host({self.id})'

class APIException(Exception):
    def __init__(self, *args: object, code=None) -> None:
        super().__init__(*args)
        self.code=code

if __name__ == '__main__':
    args = {
        'url': 'http://localhost:8112',
        'daemon': '58846',
        'password': 'deluge'
    }
    client = Deluge(args)
    m = 'magnet:?xt=urn:btih:a803e7839826991c5ba2ff9c025bf50c799caa7a&dn=%5BSubsPlease%5D%20Jujutsu%20Kaisen%20-%2028%20%281080p%29%20%5BE7B572D9%5D.mkv&tr=http%3A%2F%2Fnyaa.tracker.wf%3A7777%2Fannounce&tr=udp%3A%2F%2Fopen.stealth.si%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fexodus.desync.com%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce'
    client.delete(['a803e7839826991c5ba2ff9c025bf50c799caa7a'] )
    client.add([m], 'C:\\Users\\William\\Documents')
    torrents = client.list()
    pass