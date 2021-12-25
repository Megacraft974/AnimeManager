from APIUtils import APIUtils, EnhancedSession, Anime, Character, log
from jikanpy import Jikan, exceptions as jikan_exceptions
from datetime import date
import json
import time
import requests


class JikanMoeWrapper(APIUtils):
    def __init__(self, dbPath):
        super().__init__(dbPath)
        self.session = EnhancedSession(timeout=30)
        self.jikan = Jikan(session=self.session)
        self.cooldown = 2
        self.last = time.time() - self.cooldown
        self.apiKey = "mal_id"
        # self.online = True

    def anime(self, id):
        mal_id = self.getId(id)
        if mal_id is None:
            return {}
        self.delay()
        a = self.jikan.anime(mal_id)
        data = self._convertAnime(a)
        return data

    def animeCharacters(self, id):
        mal_id = self.getId(id)
        if mal_id is None:
            return []
        self.delay()
        try:
            a = self.jikan.anime(mal_id, extension='characters_staff')[
                'characters']
        except requests.exceptions.ReadTimeout:
            pass
        for c in a:
            yield self._convertCharacter(c, id)

    def animePictures(self, id):
        self.delay()
        try:
            a = self.jikan.anime(id, "pictures")
        except jikan_exceptions.APIException:
            return []
        return a['pictures']

    def schedule(self, limit=50):
        # TODO - Limit + status
        self.delay()
        rep = self.jikan.schedule()
        for day, data in list(rep.items())[3:12]:
            break
            for anime in data:
                anime = self._convertAnime(anime)
                anime['status'] = 'UPDATE'
                yield anime

        top = self.jikan.top(type="anime", page=1, subtype="airing")
        for anime in top['top']:
            break
            anime = self._convertAnime(anime)
            anime['status'] = 'UPDATE'
            yield anime

    def searchAnime(self, search, limit=50):
        self.delay()
        try:
            rep = self.jikan.search('anime', search, parameters={'limit': limit})
        except requests.exceptions.ReadTimeout:
            log("Jikan.moe timed out!")
            return
        except jikan_exceptions.APIException:
            log("Jikan.moe had a parser exception!")
            return
        for a in rep['results']:
            data = self._convertAnime(a)
            if len(data) != 0:
                yield data

    def character(self, id):
        mal_id = self.getId(id, table="characters")
        self.delay()
        c = self.jikan.character(mal_id)
        return self._convertCharacter(c)

    def _convertAnime(self, a):
        id = self.database.getId("mal_id", int(a["mal_id"]))
        out = Anime()

        out["id"] = id
        # out["mal_id"] = a["mal_id"]
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

        if len(titles) >= 1:
            out['title_synonyms'] = json.dumps(titles)
        else:
            out['title_synonyms'] = None

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

        out['picture'] = a['image_url']
        out['synopsis'] = a['synopsis'] if 'synopsis' in a.keys() else None
        out['episodes'] = a['episodes'] if 'episodes' in a.keys() else None
        out['duration'] = a['duration'].split(
            " ")[0] if 'duration' in a.keys() else None
        out['status'] = None  # a['status'] if 'status' in a.keys() else None
        out['rating'] = a['rating'].split(
            "-")[0].rstrip() if 'rating' in a.keys() else None
        if 'broadcast' in a.keys() and a['broadcast'] not in (None, 'Unknown'):
            weekdays = ('Mondays', 'Tuesdays', 'Wednesdays',
                        'Thursdays', 'Fridays', 'Saturdays', 'Sundays')
            a['broadcast'] = a['broadcast'].split(" (")[0].split(' at ')
            if a['broadcast'][0] not in weekdays:
                raise ValueError(a['broadcast'][0] + " is not in weekdays!")
            out['broadcast'] = "{}-{}-{}".format(weekdays.index(
                a['broadcast'][0]), *a['broadcast'][1].split(":"))

        # out['broadcast'] = a['broadcast'] if 'broadcast' in a.keys() else None
        out['trailer'] = a['trailer_url'] if 'trailer_url' in a.keys() else None

        if out['date_from'] is None:
            out['status'] = 'UPDATE'
            return {}
        else:
            out['status'] = self.getStatus(
                out) if 'status' in a.keys() else None

        genres = []
        if 'genres' in a.keys():
            for g in a['genres']:
                if not self.database.exist(g['mal_id'], "genres", "mal_id"):
                    self.database.sql(
                        "INSERT INTO genres(mal_id,name) VALUES(?,?)", (g['mal_id'], g['name']))

                # TODO - Multi-querying?
                genres.append(
                    self.database.sql(
                        "SELECT id FROM genres WHERE mal_id=?",
                        (g['mal_id'],
                         ))[0][0])
        out['genres'] = json.dumps(genres)

        if 'related' in a.keys():
            for relation, rel_data_list in a['related'].items():
                for rel_data in rel_data_list:
                    if rel_data['type'] == "anime":
                        rel_id = self.database.getId("mal_id", rel_data["mal_id"])
                        if not self.database.sql(
                                "SELECT EXISTS(SELECT 1 FROM related WHERE id=? AND rel_id=?);", (id, rel_id)):
                            rel = {"id": id, "relation": relation,
                                   "rel_id": rel_id}
                            self.database.set(rel, table="related", save=False)
        self.database.save()

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

    def delay(self):
        if time.time() - self.last < self.cooldown:
            time.sleep(max(self.cooldown - (time.time() - self.last), 0))
        self.last = time.time()
