# from tkinter import *
from operator import itemgetter
from thefuzz import fuzz, process as fuzz_process
from getters import Getters
import time
from datetime import datetime, timezone, timedelta, time as datetime_time
import requests
from collections import defaultdict, deque
from classes import SortedDict, Anime, AnimeList, SortedList, RegroupList
import re
import os
import threading
import queue
import multiprocessing
import json
from qbittorrentapi import Client
import random
from animeManager import Manager

from utils import TableFrame

import classes
from animeAPI.JikanMoe import JikanMoeWrapper
appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
dbPath = os.path.join(appdata, "animeData.db")

data = [
    ('Anipakku',
     [{'filename': '[Anipakku] Kanojo, Okarishimasu (S01) [BD 1080p][HEVC x265 10bit][Dual Audio][Multi-Subs] (Rent-a-Girlfriend Kanokari Dub Eng PT-BR Spa Latin)',
       'torrent_url': 'https://nyaa.si/download/1406402.torrent',
       'seeds': 15,
       'leechs': 1,
       'file_size': '15.0 GiB'
       }]),
    ('HR',
     [{'filename': '[HR] Kanojo, Okarishimasu S01 (2020) [BluRay 1080p HEVC E-OPUS] HR-SR',
       'torrent_url': 'http://www.anirena.com/dl/132794',
       'seeds': 2,
       'leechs': 0,
       'file_size': '7.88 GB'},
      {'filename': '[HR] Kanojo, Okarishimasu S01 [Web 1080p x265 E-OPUS]~HR-GZ',
       'torrent_url': 'https://www.anirena.com/dl/99929',
       'seeds': 0,
       'leechs': 0,
       'file_size': '1.94GB'},
      {'filename': '[HR] Kanojo, Okarishimasu S01E02 [1080p HEVC Multi] HR-GZ',
       'torrent_url': 'http://www.anirena.com/dl/96005',
       'seeds': 0,
       'leechs': 0,
       'file_size': '179.88 MB'}]),
    ('PuyaSubs!',
     [{'filename': '[PuyaSubs!] Kanojo, Okarishimasu - 16 [ESP-ENG][1080p][F22ADC69].mkv',
       'torrent_url': 'https://nyaa.si/download/1555633.torrent',
       'seeds': 28,
       'leechs': 0,
       'file_size': '1.4 GiB'},
      {'filename': '[PuyaSubs!] Kanojo, Okarishimasu - 15 [ESP-ENG][1080p][CACEAD23].mkv',
       'torrent_url': 'https://nyaa.si/download/1552810.torrent',
       'seeds': 25,
       'leechs': 0,
       'file_size': '1.4 GiB'}]),
    ('Yameii',
     [{'filename': '[Yameii] Kanojo, Okarishimasu - 14 | Rent-a-Girlfriend [English Dub] [WEB-DL 1080p] [2AF38893]',
       'torrent_url': 'https://nyaa.si/download/1555647.torrent',
       'seeds': 47,
       'leechs': 2,
       'file_size': '1.4 GiB'},
      {'filename': '[Yameii] Kanojo, Okarishimasu - 14 | Rent-a-Girlfriend [English Dub] [WEB-DL 720p] [E36893A2]',
       'torrent_url': 'https://nyaa.si/download/1555646.torrent',
       'seeds': 16,
       'leechs': 2,
       'file_size': '722.2 MiB'}]),
    ('SubsPlease',
     [{'filename': '[SubsPlease] Kanojo, Okarishimasu - 16 (720p) [27073892].mkv',
       'torrent_url': 'https://nyaa.si/download/1555656.torrent',
       'seeds': 155,
       'leechs': 6,
       'file_size': '727.8 MiB'}]),
    ('HRS',
     [{'filename': '[HRS] Kanojo, Okarishimasu 2 - 04 1080p.mkv',
       'torrent_url': 'https://nyaa.si/download/1555763.torrent',
       'seeds': 4,
       'leechs': 0,
       'file_size': '337.3 MiB'}]),
    ('NanakoRaws',
     [{'filename': '[NanakoRaws] Kanojo, Okarishimasu SS2 - 04 (MBS 1920x1080 x264 AAC).mkv (include JPsub)',
       'torrent_url': 'https://nyaa.si/download/1556025.torrent',
       'seeds': 2,
       'leechs': 1,
       'file_size': '648.2 MiB'},
      {'filename': '[NanakoRaws] Kanojo, Okarishimasu SS2 - 03 (MBS 1920x1080 x264 AAC).mkv (include JPsub)',
       'torrent_url': 'https://nyaa.si/download/1552913.torrent',
       'seeds': 1,
       'leechs': 1,
       'file_size': '693.3 MiB'}]),
    ('CurryMassaman',
     [{'filename': '[CurryMassaman] Kanojo, Okarishimasu - 15 (AMZN 1920x1080 H.264 E-AC-3).mkv',
       'torrent_url': 'https://nyaa.si/download/1552794.torrent',
       'seeds': 29,
       'leechs': 1,
       'file_size': '1.4 GiB'},
      {'filename': '[CurryMassaman] Kanojo, Okarishimasu - 16 (AMZN 1920x1080 H.264 E-AC-3).mkv',
       'torrent_url': 'https://nyaa.si/download/1557845.torrent',
       'seeds': 20,
       'leechs': 2,
       'file_size': '795.7 MiB'},
      {'filename': '[CurryMassaman] Kanojo, Okarishimasu - 13 (AMZN 1920x1080 H.264 E-AC-3).mkv',
       'torrent_url': 'https://nyaa.si/download/1552792.torrent',
       'seeds': 12,
       'leechs': 1,
       'file_size': '795.4 MiB'},
      {'filename': '[CurryMassaman] Kanojo, Okarishimasu - 14 (AMZN 1920x1080 H.264 E-AC-3).mkv',
       'torrent_url': 'https://nyaa.si/download/1552793.torrent',
       'seeds': 11,
       'leechs': 2,
       'file_size': '845.3 MiB'}]),
    ('Ohys-Raws',
     [{'filename': '[Ohys-Raws] Kanojo, Okarishimasu 2 - 05 (JNN 1280x720 x264 AAC).mp4',
       'torrent_url': 'https://nyaa.si/download/1558537.torrent',
       'seeds': 228,
       'leechs': 91,
       'file_size': '303.1 MiB'},
      {'filename': '[Ohys-Raws] Kanojo, Okarishimasu 2 - 05 (JNN 1920x1080 x265 AAC).mp4',
       'torrent_url': 'https://nyaa.si/download/1558538.torrent',
       'seeds': 78,
       'leechs': 17,
       'file_size': '447.6 MiB'},
      {'filename': '[Ohys-Raws] Kanojo, Okarishimasu 2 - 04 (BS6 1280x720 x264 AAC).mp4',
       'torrent_url': 'https://nyaa.si/download/1555506.torrent',
       'seeds': 53,
       'leechs': 10,
       'file_size': '237.3 MiB'},
      {'filename': '[Ohys-Raws] Kanojo, Okarishimasu 2 - 03 (BS6 1280x720 x264 AAC).mp4',
       'torrent_url': 'https://nyaa.si/download/1552934.torrent',
       'seeds': 46,
       'leechs': 3,
       'file_size': '236.7 MiB'},
      {'filename': '[Ohys-Raws] Kanojo, Okarishimasu 2 - 04 (BS6 1920x1080 x265 AAC).mp4',
       'torrent_url': 'https://nyaa.si/download/1555509.torrent',
       'seeds': 27,
       'leechs': 1,
       'file_size': '337.7 MiB'}]),
    ('Lilith-Raws',
     [{'filename': '[Lilith-Raws] 出租女友 / Kanojo, Okarishimasu S02 - 05 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]',
       'torrent_url': 'https://nyaa.si/download/1558559.torrent',
       'seeds': 104,
       'leechs': 13,
       'file_size': '491.7 MiB'},
      {'filename': '[Lilith-Raws] 出租女友 / Kanojo, Okarishimasu S02 - 04 [Baha][WEB-DL][1080p][AVC AAC][CHT][MP4]',
       'torrent_url': 'https://nyaa.si/download/1555514.torrent',
       'seeds': 50,
       'leechs': 3,
       'file_size': '441.2 MiB'}]),
    ('NC-Raws',
     [{'filename': '[NC-Raws] 出租女友 / Kanojo, Okarishimasu S2 - 17 (B-Global 1920x1080 HEVC AAC MKV)',
       'torrent_url': 'https://nyaa.si/download/1558550.torrent',
       'seeds': 222,
       'leechs': 7,
       'file_size': '225.2 MiB'},
      {'filename': '[NC-Raws] 出租女友 / Kanojo, Okarishimasu S2 - 16 (B-Global 1920x1080 HEVC AAC MKV)',
       'torrent_url': 'https://nyaa.si/download/1555513.torrent',
       'seeds': 163,
       'leechs': 4,
       'file_size': '185.1 MiB'},
      {'filename': '[NC-Raws] 出租女友 第二季 / Kanojo, Okarishimasu S2 - 17 (Baha 1920x1080 AVC AAC MP4)',
       'torrent_url': 'https://nyaa.si/download/1558551.torrent',
       'seeds': 65,
       'leechs': 10,
       'file_size': '491.9 MiB'},
      {'filename': '[NC-Raws] 出租女友 第二季 / Kanojo, Okarishimasu S2 - 16 (Baha 1920x1080 AVC AAC MP4)',
       'torrent_url': 'https://nyaa.si/download/1555515.torrent',
       'seeds': 29,
       'leechs': 0,
       'file_size': '441.4 MiB'},
      {'filename': '[NC-Raws] 租借女友 / Kanojo, Okarishimasu S2 - 17 (CR 1920x1080 AVC AAC MKV)',
       'torrent_url': 'https://nyaa.si/download/1558586.torrent',
       'seeds': 28,
       'leechs': 11,
       'file_size': '1.4 GiB'},
      {'filename': '[NC-Raws] 租借女友 / Kanojo, Okarishimasu S2 - 16 (CR 1920x1080 AVC AAC MKV)',
       'torrent_url': 'https://nyaa.si/download/1555570.torrent',
       'seeds': 15,
       'leechs': 2,
       'file_size': '1.4 GiB'}]),
    ('Tsundere-Raws',
     [{'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 05 VOSTFR (CR) [WEB 1080p x264 AAC].mkv',
       'torrent_url': 'https://nyaa.si/download/1558598.torrent',
       'seeds': 30,
       'leechs': 11,
       'file_size': '1.4 GiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 04 VOSTFR (CR) [WEB 1080p x264 AAC].mkv',
       'torrent_url': 'https://nyaa.si/download/1555575.torrent',
       'seeds': 27,
       'leechs': 0,
       'file_size': '1.4 GiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 03 VOSTFR (CR) [WEB 1080p x264 AAC].mkv',
       'torrent_url': 'https://nyaa.si/download/1552849.torrent',
       'seeds': 21,
       'leechs': 1,
       'file_size': '1.4 GiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 05 VOSTFR (CR) [WEB 1080p x264 AAC].mp4',
       'torrent_url': 'https://nyaa.si/download/1558600.torrent',
       'seeds': 19,
       'leechs': 8,
       'file_size': '1.4 GiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 04 VOSTFR (CR) [WEB 1080p x264 AAC].mp4',
       'torrent_url': 'https://nyaa.si/download/1555578.torrent',
       'seeds': 12,
       'leechs': 2,
       'file_size': '1.4 GiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 05 VOSTFR (CR) [WEB 720p x264 AAC].mp4',
       'torrent_url': 'https://nyaa.si/download/1558599.torrent',
       'seeds': 12,
       'leechs': 10,
       'file_size': '722.2 MiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 05 VOSTFR (CR) [WEB 720p x264 AAC].mkv',
       'torrent_url': 'https://nyaa.si/download/1558597.torrent',
       'seeds': 11,
       'leechs': 5,
       'file_size': '722.1 MiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 04 VOSTFR (CR) [WEB 720p x264 AAC].mp4',
       'torrent_url': 'https://nyaa.si/download/1555576.torrent',
       'seeds': 10,
       'leechs': 0,
       'file_size': '723.0 MiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 03 VOSTFR (CR) [WEB 720p x264 AAC].mkv',
       'torrent_url': 'https://nyaa.si/download/1552848.torrent',
       'seeds': 9,
       'leechs': 0,
       'file_size': '722.5 MiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 03 VOSTFR (CR) [WEB 1080p x264 AAC].mp4',
       'torrent_url': 'https://nyaa.si/download/1552846.torrent',
       'seeds': 8,
       'leechs': 0,
       'file_size': '1.4 GiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 04 VOSTFR (CR) [WEB 720p x264 AAC].mkv',
       'torrent_url': 'https://nyaa.si/download/1555573.torrent',
       'seeds': 8,
       'leechs': 1,
       'file_size': '722.8 MiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu 2 - 03 VOSTFR (CR) [WEB 720p x264 AAC].mp4',
       'torrent_url': 'https://nyaa.si/download/1552845.torrent',
       'seeds': 7,
       'leechs': 0,
       'file_size': '722.7 MiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu S2 - 01 VF (CR) [WEB 720p x264 AAC].mkv',
       'torrent_url': 'https://nyaa.si/download/1555625.torrent',
       'seeds': 2,
       'leechs': 1,
       'file_size': '719.4 MiB'},
      {'filename': '[Tsundere-Raws] Kanojo Okarishimasu S2 - 01 VF (CR) [WEB 1080p x264 AAC].mkv',
       'torrent_url': 'https://nyaa.si/download/1555626.torrent',
       'seeds': 2,
       'leechs': 1,
       'file_size': '1.4 GiB'}]),
    ('CameEsp',
     [{'filename': '[CameEsp] Kanojo, Okarishimasu 2nd Season - 05 [1080p][ESP-LAT-ENG][mkv]',
       'torrent_url': 'https://nyaa.si/download/1558622.torrent',
       'seeds': 13,
       'leechs': 7,
       'file_size': '1.4 GiB'},
      {'filename': '[CameEsp] Kanojo, Okarishimasu 2nd Season - 04 [1080p][ESP-LAT-ENG][mkv]',
       'torrent_url': 'https://nyaa.si/download/1555650.torrent',
       'seeds': 10,
       'leechs': 1,
       'file_size': '1.4 GiB'},
      {'filename': '[CameEsp] Kanojo, Okarishimasu 2nd Season - 03 [1080p][ESP-LAT-ENG][mkv]',
       'torrent_url': 'https://nyaa.si/download/1552914.torrent',
       'seeds': 9,
       'leechs': 1,
       'file_size': '1.4 GiB'},
      {'filename': '[CameEsp] Kanojo, Okarishimasu 2nd Season - 05 [720p][ESP-LAT-ENG][mkv]',
       'torrent_url': 'https://nyaa.si/download/1558623.torrent',
       'seeds': 4,
       'leechs': 4,
       'file_size': '728.8 MiB'},
      {'filename': '[CameEsp] Kanojo, Okarishimasu 2nd Season - 03 [720p][ESP-LAT-ENG][mkv]',
       'torrent_url': 'https://nyaa.si/download/1552915.torrent',
       'seeds': 2,
       'leechs': 2,
       'file_size': '727.6 MiB'},
      {'filename': '[CameEsp] Kanojo, Okarishimasu 2nd Season - 04 [720p][ESP-LAT-ENG][mkv]',
       'torrent_url': 'https://nyaa.si/download/1555651.torrent',
       'seeds': 2,
       'leechs': 2,
       'file_size': '729.5 MiB'}]),
    ('YuiSubs',
     [{'filename': '[YuiSubs] Kanojo, Okarishimasu - 17  (x265 H.265 1080p)',
       'torrent_url': 'https://nyaa.si/download/1558634.torrent',
       'seeds': 17,
       'leechs': 5,
       'file_size': '342.8 MiB'},
      {'filename': '[YuiSubs] Kanojo, Okarishimasu - 15  (x265 H.265 1080p)',
       'torrent_url': 'https://nyaa.si/download/1552831.torrent',
       'seeds': 8,
       'leechs': 0,
       'file_size': '283.9 MiB'},
      {'filename': '[YuiSubs] Kanojo, Okarishimasu - 16  (x265 H.265 1080p)',
       'torrent_url': 'https://nyaa.si/download/1555674.torrent',
       'seeds': 8,
       'leechs': 0,
       'file_size': '273.1 MiB'}]),
    ('DKB',
     [{'filename': '[DKB] Kanojo, Okarishimasu - S02E05 [1080p][HEVC x265 10bit][Multi-Subs][weekly]',
       'torrent_url': 'https://nyaa.si/download/1558639.torrent',
       'seeds': 25,
       'leechs': 15,
       'file_size': '322.7 MiB'},
      {'filename': '[DKB] Kanojo, Okarishimasu - S02E04 [1080p][HEVC x265 10bit][Multi-Subs][weekly]',
       'torrent_url': 'https://nyaa.si/download/1555617.torrent',
       'seeds': 22,
       'leechs': 0,
       'file_size': '255.0 MiB'},
      {'filename': '[DKB] Kanojo, Okarishimasu - S02E03 [1080p][HEVC x265 10bit][Multi-Subs][weekly]',
       'torrent_url': 'https://nyaa.si/download/1552871.torrent',
       'seeds': 10,
       'leechs': 0,
       'file_size': '271.2 MiB'}]),
    ('Raze',
     [{'filename': '[Raze] Kanojo, Okarishimasu - 16 MultiSub x265 10bit 1080p 71.928fps.mkv',
       'torrent_url': 'https://nyaa.si/download/1555685.torrent',
       'seeds': 3,
       'leechs': 0,
       'file_size': '347.6 MiB'},
      {'filename': '[Raze] Kanojo, Okarishimasu - 15 x265 10bit 1080p 144fps.mkv',
       'torrent_url': 'https://nyaa.si/download/1552897.torrent',
       'seeds': 2,
       'leechs': 0,
       'file_size': '1.2 GiB'},
      {'filename': '[Raze] Kanojo, Okarishimasu - 17 x265 10bit 1080p 71.928fps.mkv',
       'torrent_url': 'https://nyaa.si/download/1558642.torrent',
       'seeds': 1,
       'leechs': 2,
       'file_size': '457.1 MiB'}]),
    ('neoHEVC',
     [{'filename': '[neoHEVC] Rent a Girlfriend [Season 1] [BD 1080p x265 HEVC AAC] [Dual Audio]',
       'torrent_url': 'https://nyaa.si/download/1341034.torrent',
       'seeds': 16,
       'leechs': 1,
       'file_size': '3.41GB'}]),
    ('ASW',
     [{'filename': '[ASW] Kanojo, Okarishimasu - 17 [1080p HEVC x265 10Bit][AAC]',
       'torrent_url': 'https://nyaa.si/download/1558633.torrent',
       'seeds': 190,
       'leechs': 91,
       'file_size': '260.0 MiB'},
      {'filename': '[ASW] Kanojo, Okarishimasu - 16 [1080p HEVC x265 10Bit][AAC]',
       'torrent_url': 'https://nyaa.si/download/1555960.torrent',
       'seeds': 70,
       'leechs': 1,
       'file_size': '194.4 MiB'},
      {'filename': '[ASW] Kanojo, Okarishimasu - 15 [1080p HEVC x265 10Bit][AAC]',
       'torrent_url': 'https://nyaa.si/download/1552843.torrent',
       'seeds': 68,
       'leechs': 1,
       'file_size': '212.4 MiB'},
      {'filename': '[ASW] Kanojo, Okarishimasu (Rent-A-Girlfriend) (Season 1) [1080p HEVC x265 10Bit][AAC] (Batch)',
       'torrent_url': 'https://nyaa.si/download/1294205.torrent',
       'seeds': 6,
       'leechs': 0,
       'file_size': '2.3 GiB'}]),
    ('TTGA',
     [{'filename': '[TTGA] Rent-a-Girlfriend (2020) (Season 1) [BDRemux] [1080p Dual Audio FLAC AVC] (Kanojo, Okarishimasu)',
       'torrent_url': 'https://nyaa.si/download/1340556.torrent',
       'seeds': 2,
       'leechs': 4,
       'file_size': '65.1 GiB'}]),
    (None,
     [{'filename': 'Rent-a-Girlfriend Season 2 Episode 1(S01EP13) English Dub 1080p | Kanojo, Okarishimasu Season 1 Episode 13 English Dub',
       'torrent_url': 'https://nyaa.si/download/1552992.torrent',
       'seeds': 19,
       'leechs': 0,
       'file_size': '1.4 GiB'},
      {'filename': 'Kanojo, Okarishimasu - 16 (1920x1080 HEVC2 AAC).mkv',
       'torrent_url': 'http://www.anirena.com/dl/141615',
       'seeds': 7,
       'leechs': 0,
       'file_size': '168.14 MB'},
      {'filename': 'Kanojo, Okarishimasu - 14 (1920x1080 HEVC2 AAC).mkv',
       'torrent_url': 'http://www.anirena.com/dl/140942',
       'seeds': 5,
       'leechs': 0,
       'file_size': '194.92 MB'},
      {'filename': 'Kanojo, Okarishimasu - 15 (1920x1080 HEVC2 AAC).mkv',
       'torrent_url': 'http://www.anirena.com/dl/141350',
       'seeds': 5,
       'leechs': 0,
       'file_size': '182.18 MB'},
      {'filename': 'Kanojo, Okarishimasu - 13 (1920x1080 HEVC2 AAC).mkv',
       'torrent_url': 'http://www.anirena.com/dl/140587',
       'seeds': 3,
       'leechs': 0,
       'file_size': '176.87 MB'},
      {'filename': '【极影字幕社】 ★07月新番 出租女友 Kanokari 第02话 GB 1080P HEVC MP4（字幕社招人内详）',
       'torrent_url': 'https://nyaa.si/download/1263944.torrent',
       'seeds': 0,
       'leechs': 0,
       'file_size': '194.4 MiB'},
      {'filename': '【極影字幕社】 ★07月新番 出租女友 Kanokari 第02話 BIG5 1080P HEVC MP4（字幕社招人內詳）',
       'torrent_url': 'https://nyaa.si/download/1263946.torrent',
       'seeds': 0,
       'leechs': 0,
       'file_size': '194.2 MiB'},
      {'filename': '【极影字幕社】 ★07月新番 租借女友 Kanokari 第01-02话 V2 GB 1080P HEVC MP4（字幕社招人内详）',
       'torrent_url': 'https://nyaa.si/download/1266382.torrent',
       'seeds': 0,
       'leechs': 0,
       'file_size': '354.9 MiB'},
      {'filename': '【极影字幕社】 ★07月新番 出租女友 Kanokari 第01-02话 V2 BIG5 1080P HEVC MP4（字幕社招人内详）',
       'torrent_url': 'https://nyaa.si/download/1266383.torrent',
       'seeds': 0,
       'leechs': 0,
       'file_size': '355.4 MiB'},
      {'filename': '【极影字幕社】 ★07月新番 租借女友 Kanokari 第10话 GB 1080P HEVC MP4 V2（字幕社招人内详）',
       'torrent_url': 'https://nyaa.si/download/1280104.torrent',
       'seeds': 0,
       'leechs': 0,
       'file_size': '177.8 MiB'},
      {'filename': '【极影字幕社】 ★07月新番 租借女友 Kanokari 第11话 GB 1080P HEVC MP4 V2（字幕社招人内详）',
       'torrent_url': 'https://nyaa.si/download/1283149.torrent',
       'seeds': 0,
       'leechs': 0,
       'file_size': '180.6 MiB'}]),
    ('Anime Time',
     [{'filename': '[Anime Time] Kanojo, Okarishimasu (Season 1) [BD][Dual Audio][1080p][HEVC 10bit x265][AAC][Eng Sub] [Batch] (Rental Girlfriend, Rent-A-Girlfriend)',
       'torrent_url': 'https://nyaa.si/download/1408718.torrent',
       'seeds': 30,
       'leechs': 5,
       'file_size': '2.9 GiB'},
      {'filename': '[Anime Time] Kanojo, Okarishimasu Season 2 - 02 [1080p][HEVC 10bit x265][AAC][Multi Sub] [Weekly] Rent-A-Girlfriend',
       'torrent_url': 'https://nyaa.si/download/1550554.torrent',
       'seeds': 21,
       'leechs': 0,
       'file_size': '264.9 MiB'},
      {'filename': '[Anime Time] Kanojo, Okarishimasu Season 2 - 04 [1080p][HEVC 10bit x265][AAC][Multi Sub] [Weekly] Rent-A-Girlfriend',
       'torrent_url': 'https://nyaa.si/download/1556610.torrent',
       'seeds': 21,
       'leechs': 0,
       'file_size': '224.8 MiB'},
      {'filename': '[Anime Time] Kanojo, Okarishimasu Season 2 - 03 [1080p][HEVC 10bit x265][AAC][Multi Sub] [Weekly] Rent-A-Girlfriend',
       'torrent_url': 'https://nyaa.si/download/1553125.torrent',
       'seeds': 18,
       'leechs': 0,
       'file_size': '241.5 MiB'},
      {'filename': '[Anime Time] Kanojo, Okarishimasu Season 2 - 01 [1080p][HEVC 10bit x265][AAC][Multi Sub] [Weekly] Rent-A-Girlfriend',
       'torrent_url': 'https://nyaa.si/download/1547991.torrent',
       'seeds': 16,
       'leechs': 0,
       'file_size': '231.4 MiB'},
      {'filename': '[Anime Time] Kanojo, Okarishimasu (Rental Girlfriend, Rent-A-Girlfriend) Season 1 [1080p][HEVC 10bit x265][AAC][Multi Sub]',
       'torrent_url': 'https://nyaa.si/download/1284082.torrent',
       'seeds': 2,
       'leechs': 0,
       'file_size': '2.9 GiB'}]),
    ('SSA',
     [{'filename': '[SSA] Kanojo, Okarishimasu Season 1 [720p][Batch]',
       'torrent_url': 'http://www.anirena.com/dl/104626',
       'seeds': 0,
       'leechs': 1,
       'file_size': '1.07 GB'}]),
    ('Judas',
     [{'filename': '[Judas] Kanojo, Okarishimasu (Rent-A-Girlfriend) (Season 1) [1080p][HEVC x265 10bit][Multi-Subs] (Batch)',
       'torrent_url': 'https://nyaa.si/download/1283971.torrent',
       'seeds': 67,
       'leechs': 4,
       'file_size': '3.5 GiB'},
      {'filename': '[Judas] Kanojo, Okarishimasu (Rent-A-Girlfriend) - S02E04 [1080p][HEVC x265 10bit][Multi-Subs] (Weekly)',
       'torrent_url': 'https://nyaa.si/download/1555755.torrent',
       'seeds': 52,
       'leechs': 0,
       'file_size': '195.2 MiB'},
      {'filename': '[Judas] Kanojo, Okarishimasu (Rent-A-Girlfriend) - S02E03 [1080p][HEVC x265 10bit][Multi-Subs] (Weekly)',
       'torrent_url': 'https://nyaa.si/download/1552945.torrent',
       'seeds': 41,
       'leechs': 1,
       'file_size': '210.3 MiB'}]),
    ('EMBER',
     [{'filename': '[EMBER] Kanojo, Okarishimasu S02E04 [1080p] [HEVC WEBRip] (Rent-a-Girlfriend 2nd Season)',
       'torrent_url': 'https://nyaa.si/download/1555599.torrent',
       'seeds': 216,
       'leechs': 3,
       'file_size': '306.9 MiB'},
      {'filename': '[EMBER] Kanojo, Okarishimasu S02E03 [1080p] [HEVC WEBRip] (Rent-a-Girlfriend 2nd Season)',
       'torrent_url': 'https://nyaa.si/download/1552870.torrent',
       'seeds': 120,
       'leechs': 2,
       'file_size': '315.7 MiB'},
      {'filename': '[EMBER] Kanojo, Okarishimasu S02E01 [1080p] [HEVC WEBRip] (Rent-a-Girlfriend 2nd Season)',
       'torrent_url': 'https://nyaa.si/download/1547924.torrent',
       'seeds': 111,
       'leechs': 1,
       'file_size': '256.8 MiB'},
      {'filename': '[EMBER] Kanojo, Okarishimasu S02E02 [1080p] [HEVC WEBRip] (Rent-a-Girlfriend 2nd Season)',
       'torrent_url': 'https://nyaa.si/download/1550314.torrent',
       'seeds': 110,
       'leechs': 2,
       'file_size': '297.7 MiB'},
      {'filename': '[EMBER] Rent-a-Girlfriend (2020) (Season 1) [BDRip] [1080p Dual Audio HEVC 10 bits] (Kanojo, Okarishimasu) V3',
       'torrent_url': 'https://nyaa.si/download/1341307.torrent',
       'seeds': 21,
       'leechs': 0,
       'file_size': '5.0 GiB'},
      {'filename': '[EMBER] Kanojo, Okarishimasu (2020) (Season 1) [1080p] [Dual Audio HEVC WEBRip] (Rent-a-Girlfriend)',
       'torrent_url': 'https://nyaa.si/download/1302076.torrent',
       'seeds': 2,
       'leechs': 0,
       'file_size': '3.2 GiB'},
      {'filename': '[EMBER] Kanojo, Okarishimasu (2020) (Season 1) [1080p] [HEVC WEBRip] (Rent-a-Girlfriend)',
       'torrent_url': 'https://nyaa.si/download/1283919.torrent',
       'seeds': 1,
       'leechs': 1,
       'file_size': '2.9 GiB'}]),
    ('Erai-raws',
     [{'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 05 [1080p][Multiple Subtitle] [US][BR][MX][ES][SA][FR][DE][IT][RU]',
       'torrent_url': 'https://nyaa.si/download/1558587.torrent',
       'seeds': 199,
       'leechs': 38,
       'file_size': '1.4 GiB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 05 [1080p][Multiple Subtitle][60817483]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2005%20%5B1080p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 184,
       'leechs': 54,
       'file_size': '1.39GB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 04 [1080p][Multiple Subtitle][7E04599E]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2004%20%5B1080p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 121,
       'leechs': 1,
       'file_size': '1.39GB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 05 [720p][Multiple Subtitle][47DDB2CC]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2005%20%5B720p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 89,
       'leechs': 23,
       'file_size': '729.06MB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 05 [720p][Multiple Subtitle] [US][BR][MX][ES][SA][FR][DE][IT][RU]',
       'torrent_url': 'https://nyaa.si/download/1558590.torrent',
       'seeds': 81,
       'leechs': 16,
       'file_size': '729.1 MiB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 03 [1080p][Multiple Subtitle][AACFA783].mkv',
       'torrent_url': 'https://nyaa.si/download/1552802.torrent',
       'seeds': 79,
       'leechs': 2,
       'file_size': '1.4 GiB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 01 [1080p][Multiple Subtitle][08CDF911]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2001%20%5B1080p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 68,
       'leechs': 0,
       'file_size': '1.39GB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 02 [1080p][Multiple Subtitle][44FB0A31]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2002%20%5B1080p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 53,
       'leechs': 0,
       'file_size': '1.39GB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 04 [720p][Multiple Subtitle][A803AF0C]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2004%20%5B720p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 46,
       'leechs': 0,
       'file_size': '729.84MB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 04 [1080p][HEVC][Multiple Subtitle][E5C742A5]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2004%20%5B1080p%5D%5BHEVC%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 43,
       'leechs': 0,
       'file_size': '373.58MB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 03 [1080p][HEVC][Multiple Subtitle][DB7883A9]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2003%20%5B1080p%5D%5BHEVC%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 37,
       'leechs': 0,
       'file_size': '404.89MB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 02 [1080p][HEVC][Multiple Subtitle][B76F8CA0]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2002%20%5B1080p%5D%5BHEVC%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 33,
       'leechs': 0,
       'file_size': '617.6MB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 01 [1080p][HEVC][Multiple Subtitle][E671BE72]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2001%20%5B1080p%5D%5BHEVC%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 32,
       'leechs': 0,
       'file_size': '530.16MB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 03 [720p][Multiple Subtitle][34DD9400].mkv',
       'torrent_url': 'https://nyaa.si/download/1552803.torrent',
       'seeds': 31,
       'leechs': 0,
       'file_size': '729.4 MiB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 05 [480p][Multiple Subtitle][D9CDDF18]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2005%20%5B480p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 30,
       'leechs': 7,
       'file_size': '373.99MB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 05 [480p][Multiple Subtitle] [US][BR][MX][ES][SA][FR][DE][IT][RU]',
       'torrent_url': 'https://nyaa.si/download/1558592.torrent',
       'seeds': 29,
       'leechs': 6,
       'file_size': '374.0 MiB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 02 [720p][Multiple Subtitle][DFB9DF86]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2002%20%5B720p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 27,
       'leechs': 0,
       'file_size': '729.49MB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 01 [720p][Multiple Subtitle][D18A392C]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2001%20%5B720p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 25,
       'leechs': 0,
       'file_size': '726.89MB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 04 [480p][Multiple Subtitle][B3DAD843].mkv',
       'torrent_url': 'https://nyaa.si/download/1555557.torrent',
       'seeds': 12,
       'leechs': 0,
       'file_size': '374.4 MiB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 03 [480p][Multiple Subtitle][E6F9633E].mkv',
       'torrent_url': 'https://nyaa.si/download/1552804.torrent',
       'seeds': 8,
       'leechs': 0,
       'file_size': '374.1 MiB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 01 [480p][Multiple Subtitle][A164E9B4]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2001%20%5B480p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 4,
       'leechs': 0,
       'file_size': '373.59MB'},
      {'filename': '[Erai-raws] Kanojo Okarishimasu 2nd Season - 02 [480p][Multiple Subtitle][C59B46EF]. mkv',
       'torrent_url': 'https://ddl.erai-raws.info/Torrent/2022/Summer/Kanojo%20Okarishimasu%202nd%20Season/%5BErai-raws%5D%20Kanojo%20Okarishimasu%202nd%20Season%20-%2002%20%5B480p%5D%5BMultiple%20Subtitle%5D.mkv.torrent',
       'seeds': 4,
       'leechs': 0,
       'file_size': '373.44MB'}])]

def filename_slug(f):
    # Format a filename to increase matchs
    return f.lower().replace(' ', '')

def get_publisher(filename):
    # Try to get a publisher name from a filename

    # '[publisher name]torrent name.torrent'
    publisher_pattern = r'^\[(.*?)\]+'

    result = re.findall(publisher_pattern, filename)
    if len(result) >= 1:
        return result[0]
    else:
        return None

def key_topPublishers(k):
    # Bring best publishers to the top of the list
    topPublishers = [
            "SubsPlease",
            "EMBER",
            "Judas",
            "HorribleSubs",
            "SSA",
            "LostYears",
            "HorribleRips",
            "Erai-raws"
        ]
    if k[0] in topPublishers:
        return len(topPublishers) - topPublishers.index(k[0])
    else:
        return 0

def key_dualAudio(k):
    # Try to guess if torrent has dual audio
    marked = ('dual', 'dub') # TODO - Shouldn't be hardcoded
    for mark in marked:
        for title in k[1]:
            if mark in title['filename'].lower():
                return 1

    return 0

keys = (
    (key_topPublishers, True),
    (key_dualAudio, True), # Bring torrents with dual audio to the top
    (lambda k: max((t['seeds'] for t in k[1])) if k[1] else -1, True), # Sort by seeds
)
publishers = SortedDict(keys=keys)

def add_torrent(torrent):
    filename = torrent['filename']
    # Look for publisher name
    publisher = get_publisher(filename)

    if publisher in publishers:
        # Do not add file if it has already been found with more seeds
        file_hash = filename_slug(filename)

        for i, tmp_torrent in enumerate(publishers[publisher]):
            if file_hash == filename_slug(tmp_torrent['filename']):
                # Replace torrent if it has more seeds
                if torrent['seeds'] > tmp_torrent['seeds']:
                    publishers[publisher][i] = torrent

        else:
            # Should run if the loop wasn't broken
            # Add torrent to list
            publishers[publisher].append(torrent)

    else:
        # Insert new publisher
        publishers[publisher] = SortedList(
            keys=((itemgetter('seeds'), True),))
        publishers[publisher].append(torrent)

for publisher, torrents in data:
    for torrent in torrents:
        add_torrent(torrent)

print(' / '.join(map(lambda e: str(e[0]+1) + ': ' + str(e[1]), enumerate(publishers.keys()))))

exit()

db = Getters.getDatabase()

qb = Client("http://localhost:8080", REQUESTS_ARGS={'timeout': 2})
qb.auth_log_in("admin", "1234567")

data = db.sql('SELECT * FROM animeRelations')
seen = set()

keys = ('id',
        'type',
        'name',
        'rel_id')

for rel in data:
    if rel in seen:
        db.sql(
            'DELETE FROM animeRelations WHERE id=? AND type=? AND name=? AND rel_id=?', rel)
    else:
        seen.add(rel)


def send_animes():
    for i, anime in enumerate(db.sql("SELECT * FROM anime WHERE tag IS NOT null;", to_dict=True)):
        anime = Anime(anime)

        def format_keys(key):
            key = str(key)
            if key in ('status',
                       'like'):
                key = "has_" + key
            return key

        def format_values(val):
            if type(val) != str:
                val = str(val)
            if "\\" in val:
                val = val.replace("\\", "/")
            return val

        url = "http://animemanager/add_anime.php?" + '&'.join(format_keys(k) + "=" + format_values(
            v) for k, v in anime.items() if k not in anime.metadata_keys and v is not None)

        if anime['tag'] == "WATCHING":
            print(f"\n{url} -- {anime['tag']}\n")

        a = requests.get(url)
        print(i, anime['title'])
        for line in a.content.split(b"<br/>"):
            print(re.sub(b'<.*>', b'', line))
        # time.sleep(1)


for anime in db.sql('SELECT * FROM anime WHERE broadcast IS NOT null', to_dict=True):
    anime = Anime(anime)
    b = anime.broadcast

    weekday, hour, min = b.split('-')

    print(anime.id, anime.title, anime.broadcast, weekday, hour, min)
    db.sql('INSERT INTO broadcasts(id, weekday, hour, minute) VALUES (?, ?, ?, ?)',
           (anime.id, weekday, hour, min))

db.save()
