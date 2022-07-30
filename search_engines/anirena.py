""" Torrent web parser for anirena.com """
import urllib.parse
import io
import re

from lxml import etree

try:
    from .parserUtils import ParserUtils, exceptions
except ImportError:
    # Local testing
    import os
    import sys
    sys.path.append(os.path.abspath('./'))
    from parserUtils import ParserUtils, exceptions


class Parser(ParserUtils):
    def search(self, terms, limit=50):
        terms = terms.strip()
        searchterms = urllib.parse.quote_plus(terms)

        tree = None
        url = "https://www.anirena.com/rss.php?s={}".format(searchterms)
        try:
            r = self.get(url, timeout=15)
            if r.status_code == 522:
                self.log("Timed out!")
                return
        except exceptions.ConnectionError:
            self.log("Anirena - No internet connection!")
            yield False
        except exceptions.ReadTimeout:
            self.log("Anirena - Timed out!")
            yield False
        else:
            tree = etree.parse(io.BytesIO(r.content))
            pattern = re.compile(
                r"(\d+?) seeder\(s\), (\d+?) leecher\(s\), \d+? downloads, (\S+? .B)")
            for child in tree.getroot().find('channel'):
                try:
                    if child.tag == 'item':
                        category = child.find('category').text
                        if category == "Anime":
                            filename = child.find('title').text
                            torrent_url = child.find('link').text
                            desc = child.find('description').text
                            seeds, leechs, file_size = pattern.findall(desc)[0]
                            out = {
                                'filename': filename,
                                'torrent_url': torrent_url,
                                'seeds': seeds,
                                'leechs': leechs,
                                'file_size': file_size}
                            yield out
                except Exception as e:
                    self.log("Anirena - error:", e)


if __name__ == "__main__":
    p = Parser()

    r = p.search("meikyu")
    for m in r:
        # pass
        print(m)
