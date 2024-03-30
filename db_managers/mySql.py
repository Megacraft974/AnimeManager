import os
import re
import mysql.connector
from mysql.connector.errors import ProgrammingError, OperationalError

from ..classes import Anime, AnimeList, Character, NoneDict

from .base import BaseDB

class MySQL(BaseDB):

	THREAD_SAFE = True

	def __init__(self, settings) -> None:
		super().__init__()
		
		self.settings = settings
		if not {'host', 'user', 'password', 'database'} <= set(settings.keys()):
			# Missing some keys
			raise ValueError('Some keys are missing from configuration!')
  
		try:
			self.db = mysql.connector.connect(
				host=settings['host'],
				user=settings['user'],
				password=settings['password'],
				database=settings['database'],
				buffered=True
			)
		except ProgrammingError as e:
			if e.errno == 1045:
				# Wrong password
				raise Exception('Invalid database credentials')
			elif e.errno == 1049:
				# Database doesn't exist
    
				self.db = mysql.connector.connect(
					host=settings['host'],
					user=settings['user'],
					password=settings['password'],
					buffered=True
				)

				self.cur = self.db.cursor()
				self.createNewDb(settings['database'])
			else:
				raise

		self.cur = self.db.cursor()

	def createNewDb(self, database=None):
		""" Create a new database
		"""
		if database is not None:
			self.execute(f'CREATE DATABASE {database};')
			self.execute(f'USE {database};')

		cwd = os.path.dirname(os.path.abspath(__file__))
		with open(os.path.join(cwd, 'db_model.sql')) as f:
			for line in f.readlines():
				self.execute(line.strip())
			# Should save from within the script

	def execute(self, sql, *args, loops=0):
		""" Run the sql command directly
		"""
		pat = r'\?|:(\w+)'
		replace = lambda match: f'%({match.group(1)})s' if match.group(1) else '%s'
		formatted = re.sub(pat, replace, sql)
		try:
			out = super().execute(formatted, *args)
		except mysql.connector.errors.DatabaseError as e:
			if e.errno == 1205: # Lock wait timeout exceeded; try restarting transaction
				if loops < 5:
					return self.execute(sql, *args, loops=loops+1)
				else:
					if loops == 5:
						self.db.reconnect()
						return self.execute(sql, *args, loops=loops)
					else:
						raise
			elif e.errno == 4031: # The client was disconnected by the server because of inactivity. See wait_timeout and interactive_timeout for configuring this behavior.
				self.__init__(self.settings)
				return self.execute(sql, *args, loops=loops)
			elif e.errno == 1040: # Too many connections
				# Wrong server configuration, I'm not rlly sure what's the best thing to do here
				raise
			elif e.errno == 2055: # Cursor is not connected
				try:
					self.cur = self.db.cursor()
				except OperationalError:
					self.__init__(self.settings)

				return self.execute(sql, *args) # TODO - This *could* results in an endless loop
			else:
				raise
		else:
			return out

	def executemany(self, sql, *args):
		""" Run sql commands as a batch, should be faster than execute()
		"""
		pat = r'\?|:(\w+)'
		replace = lambda match: f'%({match.group(1)})s' if match.group(1) else '%s'
		formatted = re.sub(pat, replace, sql)
		try:
			return super().executemany(formatted, *args)
		except mysql.connector.errors.DatabaseError as e:
			raise

	def save(self):
		""" Save the current transaction
		"""
		self.db.commit()

	def keys(self, *args, **kwargs):
		pass

	@BaseDB.id_wrapper # type: ignore
	def exists(self, id, table):
		""" Check if an entity exists. Id can be either a single value, a list of values or a dict of key, value pairs.
		"""
		
		arg = ' AND '.join(map(lambda e: f'{e}=:{e}', id.keys()))
		sql = "SELECT EXISTS(SELECT 1 FROM " + table + f" WHERE {arg});"
		self.execute(sql, id)
		return bool(self.cur.fetchone()[0]) # type: ignore

	@BaseDB.id_wrapper(single_id=True) # type: ignore
	def get(self, id, table):
		""" Get the first row that match the id in table. Id can be either a single value, a list of values or a dict of key, value pairs.
		"""
		if not isinstance(id, dict):
			id = {'id': id}

		arg = ' AND '.join(map(lambda e: f'{e}=:{e}', id.keys()))
		sql = "SELECT * FROM " + table + f" WHERE {arg};"
		self.execute(sql, id)
		# TODO - Format output?
		data = self.cur.fetchone()
		
		if data is None or len(data) == 0:
			data = {}  # Not found

		desc = [e[0] for e in self.cur.description]

		if table == "anime":
			return self.get_all_metadata(Anime(keys=desc, values=data))
		elif table == "characters":
			return self.get_all_metadata(Character(keys=desc, values=data))
		else:
			return NoneDict(keys=desc, values=data)

	def getId(self, apiKey, apiId, table="anime"):
		if table == "anime":
			index = "indexList"
		elif table == "characters":
			index = "charactersIndex"

		apiId = int(apiId)

		sql = "SELECT id FROM {} WHERE {}=?;".format(index, apiKey)
		ids = self.sql(sql, (apiId,))
		if ids is not None and len(ids) > 0:
			# Already exists
			return ids[0][0]

		else:
			# Doesn't exists, create a new entry
			with self: # Get lock
				isql = "INSERT INTO {}({}) VALUES(?)".format(index, apiKey)
				try:
					self.execute(isql, (apiId,))
					
				except Exception as e:
					self.log("[ERROR] - On getId:", e)
					raise
				
				else:
					self.save()
					
				finally:
					ids = self.sql(sql, (apiId,))
					# if len(ids) == 0 or len(ids[0]) == 0:  #TODO
					if ids:
						return ids[0][0]
					else:
						raise Exception('Id wasn\'t inserted, wtf??')

	@BaseDB.id_wrapper # type: ignore
	def set(self, id, data, table):
		""" Either insert or update, depending on if id exists. Id can be either a single value, a list of values or a dict of key, value pairs.
		"""

		# Kinda messy, I would rather not reimplement this method
		raise NotImplementedError()


	def insert(self, data, table):
		""" Insert data in a table
		"""

		keys, values = [], []
		for k, v in data.items():
			if not isinstance(v, (dict, list)):
				# Isn't a metadata key
				keys.append(k)
				values.append(v)

		sql = "INSERT INTO " + table + "(" + ",".join(["{}"] * len(keys)) + ") VALUES(" + ",".join("?" * len(keys)) + ");"
		sql = sql.format(*keys)
		self.execute(sql, (*values,))

	@BaseDB.id_wrapper # type: ignore
	def update(self, id, data, table):
		""" Update data for the given id. Id can be either a single value, a list of values or a dict of key, value pairs.
		"""
		arg = ' AND '.join(map(lambda e: f'{e}=:{e}', id.keys()))
		sets = ', '.join(map(lambda e: f'{e} = :{e}', data.keys()))
		sql = "UPDATE " + table + f" SET {sets} WHERE {arg}"

		self.cur.execute(sql, (data | id, ))

	@BaseDB.id_wrapper # type: ignore
	def remove(self, id, table):
		""" Remove all row that match id from a table. 
			Id can be either a single value, a list of values or a dict of key, value pairs.
			Table can also be a list of string, to delete data from multiple tables at once
		"""
  
		if not isinstance(table, (list, tuple)):
			table = [table]

		arg = ' AND '.join(map(lambda e: f'{e}=:{e}', id.keys()))

		sql = ''
		for t in table:
			sql += f'DELETE FROM {t} WHERE {arg};\n'

		self.execute(sql, id)

	def filter(self, table=None, sort=None, range=(0, 50), order=None, filter=None):

		if table is None:
			table = 'anime'
		else:
			table = table


		if range is not None:
			limit = "\nLIMIT {start},{stop}".format(
				start=range[0],
				stop=range[1])
		else:
			limit = ""

		if filter is not None:
			filter = "\nWHERE {filter}".format(filter=filter)
		else:
			filter = ""

		if order is None:
			if sort is None:
				sort = "DESC"
			order = "anime.date_from"

		sql = """
			SELECT *
			FROM {table}
			{filter}
			ORDER BY {order}
			{sort} {limit};
		""".format(
			table=table,
			filter=filter,
			order=order,
			sort=sort,
			limit=limit)

		sql = re.sub(' +', ' ', sql.strip())
		with self.get_lock():
			# self.updateKeys("anime")
			# keys = list(self.tablekeys)

			self.execute(sql)
			data_list = self.cur.fetchall()
			keys = [e[0] for e in self.cur.description]

		return AnimeList([self.get_all_metadata(Anime(keys=keys, values=data)) for data in data_list])
		# return (Anime(keys=keys, values=data) for data in data_list)

	def get_metadata(self, id, key):
		""" Get metadata for a specific id and key. Should not return a generator.
		"""

		if not isinstance(id, dict):
			id = {'id': id}

		arg = ' AND '.join(map(lambda e: f'{e}=:{e}', id.keys()))
		data = self.sql(f"SELECT value FROM {key} WHERE {arg};", id)
		return [e[0] for e in data or []]

	def save_metadata(self, id, metadata):
		""" Save metadata for the given id.
		"""
		if not metadata:
			return

		c = 0
		for key, values in metadata.items():
			if not isinstance(values, (list, set, tuple)):
				raise TypeError("Values must be of type list, not", type(values))

			arg = ' AND '.join(map(lambda e: f'{e}=:{e}', id.keys()))
			db_values = [e[0] for e in self.sql(f"SELECT value FROM {key} WHERE {arg}", id) or []]
			toUpdate = []
			for v in values:
				if v:
					if v not in db_values:
						toUpdate.append((id, v))
					else:
						db_values.remove(v)

			# TODO - key is the table name??
			self.executemany(f"INSERT INTO {key}(id, value) VALUES (?,?)", toUpdate)
			self.executemany(f"DELETE FROM {key} WHERE id=? AND value=?", ((id, value) for value in db_values))
			c += len(toUpdate) + len(db_values)
		return c

