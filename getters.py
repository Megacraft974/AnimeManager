import threading

from dbManager import db

class get:
    def database(self):
        if threading.main_thread() == threading.current_thread():
            return self.database
        else:
            return db(self.dbPath)

    def image(self, path, size=None):
        if os.path.isfile(path):
            img = Image.open(path)
        else:
            img = Image.new('RGB', (10, 10), self.colors['Gray'])
        if size is not None:
            img = img.resize(size)
        return ImageTk.PhotoImage(img, master=self.root)

    def status(self, anime, reverse=True):
        if anime.status is not None:
            if anime.status in self.status.values():
                return anime.status
            if anime.status == 'NONE':
                self.log('DB_ERROR', "Unknown status for id", id)
            if anime.status == 'UPDATE':
                return 'UNKNOWN'
            return anime.status

        if anime.date_from is None:
            status = 'UNKNOWN'
        else:
            if date.fromisoformat(anime.date_from) > date.today():
                status = 'UPCOMING'
            else:
                if anime.date_to is None:
                    if anime.episodes == 1:
                        status = 'FINISHED'
                    else:
                        status = 'AIRING'
                else:
                    if date.fromisoformat(anime.date_to) > date.today():
                        status = 'AIRING'
                    else:
                        status = 'FINISHED'
        return status

    def torrent_name(self, file):
        with open(file, 'rb') as f:
            m = re.findall(rb"name\d+:(.*?)\d+:piece length", f.read())
        if len(m) != 0:
            return m[0].decode()
        else:
            return None

    def torrent_hash(self, path):
        objTorrentFile = open(path, "rb")
        try:
            decodedDict = bencoding.bdecode(objTorrentFile.read())
        except Exception as e:
            raise e

        info_hash = hashlib.sha1(bencoding.bencode(
            decodedDict[b"info"])).hexdigest()
        return info_hash

    def torrent_color(self, title):
        def fileFormat(f): return ''.join(
            f.rsplit(".torrent", 1)[0].split(" ")).lower()
        timeNow = time.time()
        if hasattr(self, 'formattedTorrentFiles') and timeNow - \
                self.formattedTorrentFiles[0] < 10:
            files = self.formattedTorrentFiles[1]
        else:
            files = [fileFormat(f) for f in os.listdir(self.torrentPath)]
            self.formattedTorrentFiles = (timeNow, files)

        fg = self.colors['White']
        for f in files:
            t = fileFormat(title)
            if t in f or f in t:
                fg = self.colors['Blue']
        else:
            for color, marks in self.fileMarkers.items():
                for mark in marks:
                    if mark in title.lower():
                        fg = self.colors[color]
                        break
        return fg

    def folder_format(self, title):
        chars = []
        spaceLike = list("-")
        if title is None:
            return " "
        for char in title:
            if char.isalnum() or char == " ":
                chars.append(char)
            if char in spaceLike:
                chars.append(" ")
        return "".join(chars)

    def folder(self, id=None, anime=None):
        if anime is None or anime == {}:
            if id is None:
                raise Exception("Id required!")
            database = self.getDatabase()
            anime = database(id=id, table="anime").get()
            self.animeFolder = os.listdir(self.animePath)
        else:
            if type(anime) != Anime:
                anime = Anime(anime)
            if id is None:
                id = anime.id

        for f in self.animeFolder:
            f_id = int(f.rsplit(" ", 1)[1])
            if f_id == id:
                folder = os.path.normpath(os.path.join(self.animePath, f))
                return folder
        folderFormat = self.getFolderFormat(anime.title)
        folderName = "{} - {}".format(folderFormat, id)
        folder = os.path.normpath(os.path.join(self.animePath, folderName))
        return folder
