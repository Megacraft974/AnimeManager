import re
import time
from datetime import date

try:
	from .APIUtils import Anime, APIUtils, Character, EnhancedSession
except ImportError:
	# Local testing
	import os
	import sys
	sys.path.append(os.path.abspath('./'))
	from APIUtils import Anime, APIUtils, Character, EnhancedSession


class JikanMoeWrapper(APIUtils):
	def __init__(self, dbPath):
		super().__init__(dbPath)
		self.session = EnhancedSession(timeout=30)
		self.base_url = 'https://api.jikan.moe/v4'
		self.cooldown = 2
		self.last = time.time() - self.cooldown
		self.apiKey = "mal_id"

		self.mapped_external = {
			'AnimeDB': {
				'api_key': 'anidb_id',
				'regex': r".+aid=(\d+).*"
			}
		}

	def anime(self, id):
		mal_id = self.getId(id)
		if mal_id is None:
			return {}
		self.delay()
		a = self.get('/anime/{id}/full', id=mal_id)

		data = self._convertAnime(a['data'])
		return data

	def animeCharacters(self, id):
		mal_id = self.getId(id)
		if mal_id is None:
			return []
		self.delay()
		a = self.get('/anime/{id}/characters', id=mal_id)['data']
		for c in a:
			yield self._convertCharacter(c, id)

	def animePictures(self, id):
		self.delay()
		a = self.get("/anime/{id}/pictures", id=id)
		return a['pictures']

	def schedule(self, limit=50):
		# TODO - Limit + status
		self.delay()

		rep = self.get('/schedules')

		for anime in rep['data']:
			anime = self._convertAnime(anime)
			# anime['status'] = 'UPDATE'
			yield anime

		top = self.get('/top/anime')
		for anime in top['data']:
			anime = self._convertAnime(anime)
			# anime['status'] = 'UPDATE'
			yield anime

	def searchAnime(self, search, limit=50):
		self.delay()
		rep = self.get(f'/anime?q={search}&order_by=end_date&sort=desc')
		count = 0
		for a in rep['data']:
			data = self._convertAnime(a)
			if len(data) != 0:
				yield data
				count += 1
				if count >= limit:
					return

		for a in self.searchAnimeLetter(search[0], limit=limit-count):
			yield a

	def searchAnimeLetter(self, letter, limit=50):
		req = f'/anime?letter={letter}&order_by=end_date&sort=desc&page=''{page}'
		page = 1
		count = 0
		looping = True
		while looping:
			self.delay()
			rep = self.get(req.format(page=page))
			data = rep.get('data')
			if data:
				for a in data:
					data = self._convertAnime(a)
					if len(data) != 0:
						yield data
						count += 1
						if count >= limit:
							return
			if 'pagination' in rep and rep['pagination']['has_next_page']:
				page += 1
			else:
				looping = False

	def character(self, id):
		mal_id = self.getId(id, table="characters")
		self.delay()
		c = self.get('/characters/{id}', id=mal_id)
		return self._convertCharacter(c)

	def _convertAnime(self, a):
		id = self.database.getId("mal_id", int(a["mal_id"]))
		out = Anime()

		out["id"] = id
		out['title'] = a['title']
		if a['title'][-1] == ".":
			out['title'] = a['title'][:-1]

		keys = ['title', 'title_english', 'title_japanese']
		titles = []
		for key in keys:
			if key in a.keys() and a[key] is not None:
				titles.append(a[key])
		if 'title_synonyms' in a.keys():
			titles += a['title_synonyms']

		out['title_synonyms'] = titles

		if 'aired' in a.keys():
			datefrom, dateto = a['aired']['prop'].values()
		else:
			datefrom, dateto = {1: None}, {1: None}
		out['date_from'] = str(
			date(
				datefrom['year'],
				datefrom['month'],
				datefrom['day'])) if None not in datefrom.values() else None
		out['date_to'] = str(
			date(
				dateto['year'],
				dateto['month'],
				dateto['day'])) if None not in dateto.values() else None

		out['picture'] = a['images']['jpg']['image_url']

		pictures = []

		sizes = {'image_url': 'medium', 'small_image_url': 'small',
				 'large_image_url': 'large'}
		pictures = []
		# for type, imgs in a['images'].items():
		for size, url in a['images']['jpg'].items(): # Ignoring webp images
			size_lbl = sizes[size]
			img = {
				'url': url,
				'size': size_lbl
			}
			pictures.append(img)

		self.save_pictures(id, pictures)

		out['synopsis'] = a['synopsis'] if 'synopsis' in a.keys() else None
		out['episodes'] = a['episodes'] if 'episodes' in a.keys() else None
		duration = a['duration'].split(
			" ")[0] if 'duration' in a.keys() else None
		out['duration'] = int(
			duration) if duration and duration != 'Unknown' else None
		out['status'] = None  # a['status'] if 'status' in a.keys() else None
		out['rating'] = (
			a['rating'].split("-")[0].rstrip()
			if 'rating' in a.keys() and a['rating'] else None
		)
		if 'broadcast' in a.keys() and a['broadcast']['day'] is not None:
			weekdays = ('Mondays', 'Tuesdays', 'Wednesdays',
						'Thursdays', 'Fridays', 'Saturdays', 'Sundays')
			if a['broadcast']['day'] not in weekdays:
				raise ValueError(a['broadcast']['day'] +
								 " is not in weekdays!")
			out['broadcast'] = "{}-{}-{}".format(weekdays.index(
				a['broadcast']['day']), *a['broadcast']['time'].split(":"))

		# out['broadcast'] = a['broadcast']['day'] + '-' +  if 'broadcast' in a.keys() else None
		out['trailer'] = a['trailer_url'] if 'trailer_url' in a.keys() else None

		if out['date_from'] is None:
			out['status'] = 'UPDATE'
			return {}
		else:
			out['status'] = self.getStatus(
				out) if 'status' in a.keys() else None

		if 'genres' in a.keys():
			genres = self.getGenres(
				[
					dict([
						('id', g['mal_id']),
						('name', g['name'])
					])
					for g in a['genres']
				]
			)
		else:
			genres = []
		out['genres'] = genres

		if 'relations' in a.keys():
			rels = []
			for relation in a['relations']:
				rel_type = relation['relation']
				entries = relation['entry']
				for entry in entries:
					rel = {
						'type': entry['type'],
						'name': relation['relation'],
						'rel_id': int(entry["mal_id"]),
						'anime': {'title': entry['name']}
					}
					rels.append(rel)
			if len(rels) > 0:
				self.save_relations(id, rels)

		if 'external' in a.keys():
			mapped = []
			for external in a['external']:
				if external['name'] in self.mapped_external:
					ext_data = self.mapped_external[external['name']]
					match = re.match(ext_data['regex'], external['url'])
					if match:
						mapped.append({
							'api_key': ext_data['api_key'],
							'api_id': match.group(1)
						})
			
			self.save_mapped('mal_id', int(a["mal_id"]), mapped)

		return out

	def _convertCharacter(self, c, anime_id=None):
		c_id = self.database.getId(
			"mal_id", int(c["mal_id"]), table="characters")
		keys = {'name': 'name', 'role': 'role', 'picture': 'image_url',
				'desc': 'about', 'animeography': 'animeography'}
		out = Character()
		out.id = c_id
		if anime_id is not None:
			out.anime_id = anime_id
		for db_key, data_key in keys.items():
			if data_key in c.keys() and c[data_key] is not None:
				out[db_key] = c[data_key]
		if 'role' in out.keys():
			out.role = out.role.lower()
		return out

	def get(self, endpoint, **kwargs):
		if kwargs:
			endpoint = endpoint.format(**kwargs)
		url = self.base_url + endpoint
		try:
			r = self.session.request('GET', url)
		except Exception as e:
			self.log("API_WRAPPER", "[Jikan.moe] - Error: ", e)
			return {}
		else:
			return r.json()

	def delay(self):
		if time.time() - self.last < self.cooldown:
			time.sleep(max(self.cooldown - (time.time() - self.last), 0))
		self.last = time.time()


if __name__ == "__main__":
	import os
	appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
	dbPath = os.path.join(appdata, "animeData.db")
	api = JikanMoeWrapper(dbPath)
	out = api.anime(2)
	pass
