import json
import os
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

try:
    from .APIUtils import APIUtils, Anime, Character
except ImportError:
    # Local testing
    import sys
    import os
    sys.path.append(os.path.abspath('./'))
    from APIUtils import APIUtils, Anime, Character


class MyAnimeListNetWrapper(APIUtils):
    def __init__(self, dbPath, tokenPath='token.json'):
        super().__init__(dbPath)
        self.CLIENT_ID = '12811732694cf9a5ce1eff0694af5dc8'
        self.CLIENT_SECRET = 'fbf4c615abc334263ac2a3c92386586bafa067619be7a4f3fb7c2f6824f2bf03'
        self.hostName = "127.0.0.1"
        self.serverPort = 2412
        self.tokenPath = os.path.join(os.path.dirname(__file__), tokenPath)
        # self.tokenPath = tokenPath
        self.token = self.getToken()
        self.baseUrl = "https://api.myanimelist.net/v2/"

        self.apiKey = "mal_id"

        fields = ('alternative_titles', 'average_episode_duration',
                  'broadcast', 'end_date', 'genres', 'id',
                  'main_picture', 'num_episodes', 'start_date',
                  'status', 'synopsis', 'title', 'related_anime', 'rating')
        self.fields = ','.join(fields)

    def anime(self, id, relations=False):
        mal_id = self.getId(id)
        if mal_id is None:
            return {}

        a = self.get("anime", mal_id, fields=self.fields)
        if not a:
            return {}
        data = self._convertAnime(a)
        return data

    def animeCharacters(self, id):
        pass

    def animePictures(self, id):
        pass

    def schedule(self, save=True, limit=100):
        pass

    def searchAnime(self, search, save=True, limit=50):
        rep = self.get("anime", q=search, limit=limit, fields=self.fields)

        count = 0
        looping = True
        while looping:
            if 'data' not in rep:
                looping = False
                break

            for a in rep['data']:
                data = self._convertAnime(a['node'])

                if len(data) != 0:
                    yield data

                    count += 1
                    if count >= limit:
                        return

            if rep.get('paging', {}).get('next', None):
                next_url = rep['paging']['next']
                rep = self.get(next_url)
            else:
                looping = False

    def character(self, id):
        pass

    def _convertAnime(self, a, relations=False):
        id = self.database.getId("mal_id", int(a["id"]))
        out = Anime()

        out["id"] = id
        # out["mal_id"] = a["mal_id"]
        out['title'] = a['title']
        if a['title'][-1] == ".":
            out['title'] = a['title'][:-1]

        titles = [a['title']]
        if 'alternative_titles' in a.keys():
            for sub in a['alternative_titles'].values():
                if isinstance(sub, list):
                    titles += sub
                else:
                    titles.append(sub)

        out['title_synonyms'] = titles
        out['date_from'] = a['start_date'] if 'start_date' in a.keys() and len(
            a['start_date'].split('-')) == 3 else None
        out['date_to'] = a['end_date'] if 'end_date' in a.keys() and len(
            a['end_date'].split('-')) == 3 else None
        out['picture'] = list(
            a['main_picture'].items()
            )[-1][1] if 'main_picture' in a.keys() else None

        pictures = []
        for size, url in a['main_picture'].items():
            if size in ('small', 'medium', 'large'):
                pictures.append({
                    'url': url,
                    'size': size
                })
            
        self.save_pictures(id, pictures)

        out['synopsis'] = a['synopsis'] if 'synopsis' in a.keys() else None
        out['episodes'] = a['num_episodes'] if 'num_episodes' in a.keys() else None
        out['duration'] = a['average_episode_duration'] // 60 if 'average_episode_duration' in a.keys() else None
        out['status'] = None  # a['status'] if 'status' in a.keys() else None
        out['rating'] = a['rating'].upper() if 'rating' in a.keys() else None
        if 'broadcast' in a.keys() and 'start_time' in a['broadcast'].keys():
            weekdays = ('monday', 'tuesday', 'wednesday',
                        'thursday', 'friday', 'saturday', 'sunday')
            weekday = a['broadcast']['day_of_the_week']

            if weekday in weekdays: # Can be 'other' -> Not scheduled once per week 
                w = weekdays.index(weekday)
                h, m = a['broadcast']['start_time'].split(":")[:2]
                
                self.save_broadcast(id, w, h, m)

                out['broadcast'] = "{}-{}-{}".format(w, h, m) # TODO - Should be removed

        # out['trailer'] = a['trailer_url'] if 'trailer_url' in a.keys() else None

        if out['date_from'] is None:
            out['status'] = 'UPDATE'
        else:
            out['status'] = self.getStatus(
                out) if 'status' in a.keys() else None

        if 'genres' in a.keys():
            genres = self.getGenres(a['genres'])
        else:
            genres = []
        out['genres'] = genres

        if 'related_anime' in a.keys():
            rels = []
            for relation in a['related_anime']:
                node = relation['node']
                if 'main_picture' not in node:
                    continue
                rel = {
                    'type': 'anime', 
                    'name': relation['relation_type_formatted'], 
                    'rel_id': node['id'], 
                    'anime': {
                        'title': node['title'],
                        'picture': node['main_picture']['medium']
                    }
                }
                rels.append(rel)
            self.save_relations(id, rels)

        return out

    def _convertCharacter(self, c, anime_id=None):
        pass

    def get(self, *args, **kwargs):
        if self.token is None:
            return {}
        url = self.baseUrl + "/".join(map(str, args))
        if len(kwargs) > 0:
            url += "?" + "&".join(str(k) + "=" + str(v)
                                  for k, v in kwargs.items())
        headers = {'Authorization': f'Bearer {self.token}'}
        try:
            r = requests.get(url, headers=headers)
        except requests.exceptions.ConnectionError:
            return {}
        else:
            return r.json()

    def check_validity(self, access_token, refresh_token=None):
        url = 'https://api.myanimelist.net/v2/users/@me'
        try:
            rep = requests.get(url, headers={
                'Authorization': f'Bearer {access_token}'
            })
        except requests.exceptions.ConnectionError:
            return False

        if rep.status_code == 401:
            rep.close()
            return False
        user = rep.json()
        rep.close()

        # self.log(f">>> Greetings {user['name']}! <<<")
        return True

    def getNewToken(self):
        log = self.log

        class AuthServer(BaseHTTPRequestHandler):
            def do_GET(self):
                log(
                    "SERVER - Received GET request from address {}".format(self.client_address))
                req = self.path.split("/")[1]
                args = {}
                for arg in req.split("?")[1:]:
                    a = arg.split("=")
                    if len(a) == 2:
                        args[a[0]] = a[1]
                if "code" in args.keys():
                    code = args["code"]
                    globals()['Auth_Code'] = code

                    self.send_response(200)
                    self.end_headers()
                    # self.wfile.write(bytes('<!DOCTYPE html><html><head><script type="text/javascript">function close_window(){window.close();}</script></head><body onload="close_window();"><p>WTF</p></body></html>', "utf-8"))
                    self.wfile.write(bytes('OK', "utf-8"))
                else:
                    self.wfile.write(bytes("Error", "utf-8"))

        code = secrets.token_urlsafe(100)[:128]
        url = f'https://myanimelist.net/v1/oauth2/authorize?response_type=code&client_id={self.CLIENT_ID}&code_challenge={code}'
        webbrowser.open(url)

        authServ = HTTPServer((self.hostName, self.serverPort), AuthServer)
        while True:
            authServ.handle_request()
            if 'Auth_Code' in globals().keys():
                authorisation_code = globals()['Auth_Code']
                break

        url = 'https://myanimelist.net/v1/oauth2/token'
        data = {
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
            'code': authorisation_code,
            'code_verifier': code,
            'grant_type': 'authorization_code'
        }

        response = requests.post(url, data)
        response.raise_for_status()

        token = response.json()
        response.close()
        self.log('MAL token generated successfully!')

        with open(self.tokenPath, 'w') as file:
            json.dump(token, file, indent=4)

        if not self.check_validity(token['access_token']):
            return self.refresh_token(token['refresh_token'])

        return token

    def refresh_token(self, r_token):
        url = 'https://myanimelist.net/v1/oauth2/token'
        data = {
            'client_id': self.CLIENT_ID,
            'client_secret': self.CLIENT_SECRET,
            'grant_type': "refresh_token",
            'refresh_token': r_token,
        }

        try:
            response = requests.post(url, data)
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            return

        token = response.json()
        response.close()
        self.log('MAL token refreshed successfully!')

        with open(self.tokenPath, 'w') as file:
            json.dump(token, file, indent=4)

        return token

    def getToken(self):
        if os.path.isfile(self.tokenPath):
            with open(self.tokenPath, 'r') as file:
                token = json.load(file)
            if not self.check_validity(token['access_token']):
                token = self.refresh_token(token['refresh_token'])
        else:
            token = self.getNewToken()

        if token is not None:
            return token["access_token"]
        else:
            self.log("Error while fetching MAL token!")
            # if os.path.isfile(self.tokenPath):
            #     os.remove(self.tokenPath)
            return None


if __name__ == "__main__":
    import os
    appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
    dbPath = os.path.join(appdata, "animeData.db")
    wrapper = MyAnimeListNetWrapper(dbPath)

    a = wrapper.anime(2)
    pass
    for a in wrapper.searchAnime('arif'):
        print(a['id'], a['date_to'], a['title'])
        pass
    pass
