
import unittest
import sys, os

sys.path.append(os.path.abspath("../"))

from AnimeManager import Manager # type: ignore

class TestDbSQLite(unittest.TestCase):
	def setUp(self):
		self.manager = Manager(remote=True)
		self.db = self.manager.getDatabase()

	def test_tables(self):
		tables = ["anime", "animeRelations", "broadcasts", "characters", "charactersIndex", "characterRelations", "genres", "genresIndex", "indexList", "pictures", "title_synonyms", "torrents", "torrentsIndex"]
		with self.db:
			for table in tables:
				try:
					data = self.db.sql(f"SELECT * FROM {table} LIMIT 1")
				except Exception as e:
					self.fail(f"Error while trying to access table {table}: {e}")
				else:
					self.assertIsNotNone(data, f"Table {table} seems to be empty")


if __name__ == '__main__':
	unittest.main()