from collections import deque
import json
import os
import queue
import sys
import time
from datetime import datetime, timezone
from types import NoneType

import requests

sys.path.append(os.path.abspath("../"))
try:
	from ..constants import Constants
	from ..classes import Anime, Character, NoIdFound
	from ..getters import Getters
	from ..utils import dict_merge
	from ..logger import Logger
except ModuleNotFoundError as e:
	print("Module not found:", e)

def cached_request(func):
	def wrapper(*args, **kwargs):
		self = args[0]
		self.queue.put((func, args, kwargs))
	return wrapper

class APIUtils(Logger, Getters):
	def __init__(self):
		Logger.__init__(self, logs="ALL")
		self.states = {
			'airing': 'AIRING',
			'Currently Airing': 'AIRING',
			'completed': 'FINISHED',
			'complete': 'FINISHED',
			'Finished Airing': 'FINISHED',
			'to_be_aired': 'UPCOMING',
			'tba': 'UPCOMING',
			'upcoming': 'UPCOMING',
			'Not yet aired': 'UPCOMING',
			'NONE': 'UNKNOWN'}

		# self.database = DummyDB(self.getDatabase())
		self.database = self.getDatabase()
		self.queue = queue.Queue()

	@property
	def __name__(self):
		return str(self.__class__).split("'")[1].split('.')[-1]

	def getStatus(self, data, reverse=True):
		if data['date_from'] is None:
			status = 'UNKNOWN'
		else:
			if not isinstance(data['date_from'], int):
				status = 'UPDATE'
			elif datetime.fromtimestamp(data['date_from'], timezone.utc) > datetime.now(timezone.utc):
				status = 'UPCOMING'
			else:
				if data['date_to'] is None:
					if data['episodes'] == 1:
						status = 'FINISHED'
					else:
						status = 'AIRING'
				else:
					if datetime.fromtimestamp(data['date_from'], timezone.utc) > datetime.now(timezone.utc):
						status = 'AIRING'
					else:
						status = 'FINISHED'
		return status

	def getId(self, id, table="anime"): # TODO - Same name as in database.py -> need renaming
		""" Get the internal id for an external id. Uses self.apiKey to determine the column to search! """

		table = {'anime': 'indexList', 'characters': 'charactersIndex'}.get(table, table)

		sql = f"SELECT {self.apiKey} FROM {table} WHERE id=?"
		with self.database.get_lock():
			api_id = self.database.sql(sql, (id,))

		if api_id == []:
			# self.log("Key not found!", sql, id)
			raise NoIdFound(id)
		return api_id[0][0]

	def getRates(self, name):
		with self.database.get_lock():
			data = self.database.sql('SELECT value FROM rateLimiters WHERE id=? AND name=?', (self.apiKey, name))
			if len(data) == 0:
				return None
			else:
				return data[0][0]

	def setRates(self, name, value):
		with self.database.get_lock():
			self.database.sql('INSERT OR REPLACE INTO rateLimiters(value) VALUES (?) WHERE id=? AND name=?', (value, self.apiKey, name), save=True) # TODO - Maybe save later?

	# Anime metadata

	@cached_request
	def save_relations(self, id, rels):
		# Rels must be a list of dicts, each containing three fields: 'type', 'name', 'rel_id'
		if len(rels) == 0:
			return

		with self.database.get_lock():
			db_rels = self.get_relations(id)
			for rel in rels:
				if rel["type"] == "anime": # TODO - Add support for other types or relations
					rel["id"] = int(id)

					# Get internal id for relation
					rel["rel_id"] = self.database.getId(self.apiKey, rel["rel_id"], table="anime")

					rel['type'] = str(rel['type']).lower().strip()
					rel['name'] = str(rel['name']).lower().strip()

					# Check if relation already exists
					found = False
					for e in db_rels:
						if e['id'] == id and rel['rel_id'] in e['rel_id']:
							if e['type'] != rel['type'] or e['name'] != rel['name']:
								# TODO - What to do if the relation's name/type is different?
								pass # Ignore for now

							found = True
							break

					if not found:
						k, v = list(zip(*rel.items()))
						sql = "INSERT INTO animeRelations (" + ",".join(k) + ") VALUES (" + ", ".join("?" * len(rel)) + ");"
						self.database.sql(sql, v)

	@cached_request
	def save_mapped(self, id, mapped):
		# mapped must be a list of tuples, each containing two elements: 'api_key' and 'api_id'
		if len(mapped) == 0:
			return

		return # TODO - Implement this
		with self.database.get_lock():
			for m in mapped:  # Iterate over each external anime
				api_key, api_ip = m

				# Get the id of the external anime
				sql = f"SELECT id FROM indexList WHERE {api_key}=?"

				associated = self.database.sql(sql, (api_ip,))
				if len(associated) == 0: continue

				ass_id = associated[0][0]
				if ass_id != id: # Merge both ids

					# Remove new id and merge with old one
					self.database.remove(id=id)

					# Merge
					self.database.sql(
						f"UPDATE indexList SET {api_key} = ? WHERE id=?",
						(api_ip, ass_id)
					)

					# TODO - Also update animeRelations!

	@cached_request
	def save_pictures(self, id, pictures):
		# pictures must be a list of dicts, each containing two fields: 'url', 'size'
		# return # TODO - Put all that stuff in a queue and process everything at once
		valid_sizes = ('small', 'medium', 'large', 'original')
		data = []
		for pic in pictures:
			if pic['size'] not in valid_sizes or pic['url'] is None:
				continue
			data.append(pic)

		args, out = self.database.procedure('save_picture', id, json.dumps(pictures))

	@cached_request
	def save_broadcast(self, id, w, h, m):
		with self.database.get_lock():
			args, out = self.database.procedure('save_broadcast', id, w, h, m)

	@cached_request
	def save_genres(self, id, genres):
		# Genres must be an iterable of str, the genre name

		if len(genres) == 0:
			return

		def format(g):
			return g.title().strip()
		genres = list(sorted(map(format, genres)))

		with self.database.get_lock():
			args, out = self.database.procedure('save_genres', id, json.dumps(genres))

	# Character metadata

	def save_animeography(self, character_id, animes):
		# animes must be a dict with keys being anime ids and values the role of the character

		with self.database.get_lock():
			for anime_id, role in animes.items():
				sql = "SELECT EXISTS(SELECT 1 FROM characterRelations WHERE id = ? AND anime_id = ?);"
				exists = bool(self.database.sql(sql, (character_id, anime_id))[0][0])

				if exists:
					# The relation already existed
					sql = "UPDATE characterRelations SET role = ? WHERE id = ? AND anime_id = ?;"
					self.database.sql(sql, (role, character_id, anime_id))
				else:
					# Create new relation
					sql = "INSERT INTO characterRelations(id, anime_id, role) VALUES(?, ?, ?);"
					self.database.sql(sql, (character_id, anime_id, role))

			# self.database.save()

	# def save_mapped_characters(self, ) TODO

	def handle_sql_queue(self):
		with self.database.get_lock():
			while not self.queue.empty():
				func, args, kwargs = self.queue.get()
				func(*args, **kwargs)

	def reroute_sql_queue(self, queue):
		old_queue = self.queue
		self.queue = queue

		while not old_queue.empty():
			data = old_queue.get()
			queue.put(data)

class EnhancedSession(requests.Session):
	def __init__(self, timeout=(3.05, 4)):
		self.timeout = timeout
		return super().__init__()

	def request(self, method, url, **kwargs):
		if "timeout" not in kwargs:
			kwargs["timeout"] = self.timeout
		return super().request(method, url, **kwargs)

class DummyDB:
	""" Fake db to cache requests. Will only run SELECT comands """
	
	def __init__(self, db) -> NoneType:
		self.db = db
		self.cache = deque()
 
	def sql(self, sql, *args, **kwargs):
		if sql.startswith('SELECT '):
			return self.db.sql(sql, *args, **kwargs)
		else:
			self.cache.append(('sql', sql, args, kwargs))

	def cache_wrapper(self, func_name):
		def wrapper(*args, **kwargs):
			self.cache.append((func_name, args, kwargs))
		if func_name in ('save',):
			return lambda *args, **kwargs: None
		return wrapper

	def __getattr__(self, name):
		if name in ('getId','get_lock',):
			return self.db.__getattribute__(name)

		return self.cache_wrapper(name)
		# return super().__getattr__(name)
