import random
import string
import time
import traceback
from types import NoneType

import sys, os

sys.path.append(os.path.abspath("../"))

from AnimeManager.animeAPI import AnimeAPI # type: ignore
from AnimeManager.classes import Anime, NoIdFound # type: ignore


class ApiTester():
	def __init__(self, api_instance):

		self.DELAY = 5

		self.SEARCH_SIZE = 1
		self.SEARCH_LENGTH = 5

		if isinstance(api_instance, type):
			self.api = api_instance()
		else:
			self.api = api_instance

	def test_all(self):
		self.test_anime()
		self.test_search()
		self.test_schedule()

	def check_anime(self, anime):
		assert isinstance(anime, (NoneType, Anime)), 'Not an instance of Anime!'
		if anime is None:
			return
		assert anime.id is not None, 'Anime id is None!'
		# print(anime.id, anime.title)

	def check_endpoint(self, endpoint):
		if not hasattr(self.api, endpoint):
			print(f'Endpoint "{endpoint}": ERROR - Not implemented')
			return False
		return True

	def test_anime(self):
		if not self.check_endpoint('anime'):
			return

		search_size = 1

		# print('\n-- Fetch anime by id --')

		db = self.api.database
		with db.get_lock():
			sql = f'SELECT id FROM indexList WHERE {self.api.apiKey} IS NOT null'
			ids = db.sql(sql)
		
		ids = [row[0] for row in ids]

		animeIds = random.choices(ids, k=search_size)
		times = []

		ok = True
		while animeIds:
			a_id = animeIds.pop(0)
			start = time.time()
			try:
				anime = self.api.anime(a_id)
				self.check_anime(anime)

			except NoIdFound:
				animeIds.append(ids.pop(0))

			except Exception as e:
				print(f'Endpoint "anime": ERROR - {e}')
				ok = False
				traceback.print_exc()
				break

			else:
				times.append(time.time() - start)
				time.sleep(self.DELAY)

		if ok:
			print(f'Endpoint "anime": OK - {sum(times) / len(times):.2f}s / {max(times):.2f}s')

	def test_search(self, terms=None):
		if not self.check_endpoint('searchAnime'):
			return

		# print('\n-- Fetch anime by title (search) --')

		if terms is None:
			chars = string.ascii_lowercase + ' '
			searchTerms = [''.join(random.choices(chars, k=random.randint(3, self.SEARCH_LENGTH))) for i in range(self.SEARCH_SIZE)]
		else:
			searchTerms = terms

		start = time.time()
		counter_tot = 0
		toggle = False
		ok = True
		for terms in searchTerms:
			if toggle:
				time.sleep(self.DELAY)
				start -= self.DELAY
			else:
				toggle = True

			try:
				counter = 0
				for anime in self.api.searchAnime(terms):
					self.check_anime(anime)
					counter += 1
					if counter > 50:
						break
			except Exception as e:
				print(f'Endpoint "search": ERROR - {e}')
				ok = False
				traceback.print_exc()
				pass
			else:
				counter_tot += counter
				if ok and counter == 0:
					print(f'Endpoint "search": ERROR - No anime returned for "{terms}"')
					ok = False
					break

		took = time.time() - start
		if ok and counter_tot > 0:
			print(f'Endpoint "search": OK - {counter} animes / {took:.2f}s')

	def test_schedule(self):
		if not self.check_endpoint('schedule'):
			return

		start = time.time()
		counter = 0
		ok = True
		try:
			for anime in self.api.schedule():
				self.check_anime(anime)
				counter += 1
				if counter > 50:
					break
		except Exception as e:
			print(f'Endpoint "schedule": ERROR - {e}')
			ok = False
			traceback.print_exc()
			pass
		else:
			if ok and counter == 0:
				print(f'Endpoint "schedule": ERROR - No anime returned')
				ok = False

		took = time.time() - start
		if ok and counter > 0:
			print(f'Endpoint "schedule": OK - {counter} animes / {took:.2f}s')


if __name__ == "__main__":
	a = AnimeAPI()
	a.init_thread.join()
	for api in a.apis:
		print(f'\n-- Testing {api.__name__} --')
		t = ApiTester(api)
		t.test_all()