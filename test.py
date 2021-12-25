# import re,requests,urllib,socket

# url = "magnet:?xt=urn:btih:RRN4MNLGBHMAVYU372YXQ46NU3WVZ5WR&dn=%5BSubsPlease%5D%20Mushoku%20Tensei%20-%2015%20%28720p%29%20%5B14A68BE1%5D.mkv&xl=686477749&tr=http%3A%2F%2Fnyaa.tracker.wf%3A7777%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2F9.rarbg.to%3A2710%2Fannounce&tr=udp%3A%2F%2F9.rarbg.me%3A2710%2Fannounce&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.internetwarriors.net%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.cyberia.is%3A6969%2Fannounce&tr=udp%3A%2F%2Fexodus.desync.com%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker3.itzmx.com%3A6961%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce&tr=udp%3A%2F%2Ftracker.tiny-vps.com%3A6969%2Fannounce&tr=udp%3A%2F%2Fretracker.lanta-net.ru%3A2710%2Fannounce&tr=http%3A%2F%2Fopen.acgnxtracker.com%3A80%2Fannounce&tr=wss%3A%2F%2Ftracker.openwebtorrent.com"
# pattern = re.compile(r"^magnet:?")

# print(str("0x41727101980"))

# def getTracker(protocol,url,port,info_hash,size):
#     params = {
#         'info_hash': info_hash,
#         'peer_id': "weshweshcava12345678",
#         'port': port,
#         'uploaded': '0',
#         'downloaded': '0',
#         'left': str(size),
#         'compact': '1',
#         'no_peer_id': '0',
#         'event': 'started'
#     }
#     if protocol == "http":
#         try:
#             page = requests.get(url, params=params)
#         except ConnectionResetError as e:
#             print(e)
#         except requests.exceptions.ConnectionError as e:
#             print(2,e)
#         except requests.exceptions.InvalidSchema as e:
#             print(3,e)
#         else:
#             print("---",page.text)
#     elif protocol == "udp":
#         sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
#         sock.sendto(bytes(MESSAGE, "utf-8"), (UDP_IP, UDP_PORT))
#     else:
#         print(protocol,"not supported")

# if pattern.match(url):
#     print("Magnet!")

#     parameters = re.compile(r"(\w{2})=([^&]+)")
#     data = list((a,urllib.parse.unquote(b)) for a,b in parameters.findall(url))
#     for i,d in enumerate(data):
#         k,v = d
#         if k == "tr":
#             try:
#                 v = urllib.parse.urlparse(v)
#             except Exception as e:
#                 print(e)
#         else:
#             print(k,v)
#         data[i] = (k,v)

#     print("___________")
#     info_hash = [d[1] for d in data if d[0] == "xt"][0].split(":")[-1]
#     size = [d[1] for d in data if d[0] == "xl"][0]
#     print(info_hash,size)
#     for k,v in (d for d in data if d[0] == "tr"):
#         url = urllib.parse.urlunparse(v)
#         print(url)
#         getTracker(v.scheme,url,v.port,info_hash,size)

from collections import deque
import time
import sys

def get_paths(graph, start, end):
    queue = []
    queue.append((start, [start]))
    visited = set()

    while queue:
        node, path = queue.pop(0)
        for adjacent_node in graph.get(node, []):
            if adjacent_node not in visited:
                visited.add(adjacent_node)
                if adjacent_node == end:
                    yield path + [adjacent_node]
                else:
                    queue.append((adjacent_node, path + [adjacent_node]))


def get_paths_2(graph, start, end, path=[]):
    path = path + [start]
    if start == end:
        return [path]
    if start not in graph:
        return []
    paths = []
    for node in graph[start]:
        if node not in path:
            newpaths = get_paths_2(graph, node, end, path)
            for newpath in newpaths:
                paths.append(newpath)
    return paths


def get_paths_3(graph, start, end):
    paths = {start: [start]}
    que = deque([start])
    while len(que):
        node = que.popleft()
        for adj_node in graph.get(node, []):
            if adj_node not in paths:
                paths[adj_node] = []
                que.append(adj_node)
            paths[adj_node].append(node)

    print(paths.keys(), end, end in paths.keys())
    def parse_paths(paths, node):
        if node not in paths:
            yield [node]
            return
        parents = paths[node]
        for parent in parents:
            for path in parse_paths(paths, parent):
                yield path + [node]

    return list(parse_paths(paths, end))


def find_shortest_path(graph, start, end):
    paths = {start: [start]}
    que = deque([start])
    while len(que):
        node = que.popleft()
        for adj_node in graph.get(node, []):
            if adj_node not in paths:
                paths[adj_node] = [paths[node], adj_node]
                que.append(adj_node)
    path = paths.get(end)
    if not path:
        return
    while len(path) > 1:
        yield path[1]
        path = path[0]
    yield path[0]


def solve_question(args):
    graph, signaux, a, b = args
    if a == b:
        # print(signaux[a])
        return signaux[a]
    else:
        active = set()

        print("A", get_paths_3(graph, a, b))

        for path in get_paths(graph, a, b):
            for p in path:
                active.add(p)

        if len(active) == 0:
            # print(0)
            return 0
        else:
            signal = 1
            for p in active:
                signal = (signal * signaux[p]) % 1671404011

            # print(signal)
            return signal


def calculer_signaux(n, m, r, signaux, fils, questions):
    """
    :param n: nombre de puces
    :type n: int
    :param m: nombre de fils
    :type m: int
    :param r: nombre de questions
    :type r: int
    :param signaux: liste des signaux
    :type signaux: list[int]
    :param fils: liste des fils entre les puces
    :type fils: list[dict["puce1": int, "puce2": int]]
    :param questions: liste des questions
    :type questions: list[dict["puce a": int, "puce b": int]]
    """

    start = time.time()
    graph = dict()
    for a, b in fils:
        graph[a] = graph.get(a, []) + [b]
        graph[b] = graph.get(b, []) + [a]

    args = ((graph, signaux, *q) for q in questions)
    for e in map(solve_question, args):
        # print(e)
        pass
    print("b", time.time() - start)

import random

if __name__ == "__main__":

    while True:
        n, r = random.randint(0, 100000), random.randint(0, 100000)
        m = n - 1
        signaux = random.sample(range(1, 1671404011), n)
        fils = list(random.sample(range(n), 2) for i in range(random.randint(0, n)))
        questions = list(random.sample(range(n), 2) for i in range(random.randint(0, n)))
        calculer_signaux(n, m, r, signaux, fils, questions)
