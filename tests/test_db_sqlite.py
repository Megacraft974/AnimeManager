
import unittest
import sys, os

from db_global_tests import DbGlobalTests

sys.path.append(os.path.abspath("../"))

from AnimeManager import Manager # type: ignore

class TestDbSQLite(unittest.TestCase, DbGlobalTests):
	def setUp(self):
		self.manager = Manager(remote=True)
		self.db = self.manager.getDatabase()


if __name__ == '__main__':
	unittest.main()