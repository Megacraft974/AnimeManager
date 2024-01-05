import json
import multiprocessing
import os
import queue
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import traceback
import urllib.parse
import webbrowser
from tkinter import *
from classes import Torrent
import torrent_managers

try:
	import sys

	import requests
	import bencoding
	import requests
	from lxml import etree
	from PIL import Image, ImageTk
	from pypresence import Presence
	from thefuzz import fuzz
	if getattr(sys, 'frozen', None):
		basedir = sys._MEIPASS
		os.environ['REQUESTS_CA_BUNDLE'] = os.path.join(basedir, 'certifi', 'cacert.pem')  # Required for requests and certifi
except ModuleNotFoundError as e:
	import sys
	if getattr(sys, 'frozen', None):
		print(f"Module missing: {e}")
	else:
		print(f"Installing modules! {e}")
		subprocess.run([
			sys.executable,
			"-m",
			"pip", 
			"install", 
			"qbittorrent-api", 
			"lxml", 
			"jikanpy", 
			"jsonapi_client", 
			"requests", 
			"Pillow", 
			"bencoding", 
			"thefuzz", 
			"python-mpv", 
			"python-vlc", 
			"pypresence",
			# "ffpyplayer", 
			# "python-Levenshtein"
		])
		# os.execv(sys.executable, ['python'] + sys.argv) # Restart the app
	time.sleep(20)

	sys.exit()

globals()['auto_launch_initialized'] = True

try:
	import animeAPI
	import search_engines
	import utils
	import mobile_server
	import windows
	from classes import (Anime, AnimeList, Character, Magnet, SortedDict,
						 SortedList, TorrentList)
	from constants import Constants
	from dbManager import db
	from discord_presence import DiscordPresence
	from getters import Getters
	from logger import Logger
	from media_players import MediaPlayers
	from update_utils import UpdateUtils
	from classes import DefaultDict
	from file_managers import LocalFileManager, FTPFileManager
except ModuleNotFoundError as e:
	print(f"Please verify your app installation!\n{traceback.format_exc()}")
	import sys
	sys.exit()

# TodoList - Yeah I know there are better tools for that but I'm lazy
# TODO - Torrent path dependent of file manager / multiple file managers?
# TODO - Look for torrent client on file system + give installation link?
# TODO - Multiple torrent clients compatibility (module-like)
# TODO - App Installer
# TODO - Relations tree
# TODO - simkl.com API
# TODO - Logger panel
# TODO - characterWindow - fix 'Go to anime' button
# TODO - Hardcoded 'dual audio' in torrents search keys
# TODO - Fix multi word search -> just search
# TODO - Fix known torrent color match in getTorrentColor() -> compare file length?
# TODO - Tkinter event queue
# TODO - Recently finished anime should appear on top of the watching filter 
# TODO - Fix characters API
# TODO - Use the db.get_lock() with API wrappers
# TODO - Factory functions for characters and anime mappings
# TODO - RPC animes storage size is incorrect
# TODO - What to do with the MAL API token registration? - Idk?
# TODO - Load new images on downloading error
# TODO - Implement the TableFrame class
# TODO - Add filter for torrent list (seeds / name)
# TODO - Play button on media player isn't centered
# TODO - Update the loading... text on media player
# TODO - Exception ignored in Var.__del__ on media player
# TODO - Put single files in directories
# TODO - Add search by studios ?
# TODO - Add pictures window
# TODO - Allow window resizing ?
# TODO - Auto associate latest torrents ?
# TODO - Add python-based torrent client -> uh oh complicated
# TODO - Add RSS option
# TODO - Automatic torrent downloading from RSS?
# TODO - Qt windows / themes
# TODO - Phone version -> Yup maybe not (Apple dev licence is too expensive)
# TODO - Web version


class Manager(Constants, Logger, UpdateUtils, Getters, MediaPlayers, DiscordPresence, *windows.windows()):
	def __init__(self, remote=False):
		self.start = time.time()
		Logger.__init__(self)
		Constants.__init__(self)

		self.remote = remote
		self.animeFolder = []
		self.searchQueue = []
		self.relationIds = []
		self.characterIds = []
		self.animeHashes = {}
		self.timer_id = None
		self.stopSearch = False
		self.closing = False
		self.maxLogsSize = 50000  # In bytes
		self.blank_image = None

		self.root = None
		self.initWindow = None
		self.logsWindow = None
		self.optionsWindow = None
		self.ddlWindow = None
		self.fileListWindow = None
		self.torrentFilesWindow = None
		self.loadingWindow = None
		self.characterListWindow = None
		self.characterWindow = None
		self.settingsWindow = None
		self.diskWindow = None
		self.textPopupWindow = None
		self.searchTermsWindow = None

		self.menuOptions = {
			'Liked characters': {'color': 'Green', 'command': lambda: self.drawCharactersWindow("LIKED")},
			'Disk manager': {'color': 'Orange', 'command': self.drawDiskWindow},
			'Log panel': {'color': 'Blue', 'command': self.drawLogsWindow},
			'Clear logs': {'color': 'Green', 'command': self.clearLogs},
			'Clear cache': {'color': 'Blue', 'command': self.clearCache},
			# 'Clear db': {'color': 'Red', 'command': self.clearDb},
			'Settings': {'color': 'Gray', 'command': self.drawSettingsWindow},
			'Reload': {'color': 'Orange', 'command': self.reloadAll},
			'Exit': {'color': 'Red', 'command': self.quit}}
		self.actionButtons = (
			{'text': 'Copy title', 'color': 'Green', 'command': self.copy_title},
			{'text': 'Reload', 'color': 'Blue', 'command': self.reload},
			{'text': 'Redownload files', 'color': 'Green', 'command': self.redownload},
			{'text': 'Characters', 'color': 'Green', 'command': self.drawCharactersWindow},
			{'text': 'Delete seen episodes', 'color': 'Blue', 'command': self.deleteSeenEpisodes},
			{'text': 'Delete all files', 'color': 'Red', 'command': self.deleteFiles},
			{'text': 'Remove from db', 'color': 'Red', 'command': self.delete},)

		self.startup()

	def startup(self):
		self.getFileManager()
		# TODO - Put that in settings

		with self.getDatabase() as self.database:
			if not os.path.exists(self.dbPath):
				self.checkSettings()
				self.reloadAll()
				return
			else:
				self.checkSettings()

			if not self.remote:
				try:
					self.drawInitWindow()
				except Exception as e:
					self.log("MAIN_STATE", "[ROOT]:\n", traceback.format_exc())
				finally:
					self.quit()
			else:
				self.late_startup()

	def late_startup(self):
		MediaPlayers.__init__(self)
		DiscordPresence.__init__(self)
		
		if not self.remote:
			self.animeList.from_filter("DEFAULT")

		self.api = animeAPI.AnimeAPI('all', self.dbPath)
		
		for player_name in self.players_order:
			if player_name in self.media_players:
				self.player = self.media_players[player_name]
				break
		else:
			# No player found
			self.player = None
			self.log('MAIN_STATE', '[ERROR] - No media player found!')


		# self.last_broadcasts = self.getBroadcast()
		self.getTorrentManager()
		# TODO - Put that in settings

		self.RPC_menu()
		self.checkServer()

		self.getSchedule(thread=True)

		self.log('TIME', "Ready:".ljust(25), round(
			time.time() - self.start, 2), "sec")

	# ___Search___
	def search(self, event=None, force_search=False):
		if event:
			# if not event.char:
			# 	# Probably a modifier key - ignore
			# 	return

			if event.state & 0x4 != 0:
				# Control modifier
				force_search=True
			else:
				# Maybe return?
				pass

		terms = self.searchTerms.get()
		if len(terms) > 2 or force_search:
			if not force_search:
				animeList = self.searchDb(terms)

			if not force_search and animeList is not False:
				self.animeList.set(animeList)

			else:
				self.stopSearch = False
				self.loading()
				self.log("Searching {} with APIs".format(terms))
				self.animeList.set(self.api.searchAnime(terms, limit=self.animePerPage))
		else:
			self.animeList.from_filter("DEFAULT")

		if self.root is None:
			return

	def searchDb(self, terms):
		def fuzzy_enumerator(terms):  # Unused
			sql = """
				SELECT value, anime.*
				FROM title_synonyms
				JOIN anime using(id)
				GROUP BY anime.id
				ORDER BY anime.date_from DESC;
			"""

			match_threshold = 70
			partial_threshold = 50
			keys = list(self.database.keys(table="anime"))
			match = SortedList(keys=[(lambda e: e[1], True)])
			partial = []
			for data in self.database.sql(sql):
				ratio = fuzz.WRatio(terms, data[0])
				if ratio >= match_threshold:
					match.append((data[1:], ratio))
				elif ratio >= partial_threshold:
					partial.append((data[1:], ratio))
			if len(match) == 0:
				yield False
				return
			else:
				yield True
			for data in match + partial:
				yield Anime(keys=keys, values=data[0])

		def like_enumerator(terms):
			sql = """
				SELECT anime.*
				FROM anime
				JOIN title_synonyms using(id)
				WHERE LOWER(value) LIKE "%{}%"
				GROUP BY anime.id
				ORDER BY anime.date_from DESC;
			"""

			keys = list(self.database.keys(table="anime"))
			matchs = self.database.sql(sql.format(terms.lower()))
			if len(matchs) == 0:
				yield False
				return
			else:
				yield True
				for m in matchs:
					yield Anime(keys=keys, values=m)

		def searchNgrams(self, terms):  # TODO
			def ngrams(string, n=3):
				string = [l for l in string.lower() if l.isalnum() or l == " "]
				ngrams = zip(*[string[i:] for i in range(n)])
				return (''.join(ngram) for ngram in ngrams)

			with self.database.get_lock():
				data = self.database.sql("SELECT id, value FROM title_synonyms")

				t_ngrams = set(ngrams(terms))
				matches = DefaultDict(default=0)
				for id, value in data:
					for ngram in ngrams(value): # Removed comment
						if ngram in t_ngrams:
							matches[id] += 1

				sql = 'SELECT * FROM anime WHERE id IN(' + ','.join("?" * len(matches)) + ');'
				return AnimeList(
					Anime(data)
					for data in SortedList(
						[(lambda e: matches[e['id']], True)]
					).extend(
						self.database.sql(
							sql,
							matches.keys(),
							to_dict=True
						)
					)
				)

		def match_enumerator(terms):
			sql = """
				SELECT value, anime.*
				FROM title_synonyms
				JOIN anime using(id)
				GROUP BY anime.id
				ORDER BY anime.date_from DESC
				LIMIT 0, 1000;
			"""

			start = time.time()

			keys = list(self.database.keys(table="anime"))
			date_key_idx = keys.index('date_from')
			match = SortedList(keys=[(lambda e: e[1], True), (lambda e: e[0][date_key_idx] or '0', True)])

			threshold = 0.5 # Min fraction of the terms must match
			max_matchs = 50 # Maximum amount of animes to return

			terms = set(term for term in terms.lower().split(' '))
			terms_count = len(terms)

			marked = False
			count = 0

			threshold_count = int(threshold * terms_count)
			entries = self.database.sql(sql)
			# Make sure that there are no other calls to db while iterating
			print(f'Anime search: {time.time()-start}s')
			for data in entries:
				title = data[0].lower()

				matchs = 0
				for term in terms:
					# Count how many words actually match
					if term in title:
						matchs += 1

				if matchs > threshold_count:
					if not marked:
						# There is at least one entry
						yield True
						marked = True

					anime = Anime(keys=keys, values=data[1:])
					yield anime

					count += 1
					if count >= max_matchs:
						# Break if we have enough matchs
						return

					# match.append((data[1:], matchs))

			if not marked and len(match) == 0:
				# No data found
				yield False
				return

		terms = "".join([c for c in terms if c.isalnum()]).lower()
		# return self.searchNgrams(terms)

		# enum = fuzzy_enumerator(terms)
		# enum = like_enumerator(terms)
		enum = match_enumerator(terms)
		if next(enum):
			anime_list = AnimeList(enum)
			return anime_list
		else:
			return False

	# ___Clean up___
	def clearLogs(self):
		for f in os.listdir(self.logsPath):
			path = os.path.join(self.logsPath, f)
			if path != self.logFile:
				os.remove(path)

	def clearCache(self):  # TODO
		if self.cache is None or len(self.cache) == 0:
			self.log("MAIN_STATE", "[ERROR] - Cache path is invalid!")
		cmd = 'del /F /S /Q "{}"'.format(self.cache)
		try:
			subprocess.run(cmd)
			shutil.rmtree(self.cache)
		except Exception as e:
			self.log("MAIN_STATE", "[ERROR] - Cannot delete cache:", e, "-", cmd)

	def clearDb(self):
		# ONLY FOR TESTING!!! DO NOT USE WITH PROD DB!
		try:
			self.database.close()
		except Exception as e:
			self.log("DB_ERROR", "Database already closed?")
		try:
			os.remove(self.dbPath)
		except PermissionError as e:
			self.log("DB_ERROR", "File is already used", e)
		else:
			shutil.rmtree(self.cache)
			self.database = self.getDatabase()
			self.reloadAll()

	def quit(self):
		if self.closing is True:
			return

		self.log('MAIN_STATE', "Stopping")
		self.root.withdraw()

		self.start = time.time()

		self.stopSearch = True
		self.closing = True

		if self.initWindow is not None and self.initWindow.winfo_exists():
			self.initWindow.destroy()

		try:
			self.RPC_stop()
			self.updateAll()
		except Exception as e:
			self.log('MAIN_STATE', f"Error while stopping: {e}")

		self.database.close()

		self.root.destroy()
		self.root = None

		self.log('TIME', "Stopping time:".ljust(25),
					round(time.time() - self.start, 2), 'sec')

	# ___Utils___
	def mainloop_error_handler(self, exc, val, tb):
		if isinstance(exc, TclError) and "application has been destroyed" in val:
			self.log("MAIN_STATE", "[ERROR] - In tkinter mainloop: Application has been destroyed")
		else:
			self.log("MAIN_STATE", "[ERROR] - In tkinter mainloop:\n", ''.join(map(lambda t: t.replace('  ', '    '), traceback.format_exception(exc, val, tb))))

		if isinstance(exc, sqlite3.ProgrammingError) and "SQLite objects created in a thread can only be used in that same thread" in val:
			self.quit()
			self.startup()

	def reloadAll(self):
		self.log('MAIN_STATE', "Reloading")
		self.stopSearch = True
		self.closing = True
		try:
			self.initWindow.destroy()
		except Exception:
			pass
		self.initWindow = None

		self.drawLoadingWindow()

		processes = self.updateAllProgression()
		lenght = next(processes)

		self.start = time.time()
		loadStart = 0
		for i, item in enumerate(processes):
			thread, text = item
			try:
				self.loadLabel['text'] = text
			except Exception:
				if not self.loadingWindow.winfo_exists():
					break
			loadStop = (i + 1) / lenght * 100
			while thread.is_alive():
				time.sleep(1 / 60)
				loadStart += (loadStop - loadStart) / max(100 - loadStop, 2)
				try:
					self.loadProgress['value'] = loadStart
				except Exception:
					if self.closing or not self.loadingWindow.winfo_exists():
						break

		try:
			self.loadingWindow.destroy()
			# self.quit()
		except Exception:
			pass
		try:
			self.log('TIME', "Reload time:".ljust(25),
					 round(time.time() - self.start, 2), 'sec')
		except AttributeError:
			pass
		# self.startup()
		self.closing = False

		if not os.path.exists(self.dbPath):
			self.checkSettings()
			self.reloadAll()
			return
		else:
			self.checkSettings()

		# self.player = self.media_players[self.player_name]

		for player_name in self.players_order:
			if player_name in self.media_players:
				self.player = self.media_players[player_name]
				break
		else:
			# No player found
			self.player = None
			self.log('MAIN_STATE', '[ERROR] - No media player found!')

		# self.last_broadcasts = self.getBroadcast()

		# self.RPC_stop()
		DiscordPresence.__init__(self)
		self.RPC_menu()

		if not self.remote:
			self.drawInitWindow()

	def view(self, id):
		index = "indexList"
		# keys = self.database.keys(table="indexList")
		ids = self.database.sql("SELECT * FROM indexList WHERE id=?", (id,), to_dict=True)[0]
		# ids = dict(zip(keys, ids))
		ids.pop("id")
		for api_key, id in ids.items():
			if id is not None and api_key in self.websitesViewUrls.keys():
				url = self.websitesViewUrls[api_key].format(id)
				threading.Thread(target=webbrowser.open, args=(url,), daemon=True).start()

	def loading(self, n=0, after=False):
		if self.stopSearch:
			self.loadCanvas.delete(ALL)
			self.timer_id = None
			return
		elif self.timer_id is None or after:
			n = n % len(self.giflist)
			gif = self.giflist[n % len(self.giflist)]
			self.loadCanvas.delete(ALL)
			self.loadCanvas.create_image(
				gif.width() // 2, gif.height() // 2, image=gif)
		if self.timer_id is not None:
			self.initWindow.after_cancel(self.timer_id)
		self.timer_id = self.initWindow.after(30, self.loading, n + 1, True)  # TODO - Use a timer instead of n

	# ___Networking___
	def downloadFile(self, id, url=None, hash=None):
		def handler(id, out, url=None, hash=None):
			# Get torrent data (url / magnet / file)
			if url is not None:
				if isinstance(url, Magnet):
					url = url.get()
				pattern = re.compile(r"^magnet:\?xt=urn:")

				if pattern.match(url):
					# Magnet url
					isMagnet = True
					# self.log('NETWORK', 'Added magnet link:', url)
					torrent = Torrent.from_magnet(url)

				else:
					# Torrent file url
					try:
						# When nyaa.si blocked my ip:
						# if url.startswith("https://nyaa.si/"):
						#     url = "https://torproxy.cyou/?cdURL="+url
						req = None
						req = requests.get(url, allow_redirects=True)
					except Exception:
						self.log(
							'NETWORK',
							"[ERROR] - Error downloading file at url",
							url,
							"status_code",
							req.status_code if req is not None else "unknown")
						out.put(False) # Download failed
						return
					
					torrent = Torrent.from_file(req.content)
			
			elif hash is not None:
				# Should already be in database
				# TODO - hash is sometimes the anime title??
				database = self.getDatabase()
				data = database.sql('SELECT name, trackers FROM torrents WHERE hash=?', (hash,))[0]
				torrent = Torrent(hash=hash, name=data[0], trackers=data[1])

			else:
				self.log('MAIN_STATE', '[ERROR] - No torrent provided!')
				out.put(False) # Download failed
				return

			# Add torrent to database
			database = self.getDatabase()
			with database.get_lock():
				self.saveTorrent(id, torrent)

				if database(id=id, table='anime')['tag'] != 'WATCHING':
					database.set({'id': id, 'tag': 'WATCHING'}, table='anime', get_output=False)
				database.save()

			# Add torrent to client
			try:
				out.put(True) # Download started
				path = self.getFolder(id)

				# Get anime folder
				if not self.fm.exists(path):
					try:
						self.fm.mkdir(path)
					except FileExistsError:
						pass

				# Start downloading
				try:
					self.tm.add([torrent.to_magnet()], path=path)

					# Try to move torrents to anime folder					
					self.tm.move(path=path, hashes=[torrent.hash])
				except torrent_managers.TorrentException as e:
					out.put(False)
					self.log('NETWORK', f"[ERROR] - {str(e)}")
				else:
					self.log('NETWORK', 'Successfully downloaded torrent, hash:', torrent.hash)

			except Exception as e:
				out.put(False) # Download failed
				self.log(
					'NETWORK', f"[ERROR] - {str(e)}")

		assert url is not None or hash is not None, "You need to specify either an url or a file path"
		out = queue.Queue()
		threading.Thread(target=handler, args=(id, out, url, hash), daemon=True).start()
		return out

	def redownload(self, id):
		try:
			torrents = self.getTorrents(id)

			for torrent in torrents:
				self.downloadFile(id, url=torrent.to_magnet())

			if len(torrents) > 0:
				self.log(
					'NETWORK',
					'Redownloaded {} torrents'.format(
						len(torrents)))
			else:
				self.log(
					'NETWORK',
					'No torrents to download!'.format(
						len(torrents)))

		except torrent_managers.TorrentException as e:
			self.log('NETWORK', f"[ERROR] - {str(e)}")

	def search_torrent(self, id, parent=None):
		def callback(var, id):
			text = var.get()
			self.textPopupWindow.exit()

			web_reg = re.compile(r"^(http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)$")
			mag_reg = re.compile(r"^magnet:\?xt=urn:\S+$")
			if re.match(web_reg, text):
				# Web url
				self.downloadFile(id, url=text)
			elif re.match(mag_reg, text):
				# Magnet url
				self.downloadFile(id, url=text)
			else:
				# Torrent title
				self.addSearchTerms(id, text)
				fetcher = search_engines.search([text])
				self.drawDdlWindow(id, fetcher, parent=self.torrentFilesWindow)

		self.drawTextPopupWindow(
			parent or self.root,
			"Search torrents with name:",
			lambda var,
			id=id: callback(var, id),
			fentype="TEXT")

	def bluetoothConnect(self):
		pass
		# TODO -> En fait c'est chiant

	def checkServer(self):
		if threading.main_thread() == threading.current_thread():
			threading.Thread(target=self.checkServer, daemon=True).start()
			return
		if self.enableServer:
			self.server = mobile_server.startServer(
				self.hostName, self.serverPort, self.dbPath, self)
		elif self.server is not None:
			mobile_server.stopServer(self.server, self)
			self.server = None

if __name__ == '__main__':
	multiprocessing.freeze_support()
	p = multiprocessing.current_process()
	if p.name == 'MainProcess':
		m = Manager()
