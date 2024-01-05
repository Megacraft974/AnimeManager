from .transmission import Transmission
from .qbittorrent import qBittorrent
from .base import TorrentListFilter, Torrent, TorrentException

managers = {}
for m in [qBittorrent, Transmission]:
    managers[m.name] = m
