import random
import time
import unittest
import sys, os

sys.path.append(os.path.abspath("../"))

from AnimeManager import Manager, Anime # type: ignore

class TestSearch(unittest.TestCase):
	def setUp(self):
		self.manager = Manager(remote=True)

	def getStatus_tc(self):
		keys = ['date_from', 'date_to', 'episodes']
		tests = [
			((1554508800, 1569628800, 12), 'FINISHED'),
			((1630800000, None, 1), 'FINISHED'),
			((1630800000, None, 12), 'AIRING'),
			((1830332800, None, 12), 'UPCOMING'),
		]

		statuses = ['UNKNOWN', 'UPCOMING', 'FINISHED', 'UPDATE', 'AIRING']
		for a, out in tests:
			anime = Anime(dict(zip(keys, a)))
			for status in statuses:
				anime.status = status
				if status == "UPDATE":
					yield anime, "UNKNOWN"
				else:
					yield anime, status

			anime.status = None
			yield anime, out

			anime.date_from = None
			yield anime, "UNKNOWN"

	def test_getStatus(self):
		for anime, out in self.getStatus_tc():
			self.assertEqual(self.manager.getStatus(anime), out)

	def getDateText_tc(self):
		for anime, out in self.getStatus_tc():
			yield anime

			w, h, m = random.randint(0, 7), random.randint(0, 23), random.randint(0, 59)
			anime.broadcast = f"{w}-{h}-{m}"

			yield anime

	def test_getDateText(self):
		for anime in self.getDateText_tc():
			try:
				out = self.manager.getDateText(anime)
				print(out)
			except Exception as e:
				self.fail(f"Error: {e}", anime)

if __name__ == '__main__':
	unittest.main(verbosity=2)
	pass