import string
from urllib.parse import urlparse
from transmission_rpc import Client, torrent as transmission_torrent

from .base import *

class Transmission(BaseTorrentManager):
	name = 'Transmission'

	def initialize(self):
		url = self.settings.get('url', '')
		if url == '':
			return self.login_dialog()
		
		parsed = urlparse(url)
		self.url = parsed.path
		self.port = parsed.port or 9091 # Default value

		self.login = self.settings.get('user', '') or None
		self.password = self.settings.get('password', '') or None

		self.connect()
	
	def connect(self):
		try:

			self.client = Client(host=self.url, port=self.port, username=self.login, password=self.password, timeout=2)

		except Exception as e:
			self.login_dialog()
		else:
			self.client.set_session(incomplete_dir_enabled=False)
			print('Succesfully connected to Transmission torrent client!')
 
	def login_dialog(self):
		fields = {}
		fields_name = {'url': 'url', 'user': 'login', 'password': 'password'}
		for field, name in fields_name.items():
			fields[name] = self.settings.get(field, None)
		validator = lambda r: 1 if r.get('url', '') != '' else "No URL provided"

		dialog = LoginDialog(
			fields = fields, 
			title = 'Login to Transmission Web UI', 
			validator = validator
		)
		data = dialog.results

		if data is None:
			raise ConnectionAbortedError()

		settings = {}
		for field, name in fields_name.items():
			settings[field] = data.get(name, '')

		self.settings = settings

		self.initialize()

	def add(self, magnets, path=None):
		out = []
		for magnet in magnets:
			t = self.client.add_torrent(torrent=magnet, download_dir=path)
			out.append(self.convert(t))
		return out

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
		
		if hashes is None:
			hashes = []
		invalid_hash = lambda h: len(h) != 40 or (set(h) - set(string.ascii_letters+string.digits))

		torrents = self.client.get_torrents([h for h in hashes if not invalid_hash(h)])

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
			hash=data.hashString, # this one better be there
			name=data.get('name', None),
			trackers=data.get('trackers', []),
			size=data.get('total_size', 0),
			downloaded=int(data.get('percent_done', 0) * data.get('total_size', 0)),
			path = data.get('download_dir', '')
		)
		return t

if __name__ == '__main__':
	args = {
		'url': 'william-server.local',
		'user': 'admin',
		'password': '123456789',
		"dataPath": "/home/william/Documents/Anime Manager"
	}
	client = Transmission(args)
	torrents = client.list()
	# t = client.list(hashes=[torrents[0].hash])
	m = 'magnet:?xt=urn:btih:07706a525dc18b117638d801a629031657af29fd&dn=%5BSubsPlease%5D+Jujutsu+Kaisen+-+45+%28720p%29+%5BB18505A3%5D.mkv&tr=http%3A%2F%2Fnyaa.tracker.wf%3A7777%2Fannounce&tr=udp%3A%2F%2Fopen.stealth.si%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fexodus.desync.com%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce'
	p = '/home/william/Documents/Anime Manager/Animes/Jujutsu Kaisen Season 2 - 27049'
	client.add([m], path=p)
	pass