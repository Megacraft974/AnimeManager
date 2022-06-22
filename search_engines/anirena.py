""" Torrent web parser for anirena.com """
import random
import string
import time
import urllib.parse
import io
import re

import requests
from lxml import etree
from sympy import EX


class Parser:
    def search(self, terms, limit=50):
        terms = terms.strip()
        searchterms = urllib.parse.quote_plus(terms)

        tree = None
        url = "https://www.anirena.com/rss.php?s={}".format(searchterms)
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 522:
                print("Timed out!")
                return
        except requests.exceptions.ConnectionError:
            print("Anirena - No internet connection!")
        except requests.exceptions.ReadTimeout:
            print("Anirena - Timed out!")
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
                    print("Anirena - error:", e)


if __name__ == "__main__":
    p = Parser()

    r = p.search("meikyu")
    for m in r:
        # pass
        print(m)
