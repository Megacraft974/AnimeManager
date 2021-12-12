""" Torrent web parser for nyaa.si """
import urllib.parse
import requests
import io
import re

from bs4 import BeautifulSoup


class Parser():
    def search(self, terms, limit=50):
        terms = terms.strip()
        searchterms = urllib.parse.quote_plus(terms)

        soup = None
        url = "https://www.tokyotosho.info/search.php?terms={}&type=1&searchName=true&searchComment=true".format(
            searchterms)
        try:
            # print(url)
            r = requests.get(url, timeout=10)
        except requests.exceptions.ConnectionError:
            print("Tokyotosho - No internet connection!")
        except requests.exceptions.ReadTimeout:
            print("Tokyotosho - Timed out!")
        else:
            soup = BeautifulSoup(r.content, "html.parser")
            pattern = re.compile(r'\| Size: (\S*?) \|')
            table = soup.find("table", class_="listing")
            body = table.find_all("tr")[1:]
            for rowA, rowB in self.table_iter(body):
                try:
                    title_column = rowA.find("td", class_="desc-top")
                    filename = title_column.find_all("a")[-1].text
                    torrent_url = title_column.find_all("a")[-1]['href']

                    desc = rowB.find("td", class_="desc-bot").text
                    result = pattern.findall(desc)
                    file_size = result[0] if len(result) >= 1 else ""

                    stats = rowB.find("td", class_="stats")
                    seeds, leechs = map(
                        lambda e: e.text, stats.find_all("span")[:2])

                    out = {
                        'filename': filename,
                        'torrent_url': torrent_url,
                        'seeds': seeds,
                        'leechs': leechs,
                        'file_size': file_size}
                    yield out
                except Exception as e:
                    print("Tokyotosho - error:", e)

    def table_iter(self, table):
        a, b = None, None
        for e in table:
            if a is None:
                a = e
            elif b is None:
                b = e
                yield a, b
                a, b = None, None


if __name__ == "__main__":
    p = Parser()

    r = p.search("meikyu")
    for m in r:
        # pass
        print(m)
