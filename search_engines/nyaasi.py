""" Torrent web parser for nyaa.si """
import urllib.parse
import io

from lxml import etree
import requests


class Parser:
    def search(self, terms, limit=50):
        terms = terms.strip()
        searchterms = urllib.parse.quote_plus(terms)

        tree = None
        url = "https://nyaa.si/?page=rss&q={}&c=1_0&f=0".format(searchterms)
        try:
            # print(url)
            r = requests.get(url, timeout=10)
        except requests.exceptions.ConnectionError:
            print("Nyaasi - No internet connection!")
        except requests.exceptions.ReadTimeout:
            print("Nyaasi - Timed out!")
        else:
            try:
                tree = etree.parse(io.BytesIO(r.content))
            except etree.XMLSyntaxError as e:
                print("Nyaasi -", e, tree)
                return
            for child in tree.getroot().find('channel'):
                try:
                    if child.tag == 'item':
                        filename = child.find('title').text
                        torrent_url = child.find('link').text
                        seeds = child.find(
                            '{https://nyaa.si/xmlns/nyaa}seeders').text
                        leechs = child.find(
                            '{https://nyaa.si/xmlns/nyaa}leechers').text
                        file_size = child.find(
                            "{https://nyaa.si/xmlns/nyaa}size").text
                        yield {'filename': filename, 'torrent_url': torrent_url, 'seeds': seeds, 'leechs': leechs, 'file_size': file_size}
                except Exception as e:
                    print("Nyaasi - error:", e)


if __name__ == "__main__":
    p = Parser()

    r = p.search("meikyuu")
    for m in r:
        print(m)
