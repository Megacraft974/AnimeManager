from ast import Import


try:
    from .APIUtils import APIUtils, EnhancedSession, Anime, Character
except ImportError:
    # Local testing
    import sys, os
    sys.path.append(os.path.abspath('./'))
    from APIUtils import APIUtils, EnhancedSession, Anime, Character
from datetime import date
import time


class JikanMoeWrapper(APIUtils):
    def __init__(self, dbPath):
        super().__init__(dbPath)
        self.session = EnhancedSession(timeout=30)
        self.base_url = 'https://api.jikan.moe/v4'
        self.cooldown = 2
        self.last = time.time() - self.cooldown
        self.apiKey = "mal_id"

    def anime(self, id):
        mal_id = self.getId(id)
        if mal_id is None:
            return {}
        self.delay()
        a = self.get('/anime/{id}', id=mal_id)
        
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
        rep = self.get(f'/anime?q={search}')
        for a in rep['data']:
            data = self._convertAnime(a)
            if len(data) != 0:
                yield data

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

        sizes = {'image_url': (225, 328), 'small_image_url': (50, 75), 'large_image_url': (350, 525)}
        out['pictures'] = []
        for type, imgs in a['images'].items():
            for size, url in imgs.items():
                w, h = sizes[size]
                img = {
                    'url': url,
                    'width': w,
                    'height': h,
                    'type': type
                }
                out['pictures'].append(img)
        print(a['images'])

        out['synopsis'] = a['synopsis'] if 'synopsis' in a.keys() else None
        out['episodes'] = a['episodes'] if 'episodes' in a.keys() else None
        duration = a['duration'].split(" ")[0] if 'duration' in a.keys() else None
        out['duration'] = int(duration) if duration and duration != 'Unknown' else None
        out['status'] = None  # a['status'] if 'status' in a.keys() else None
        out['rating'] = a['rating'].split(
            "-")[0].rstrip() if 'rating' in a.keys() else None
        if 'broadcast' in a.keys() and a['broadcast']['day'] is not None:
            weekdays = ('Mondays', 'Tuesdays', 'Wednesdays',
                        'Thursdays', 'Fridays', 'Saturdays', 'Sundays')
            if a['broadcast']['day'] not in weekdays:
                raise ValueError(a['broadcast']['day'] + " is not in weekdays!")
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

        if 'related' in a.keys():
            rels = []
            for relation, rel_data_list in a['related'].items():
                for rel_data in rel_data_list:
                    rel = {'type': rel_data['type'], 'name': relation, 'rel_id': int(rel_data["mal_id"]), 'anime': {'title': rel_data['name']}}
                    rels.append(rel)
            if len(rels) > 0:
                self.save_relations(id, rels)
        return out

    def _convertCharacter(self, c, anime_id=None):
        c_id = self.database.getId("mal_id", int(c["mal_id"]), table="characters")
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
        endpoint = endpoint.format(**kwargs)
        url = self.base_url + endpoint
        try:
            r = self.session.request('GET', url)
        except Exception as e:
            print("API_WRAPPER", "[Jikan.moe] - Error: ", e)
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
    print(api.anime(5))