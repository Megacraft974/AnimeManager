
import unittest
import sys, os

from db_global_tests import DbGlobalTests

sys.path.append(os.path.abspath("../"))

from AnimeManager import Manager # type: ignore

class TestDbMySQL(unittest.TestCase, DbGlobalTests):
	def setUp(self):
		self.manager = Manager(remote=True)
		self.db = self.manager.getDatabase()

	@unittest.skip("Not implemented yet")
	def test_procedures(self):
		tests = [
			('get_torrent_data', )
		]
		with self.db:
			for name, *args in tests:
				args, out = self.db.procedure(name, *args)
				out = list(out)
				self.assertGreater(len(out), 0, f"Procedure {name} returned an empty result")

if __name__ == '__main__':
	unittest.main()