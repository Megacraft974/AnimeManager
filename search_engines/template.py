""" Template to use for the torrent database web parsers """


class Parser:
    def search(self, terms, results=50):
        data = [{'filename': 'firstMatch.mkv',
                 'torrent_url': 'https://somewebsite.com/torrent_id',
                 'seeds': 0,
                 'leechs': 0,
                 'file_size': 0},
                {'filename': 'secondMatch.mkv',
                 'torrent_url': 'https://somewebsite.com/other_torrent_id',
                 'seeds': 0,
                 'leechs': 0,
                 'file_size': 0}]
        return data
