from APIUtils import APIUtils, Anime, Character, log
import requests
import json
import secrets
import webbrowser
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


class MyAnimeListNetWrapper(APIUtils):
    def __init__(self, dbPath, tokenPath='token.json'):
        super().__init__(dbPath)
        self.CLIENT_ID = '12811732694cf9a5ce1eff0694af5dc8'
        self.CLIENT_SECRET = 'fbf4c615abc334263ac2a3c92386586bafa067619be7a4f3fb7c2f6824f2bf03'
        self.hostName = "127.0.0.1"
        self.serverPort = 2412
        self.tokenPath = tokenPath
        self.token = self.getToken()
        self.baseUrl = "https://api.myanimelist.net/v2/"

        self.apiKey = "mal_id"

        fields = ('alternative_titles', 'average_episode_duration',
                  'broadcast', 'end_date', 'genres', 'id',
                  'main_picture', 'num_episodes', 'start_date',
                  'status', 'synopsis', 'title', 'related_anime', 'rating')
        self.fields = ','.join(fields)

    def anime(self, id, save=True, relations=False):
        mal_id = self.getId(id)
        if mal_id is None:
            return {}

        a = self.get("anime", mal_id, fields=self.fields)
        data = self._convertAnime(a)
        if save:
            self.db(id=id, table="anime").set(data)
        return data

    def animeCharacters(self, id):
        pass

    def animePictures(self, id):
        pass

    def schedule(self, save=True, limit=100):
        pass

    def searchAnime(self, search, save=True, limit=50):
        data = self.get("anime", q=search, limit=limit)['data']
        for a in data:
            yield self._convertAnime(a['node'])

    def character(self, id):
        pass

    def _convertAnime(self, a, relations=False):
        id = self.db.getId("mal_id", int(a["id"]))
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

        if len(titles) > 0:
            out['title_synonyms'] = json.dumps(titles)
        else:
            out['title_synonyms'] = None

        out['date_from'] = a['start_date'] if 'start_date' in a.keys() else None
        out['date_to'] = a['end_date'] if 'end_date' in a.keys() else None
        out['picture'] = list(a['main_picture'].items(
        ))[-1][1] if 'main_picture' in a.keys() else None
        out['synopsis'] = a['synopsis'] if 'synopsis' in a.keys() else None
        out['episodes'] = a['num_episodes'] if 'num_episodes' in a.keys() else None
        out['duration'] = a['average_episode_duration'] // 60 if 'average_episode_duration' in a.keys() else None
        out['status'] = None  # a['status'] if 'status' in a.keys() else None
        out['rating'] = a['rating'].upper() if 'rating' in a.keys() else None
        if 'broadcast' in a.keys():
            weekdays = ('monday', 'tuesday', 'wednesday',
                        'thursday', 'friday', 'saturday', 'sunday')
            out['broadcast'] = "{}-{}-{}".format(weekdays.index(
                a['broadcast']['day_of_the_week']), *a['broadcast']['start_time'].split(":"))

        # out['trailer'] = a['trailer_url'] if 'trailer_url' in a.keys() else None

        if out['date_from'] is None:
            out['status'] = 'UPDATE'
        else:
            out['status'] = self.getStatus(
                out) if 'status' in a.keys() else None

        genres = []
        if 'genres' in a.keys():
            for g in a['genres']:
                if not self.db.exist("mal_id", g['id'], "genres"):
                    self.db.sql(
                        "INSERT INTO genres(mal_id,name) VALUES(?,?)", (g['id'], g['name']))

                genres.append(self.db.sql(
                    "SELECT id FROM genres WHERE mal_id=?", (g['id'],))[0][0])
        out['genres'] = json.dumps(genres)

        if 'related' in a.keys():
            for relation, rel_data_list in a['related'].items():
                for rel_data in rel_data_list:
                    if rel_data['type'] == "anime":
                        rel_id = self.db.getId("mal_id", rel_data["id"])
                        if not self.db.sql(
                                "SELECT EXISTS(SELECT 1 FROM related WHERE id=? AND rel_id=?);", (id, rel_id)):
                            rel = {"id": id, "relation": relation,
                                   "rel_id": rel_id}
                            self.db(table="related").set(rel, save=False)
        self.db.save()

        return out

    def _convertCharacter(self, c, anime_id=None):
        pass

    def get(self, *args, **kwargs):
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

        # log(f">>> Greetings {user['name']}! <<<")
        return True

    def getNewToken(self):
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
        log('MAL token generated successfully!')

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
        log('MAL token refreshed successfully!')

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

        return token["access_token"]
