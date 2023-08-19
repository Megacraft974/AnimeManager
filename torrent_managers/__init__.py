from .qbittorent import qBittorrent
from .base import TorrentListFilter, Torrent, TorrentException

managers = {}
for m in [qBittorrent]:
    managers[m.name] = m

