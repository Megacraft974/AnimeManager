import time
import unittest
import sys, os

sys.path.append(os.path.abspath("../"))

from AnimeManager import Manager # type: ignore

class TestSearch(unittest.TestCase):
	def setUp(self):
		self.manager = Manager(remote=True)

	@unittest.skip("Too many problems lol")
	def test_search_online_sync(self):
		start = time.time()
		times = []

		terms = ""
		limit = 10
		search = self.manager.api.searchAnime(terms, limit=limit)

		for anime in search:
			stop = time.time()
			times.append(stop - start)

			limit -= 1
			if limit == 0: break

			start = stop

		self.assertLess(times[0], 5) # First search include connection time etc

		self.assertLess(max(times[1:]), 2)

	def test_search_single(self):
		terms = "Naruto"
		limit = 10
		if self.manager.api.init_thread is not None:
			self.manager.api.init_thread.join()

		for api in self.manager.api.apis:
			search = api.searchAnime(terms, limit=limit)
			start = time.time()
			times = []
			for anime in search:
				if anime['id'] is None: continue
				stop = time.time()
				times.append(stop - start)
				start = stop

			self.assertLess(times[0], 5) # First search include connection time etc

			self.assertLess(max(times[1:]), 2)



if __name__ == '__main__':
	unittest.main(verbosity=2)
	pass