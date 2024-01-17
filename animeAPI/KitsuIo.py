from datetime import datetime
from jsonapi_client import Filter, Inclusion, Modifier, Session, relationships, exceptions

try:
    from .APIUtils import Anime, APIUtils, Character
except ImportError:
    # Local testing
    import os
    import sys
    sys.path.append(os.path.abspath('./'))
    from APIUtils import Anime, APIUtils, Character


class KitsuIoWrapper(APIUtils):
    def __init__(self, dbPath):
        APIUtils.__init__(self, dbPath)
        # TODO - self.s.close() ??
        self.s = Session('https://kitsu.io/api/edge/')
        self.apiKey = "kitsu_id"
        self.mappedSites = {"myanimelist/anime": "mal_id",
                            "anidb": "anidb_id", "anilist/anime": "anilist_id"}
        self.subtypes = ('TV', 'movie')

    def anime(self, id):
        kitsu_id = self.getId(id)
        if kitsu_id is None:
            return {}
        modifier = Inclusion("genres", "mediaRelationships",
                             "mediaRelationships.destination", "mappings")
        rep = self.s.get('anime/' + str(kitsu_id), modifier).resource
        data = self._convertAnime(rep, force=True)
        return data

    def animeCharacters(self, id):
        kitsu_id = self.getId(id)
        if kitsu_id is None:
            return []
        modifier = Inclusion("character")
        characters = self.s.iterate(
            'anime/{}/characters'.format(str(kitsu_id)), modifier)
        for c in characters:
            yield self._convertCharacter(c, id)
            
    def animePictures(self, id):
        modifier = Filter(id=id)
        rep = self.s.get('anime', modifier).resources
        if len(rep) >= 1:
            a = [rep[0].posterImage]
        else:
            a = []
        return a

    def season(self, year, season):
        modifier = Filter(seasonYear=year,
                          season=season) + Inclusion("genres",
                                                     "mediaRelationships",
                                                     "mediaRelationships.destination")
        for a in self.s.iterate('anime', modifier):
            data = self._convertAnime(a)
            if data is None:
                continue
            yield data

    def schedule(self, limit=50):
        def getSchedule():
            modifier = Inclusion(
                "genres", "mediaRelationships", "mediaRelationships.destination", "mappings"
            ) + Modifier(
                "page[limit]=20"
            )
            trending = self.s.iterate('trending/anime', modifier)

            for a in trending:
                yield a

            modifier += Modifier("sort=-startDate,-endDate")

            r_modifier = modifier + Filter(status="current")
            recent = self.s.iterate('anime', r_modifier)

            u_modifier = modifier + Filter(status="upcoming")
            upcoming = self.s.iterate('anime', u_modifier)
            
            try:
                r_anime = next(recent, None)
            except exceptions.DocumentError as e:
                r_anime = None
                if e.errors['status_code'] == 500:
                    # Internal server error
                    # Happens while using filter, might be fixed one day?
                    pass
                else:
                    raise
            
            try:
                u_anime = next(upcoming, None)
            except exceptions.DocumentError as e:
                u_anime = None
                if e.errors['status_code'] == 500:
                    # Internal server error
                    # Happens while using filter, might be fixed one day?
                    pass
                else:
                    raise

            while r_anime is not None or u_anime is not None:
                if r_anime is not None:
                    yield r_anime
                    
                    try:
                        r_anime = next(recent, None)
                    except exceptions.DocumentError as e:
                        if e.errors['status_code'] == 500:
                            # Internal server error
                            # Happens while using filter, might be fixed one day?
                            pass
                        else:
                            raise

                if u_anime is not None:
                    yield u_anime
                    
                    try:
                        u_anime = next(upcoming, None)
                    except exceptions.DocumentError as e:
                        if e.errors['status_code'] == 500:
                            # Internal server error
                            # Happens while using filter, might be fixed one day?
                            pass
                        else:
                            raise

        schedule = getSchedule()

        for c, a in enumerate(schedule):
            data = self._convertAnime(a)
            if data is None:
                continue

            yield data
            if c >= limit:
                break

    def searchAnime(self, search, limit=50):
        modifier = (
            Filter(text=search) +
            Inclusion("genres", "mediaRelationships",
                      "mediaRelationships.destination")
            # Modifier("sort=-endDate") doesn't work for some reasons
        )
        c = 1
        for a in self.s.iterate('anime', modifier):
            data = self._convertAnime(a)
            if data is None:
                continue
            yield data
            c += 1
            if c >= limit:
                break

    def character(self, id):
        kitsu_id = self.getId(id, "characters")
        if kitsu_id is None:
            return {}
        modifier = Filter(id=kitsu_id) + \
            Inclusion("characters", "characters.character")
        rep = self.s.get('anime', modifier).resources
        if len(rep) >= 1:
            return self._convertCharacter(rep[0])

    def _convertAnime(self, a, force=False):
        if not force and a.subtype not in self.subtypes:
            return None

        with self.database.get_lock():
            id = self.database.getId("kitsu_id", int(a.id))

        data = Anime()
        # data['kitsu_id'] = int(a.id)
        data['id'] = id
        if a.canonicalTitle[-1] == ".":
            data['title'] = a.canonicalTitle[:-1]
        else:
            data['title'] = a.canonicalTitle
        try:
            data['picture'] = a.posterImage.small
        except Exception:
            pass

        pictures = []
        for size in ('small', 'medium', 'large'):
            img_url = a.posterImage.get(size)
            if img_url:
                pictures.append({
                    'url': img_url,
                    'size': size
                })

        self.save_pictures(id, pictures)

        data['title_synonyms'] = list(a.titles.values()) + [data['title']]
        epoch = datetime(1970, 1, 1)
        if a.startDate is None:
            data['date_from'] = None
        else:
            d = datetime.fromisoformat(a.startDate)
            data['date_from'] = int((d - epoch).total_seconds())
            
        if a.endDate is None:
            data['date_to'] = None
        else:
            d = datetime.fromisoformat(a.endDate)
            data['date_to'] = int((d - epoch).total_seconds())
        
        data['synopsis'] = a.synopsis
        data['episodes'] = int(
            a.episodeCount) if a.episodeCount is not None else None
        data['duration'] = int(
            a.episodeLength) if a.episodeLength is not None else None
        data['rating'] = a.ageRating

        data['status'] = self.getStatus(data)
        # data['status'] = 'UPDATE'
        if a.youtubeVideoId is not None and a.youtubeVideoId != "":
            data['trailer'] = "https://www.youtube.com/watch?v=" + a.youtubeVideoId

        if isinstance(a.relationships.genres, relationships.MultiRelationship):
            genres = self.getGenres(
                [
                    dict([
                        ('id', e['id']),
                        ('name', e['attributes']['name'])
                    ])
                    for e in (g.json for g in a.genres)
                ]
            )
        else:
            genres = []
        data['genres'] = genres

        if isinstance(a._relationships['mediaRelationships'], relationships.MultiRelationship):
            rels = []
            for f in a.mediaRelationships:
                rel = {
                    'type': f.destination.type,
                    'name': f.role,
                    'rel_id': f.destination.id,
                    'anime': {
                        'title': f.role + " - " + data['title']
                    }
                }
                rels.append(rel)
            self.save_relations(id, rels)

        if not isinstance(a.relationships.mappings, relationships.LinkRelationship):
            mapped = []

            for m in a.mappings:  # Iterate over each external anime
                api_id = m.externalId
                site = m.externalSite

                if site in self.mappedSites.keys():  # Only save known websites
                    api_key = self.mappedSites[site]
                    mapped.append({
                        'api_key': api_key,
                        'api_id': api_id
                    })
                else:
                    pass

            self.save_mapped(int(a.id), mapped)

        return data

    def _convertCharacter(self, c, anime_id=None):
        mal_id = int(c.character.malId)
        kitsu_id = int(c.character.id)

        # TODO - merge function

        sql = "SELECT EXISTS(SELECT 1 FROM charactersIndex WHERE (kitsu_id != ? or kitsu_id is null) and mal_id=?)"
        api_exist = bool(self.database.sql(sql, (kitsu_id, mal_id,))[0][0])
        if api_exist:
            temp_id = self.database.getId("mal_id", mal_id, table="characters")
            self.database.sql(
                "DELETE FROM charactersIndex WHERE id=?", (temp_id,))
            self.database.sql("DELETE FROM characters WHERE id=?", (temp_id,))

        id = self.database.getId("kitsu_id", kitsu_id, table="characters")
        self.database.sql(
            "UPDATE charactersIndex SET mal_id = ? WHERE kitsu_id=?",
            (mal_id,
             kitsu_id))

        try:
            self.database.save()
        except Exception:
            pass

        id = self.database.getId("kitsu_id", kitsu_id, table="characters")
        out = Character()
        out['id'] = id
        # out['role'] = c.role.lower()
        out['name'] = c.character.name

        if c.character.image is not None:
            out['picture'] = c.character.image['original']

        out['desc'] = c.character.description

        if anime_id is not None:
            anime_data = {anime_id: c.role.lower()}
            self.save_animeography(id, anime_data)

        return out


if __name__ == "__main__":
    from APIUtils import ApiTester

    ApiTester(KitsuIoWrapper)
