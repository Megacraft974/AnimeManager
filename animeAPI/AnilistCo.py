from datetime import date, datetime
import re
import requests

from .APIUtils import Anime, APIUtils, Character, EnhancedSession


class QueryObject:
	def __init__(self, name, args=None, fields=None) -> None:
		self.name = name
		self.args = args or []  # [(name, ?type, ?value)]
		self.fields = set(fields or [])

	def __str__(self):
		return self.build()

	def set_arg(self, arg):
		for i, sub_arg in enumerate(self.args):
			if sub_arg[0] == arg[0]:
				# Same name
				self.args[i] = arg
				break
		else:
			self.args.append(arg)

	def add_field(self, field):
		self.fields.add(field)
		return self

	def del_field(self, field):
		if field in self.fields:
			self.fields.remove(field)
		return self

	def build(self):
		args = []
		for arg, arg_type, *value in self.args:
			text = f'{arg}: {arg_type}'
			if value:
				value = value[0]
				if isinstance(value, str):
					value = f'"{value}"'
				text += f' = {value}'
			args.append(text)

		text = [self.name]

		if args:
			text.append(f'({", ".join(args)})')

		if self.fields:
			text.append('{')

			for field in self.fields:
				text.append(str(field))

			text.append('}')

		return ' '.join(text)


class AnilistCoWrapper(APIUtils):
	def __init__(self):
		super().__init__()
		self.session = EnhancedSession(timeout=30)
		self.url = 'https://graphql.anilist.co'
		self.apiKey = "anilist_id"

		self.media_fields = [
			'id',
			'idMal',
			QueryObject(
				'title',
				fields=[
					'romaji',
					'english',
					'native',
				]
			),
			QueryObject(
				'status',
				args=(
					('version', 2),
				)
			),
			QueryObject(
				'description',
				args=(
					('asHtml', 'false'),
				)
			),
			QueryObject(
				'startDate',
				fields=[
					'year',
					'month',
					'day',
				]
			),
			QueryObject(
				'endDate',
				fields=[
					'year',
					'month',
					'day',
				]
			),
			'episodes',
			'duration',
			QueryObject(
				'trailer',
				fields=[
					'site',
				]
			),
			QueryObject(
				'coverImage',
				fields=[
					'extraLarge',
					'large',
					'medium',
				]
			),
			'genres',
			'synonyms',
			QueryObject(
				'tags',
				fields=[
					'id',
					'name',
					'description',
					'isAdult',
				]
			),
			QueryObject(
				'relations',
				fields=[
					QueryObject(
						'edges',
						fields=[
							'relationType',
							QueryObject(
								'node',
								fields=[
									'id',
									QueryObject(
										'title',
										fields=[
											'english',
										]
									),
									'type',
								]
							),
						]
					),
				]
			),
			QueryObject(
				'characters',
				fields=[
					QueryObject(
						'edges',
						fields=[
							'role',
							QueryObject(
								'node',
								fields=[
									'id',
									QueryObject(
										'name',
										fields=[
											'full',
										]
									),
									QueryObject(
										'image',
										fields=[
											'large',
											'medium',
										]
									),
									'description',
								]
							),
						]
					),
				]
			),
			'isAdult',
			QueryObject(
				'nextAiringEpisode',
				fields=[
					'airingAt',
				]
			)
		]

		self.media_query = QueryObject(
			'Media',
			args=(
				('id', '$id'),
				('type', 'ANIME'),
			),
			fields=self.media_fields
		)

		self.pagination_query = QueryObject(
			# query ($id: Int, $page: Int, $perPage: Int, $search: String) {
			'Page',
			args=(
				('page', '$page'),
				('perPage', '$perPage'),
			),
			fields=[
				QueryObject(
					'pageInfo',
					fields=[
						'total',
						'currentPage',
						'lastPage',
						'hasNextPage',
						'perPage'
					]
				)
			]
		)

	def anime(self, id):
		ani_id = self.getId(id)
		if ani_id is None:
			return None

		query = QueryObject(
			'query',
			args=(
				('$id', 'Int'),
			),
			fields=[
				self.media_query
			]
		)

		variables = {
			'id': ani_id
		}
		rep = requests.post(
			self.url, json={'query': str(query), 'variables': variables})
		data = rep.json().get('data')

		if not data:
			return None

		anime = self._convertAnime(data.get('Media'))
		return anime

	def searchAnime(self, search, limit=50):
		query = QueryObject(
			'query',
			args=(
				('$id', 'Int'),
				('$page', 'Int'),
				('$perPage', 'Int'),
				('$search', 'String')
			),
			fields=[
				self.pagination_query.add_field(
					QueryObject(
						'media',
						args=(
							('id', '$id'),
							('search', '$search'),
						),
						fields=self.media_fields
					)
				)
			]
		)

		variables = {
			'search': search,
			'page': 1,
			'perPage': 50
		}
		
		count = 0
		for a in self.iterate(query, variables):
			data = self._convertAnime(a)
			if data and len(data) != 0:
				yield data
				count += 1
				if count >= limit:
					return
			

	def _convertAnime(self, a):
		if a is None:
			return
		id = self.database.getId(self.apiKey, a.get('id'))
		out = Anime()

		out.id = id

		keys = ['english', 'romaji', 'native']
		titles = []
		for key in keys:
			title = a.get('title').get(key)
			if title:
				titles.append(title)

		titles += a.get('synonyms', [])

		# Every anime should have at least one title
		out.title = titles[0].rstrip('.')
		# rstrip() is a fix for a problem where files would get corrupted

		out.title_synonyms = titles

		mapped_status = {
			'FINISHED': 'FINISHED',
			'RELEASING': 'AIRING',
			'NOT_YET_RELEASED': 'UPCOMING',
			'CANCELLED': 'UNKNOWN',
			'HIATUS': 'UPCOMING'
		}
		out.status = mapped_status.get(a.get('status'))

		desc = a.get('description')
		if desc: # Avoid using regex when it isn't necessary
			out.synopsis = re.sub('<.*?>', '', desc) # Remove all HTML tags
		else:
			out.synopsis = None

		epoch = datetime(1970, 1, 1)
		datefrom = a.get('startDate')
		if None not in datefrom.values():
			out.date_from = int((datetime(**datefrom)-epoch).total_seconds())
		else:
			out.date_from = None

		dateto = a.get('endDate')

		if None not in dateto.values():
			out.date_to = int((datetime(**dateto)-epoch).total_seconds())
		else:
			out.date_to = None

		out.episodes = a.get('episodes')
		out.duration = a.get('duration')
		out.trailer = (a.get('trailer') or {}).get('site')
		out.rating = 'R' if a.get('isAdult') else ''

		out.picture = a.get('coverImage', {}).get('medium')

		pictures = []

		sizes = {'large': 'medium', 'medium': 'small',
				 'extraLarge': 'large'}
		pictures = []
		for key, size in sizes.items():
			url = a.get('coverImage', {}).get(key)
			if url:
				img = {
					'url': url,
					'size': size
				}
				pictures.append(img)

		self.save_pictures(id, pictures)

		broadcast = (a.get('nextAiringEpisode') or {}).get('airingAt')
		if broadcast:
			broadcast = datetime.fromtimestamp(broadcast)
			data = (
				broadcast.isoweekday() - 1,
				broadcast.hour,
				broadcast.minute)

			self.save_broadcast(id, *data)

			# TODO - Should be removed
			out.broadcast = "{}-{}-{}".format(*data)

		out.status = self.getStatus(out)

		out.genres = self.getGenres(
			[
				{
					'id': None,
					'name': g
				}
				for g in a.get('genres', [])
			]
		)

		# Relations
		rels = []
		for edge in a.get('relations', {}).get('edges', []):
			node = edge.get('node', {})

			rel = {
				'type': node.get('type').lower(),
				'name': edge.get('relationType'),
				'rel_id': int(node.get('id')),
				'anime': {
					'title': node.get('title', {}).get('english')
				}
			}
			rels.append(rel)

		if len(rels) > 0:
			self.save_relations(id, rels)

		# Mapped animes
		mal_id = a.get('mal_id')
		if mal_id:
			mapped = [{
				'api_key': 'mal_id',
				'api_id': mal_id
			}]

			self.save_mapped(a.get('id'), mapped)

		# Characters
		for edge in a.get('characters').get('edges'):
			c = edge.get('node')
			c['role'] = edge.get('role')

			self._convertCharacter(c)

		return out

	def _convertCharacter(self, c, anime_id=None):
		# TODO - merge function

		id = self.database.getId(self.apiKey, c.get('id'), table="characters")
		out = Character()
		out.id = id
		out.name = c.get('name', {}).get('full')
		out.desc = c.get('description')

		image = c.get('image', {})
		out.picture = image.get('large') or image.get('medium')

		if anime_id is not None:
			anime_data = {anime_id: c.get('role').lower()}
			self.save_animeography(id, anime_data)

		return out

	def iterate(self, query, variables):
		page = 1
		while True:
			variables['page'] = page
			rep = requests.post(
				self.url, json={'query': str(query), 'variables': variables}).json()		
			if rep.get('errors', None):
				self.log(f'[ERROR] - On AnilistCo: {rep["errors"]}')
			data = rep.get('data')
			if not data:
				return

			page = data.get('Page', {})
			if page is not None:
				for m in page.get('media', []):
					yield m
     
				pageInfo = page.get('pageInfo', {})
				if not pageInfo.get('hasNextPage'):
					return
				page = pageInfo.get('currentPage', page) + 1

			else:
				pass
			
			

if __name__ == '__main__':

	from APIUtils import ApiTester
	t = ApiTester(AnilistCoWrapper)

	t.test_search(['dungeon'])
