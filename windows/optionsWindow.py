import os
import json
import threading
import re
import subprocess
import queue
import time

from operator import itemgetter
from datetime import date, datetime, timedelta, time as datetime_time
from sqlite3 import OperationalError
from tkinter import *
from tkinter.ttk import Progressbar

import qbittorrentapi.exceptions

import utils
from playerManager import MpvPlayer


class optionsWindow:
    def optionsWindow(self, id):
        # Functions
        if True:
            def findTorrent(id):
                if self.getQB() == "OK":
                    database = self.getDatabase()

                    torrents = database.sql(
                        "SELECT torrent FROM anime WHERE id = ?", (id,))[0]
                    if len(torrents) is not None:
                        torrents = torrents[0]
                    torrents = json.loads(
                        torrents) if torrents is not None else []
                    target = None

                    if torrents == []:
                        return

                    torrent_hashes = []
                    for t in torrents:
                        path = os.path.join(self.torrentPath, t)
                        if os.path.exists(path):
                            torrent_hash = self.getTorrentHash(path)
                            torrent_hashes.append(torrent_hash)
                    try:
                        qbtorrents = self.qb.torrents_info(
                            status_filter="downloading", torrent_hashes="|".join(torrent_hashes))
                    except qbittorrentapi.exceptions.APIConnectionError:
                        self.log('MAIN_STATE',
                                 '[ERROR] - Error while connecting to torrent client')
                    else:
                        if len(qbtorrents) > 0:
                            self.choice.hash = qbtorrents[0].hash
                            self.choice.after(
                                1, lambda id=id: self.reload(id, False))
                    # return target

            def updateLoadingBar(id, bar, text):
                hash = self.choice.hash
                try:
                    torrent = self.qb.torrents_properties(hash)
                except qbittorrentapi.exceptions.NotFound404Error:
                    value = 100
                except qbittorrentapi.exceptions.APIConnectionError:
                    self.log("NETWORK", "[ERROR] - Couldn't find the torrent client!")
                    value = 100
                else:
                    value = torrent.pieces_have / torrent.pieces_num * 100
                if value == 100:
                    del self.choice.hash
                    self.reload(id, update=False)
                else:
                    try:
                        bar['value'] = value
                        text.configure(text=str(round(value, 2)) + "%")
                        self.choice.update()
                    except BaseException:
                        pass
                    self.choice.after(
                        500,
                        lambda id=id,
                        bar=bar,
                        hash=hash: updateLoadingBar(
                            id,
                            bar,
                            text))

            def colorFileEntries(id, eps, epsList):
                last_seen = self.database(id=id, table="anime")['last_seen']
                if len(eps) >= 1 and list(eps)[0] is not None:
                    pathList = [os.path.normpath(i['path']) for i in eps]
                else:
                    pathList = []
                if last_seen is not None and os.path.normpath(last_seen) in pathList:
                    for i in range(pathList.index(os.path.normpath(last_seen)) + 1):
                        epsList['menu'].entryconfig(
                            i, foreground=self.colors['Green'])

            def tag(id, tag):
                self.database.set({'id': id, 'tag': tag}, table='tag')

                for lbl in self.scrollable_frame.winfo_children():
                    if lbl.winfo_class() == 'Label' and lbl.name == str(id):
                        lbl.configure(fg=self.colors[self.tagcolors[tag]])
                        break
                self.reload(id, False)

            def like(id, b):
                d = self.database(id=id, table='like')
                liked = self.database.exist(id=id, table='like') and bool(d['like'])
                self.database.set({'id': id, 'like': not liked}, table='like')

                if not liked:
                    im_path = os.path.join(self.iconPath, "heart.png")
                else:
                    im_path = os.path.join(self.iconPath, "heart(1).png")

                folder = self.getFolder(id)
                showFolderButtons = folder is not None and os.path.isdir(
                    os.path.join(self.animePath, folder))

                iconSize = (50, 50) if showFolderButtons else (30, 30)
                image = self.getImage(im_path, iconSize)
                b.configure(image=image)
                b.image = image
                b.update()

                for lbl in self.scrollable_frame.winfo_children():
                    if lbl.winfo_class() == 'Label' and lbl.name == str(id):
                        text = lbl.cget("text").replace(" ❤", "")
                        if not liked:
                            text += " ❤"
                        lbl['text'] = text
                        lbl.update()
                        break

            def watch(e, eps, var):
                var.set("Watch")
                video = [i['title'] for i in eps].index(e)
                playlist = [i['path'] for i in eps]
                self.log('MAIN_STATE', "Watching", e)
                # threading.Thread(target=MpvPlayer, args=(self.root, playlist, video, id, self.dbPath)).start()
                MpvPlayer(playlist, video, id, self.dbPath)

            def openEps(e, eps, var):
                var.set("Watch")
                playlist = [os.path.normpath(i['path']) for i in eps.values()]
                folder = os.path.dirname(playlist[0])
                self.log('MAIN_STATE', "Opening", len(playlist), "files")
                subprocess.call(
                    [os.path.normpath("C:/Program Files/VideoLAN/VLC/vlc.exe"), folder])

            def ddlFromUrl(id):
                def callback(var, id):
                    url = var.get()
                    self.downloadFile(id, url=url)
                self.textPopupWindow(
                    self.choice,
                    "Enter torrent url",
                    lambda var,
                    id=id: callback(
                        var,
                        id),
                    fentype="TEXT")

            def trailer(id):
                data = self.database(id=id, table="anime")
                trailer = anime.trailer
                if trailer is not None:
                    self.log('MAIN_STATE', "Watching trailer for anime",
                             anime.title, "url", trailer)
                    # threading.Thread(target=MpvPlayer, args=((trailer,), 0, None, None, True)).start()
                    MpvPlayer((trailer,), 0, url=True)

            def getDateText(datefrom, dateto, broadcast):
                today = date.today()
                delta = today - datefrom  # - timedelta(days=1)
                if status == 'FINISHED':
                    if dateto is None:
                        datetext = "Published on {}".format(
                            datefrom.strftime("%d %b %Y"))
                    else:
                        datetext = "From {} to {} ({} days)".format(
                            datefrom.strftime("%d %b %Y"), dateto.strftime("%d %b %Y"), delta.days)
                elif status == 'AIRING':
                    datetext = "Since {} ({} days)".format(
                        datefrom.strftime("%d %b %Y"), delta.days)
                    # ,'Unknown','Not scheduled once per week'):
                    if broadcast is not None:
                        weekday, hour, minute = map(int, broadcast.split("-"))

                        daysLeft = (weekday - today.weekday()) % 7
                        dateObj = datetime.today() + timedelta(days=daysLeft)

                        # Depends on timezone - TODO
                        hourDateObj = timedelta(hours=hour - 5, minutes=minute)
                        dateObj = datetime.combine(
                            dateObj.date(), datetime_time.min) + hourDateObj
                        text = dateObj.strftime(
                            "Next episode on %a %d at %H:%M")
                        datetext += "\n{}".format(text)

                        daysSince = (today.weekday() - weekday) % 7
                        text = "Last episode: {}"
                        if daysSince == 0:
                            text = text.format("Today")
                        elif daysSince == 1:
                            text = text.format("Yesterday")
                        elif daysSince > 1:
                            text = text.format(str(daysSince) + " days ago")
                        else:
                            text = text.format("uhh?")
                        datetext += "\n{}".format(text)
                    else:
                        daysSince = ((delta.days - 1) % 7)
                        dateObj = date.today() - timedelta(days=daysSince)
                        text = dateObj.strftime("Last episode on %a %d ({})")
                        if daysSince == 0:
                            text = text.format("Today")
                        elif daysSince == 1:
                            text = text.format("Yesterday")
                        elif daysSince > 1:
                            text = text.format(str(daysSince) + " days ago")
                        else:
                            text = text.format("uhh?")
                        datetext += "\n{}".format(text)

                elif status == 'UPCOMING':
                    datetext = "On {} ({} days left)".format(
                        datefrom.strftime("%d %b %Y"), -delta.days)
                return datetext

            def switch(id, titles=None):
                if titles is not None:
                    id = titles[id]
                self.choice.clear()
                self.optionsWindow(id)

            def dataUpdate(id):
                database = self.getDatabase()
                data = self.api.anime(id)

                database.set(data, table="anime")
                if 'status' in data.keys() and data.status != 'UPDATE':
                    self.choice.after(1, lambda id=id: self.reload(id))

        # Window init - Fancy corners - Main frame
        if True:
            anime = self.database(id=id, table="anime")

            if not self.database.exist(id=id, table="anime") or anime.status == 'UPDATE':
                threading.Thread(target=dataUpdate, args=(id,), daemon=True).start()
                anime.title = "Loading..."

            if self.choice is None or not self.choice.winfo_exists():
                size = (self.infoWindowMinWidth, self.infoWindowMinHeight)
                self.choice = utils.RoundTopLevel(
                    self.fen,
                    title=anime.title,
                    minsize=size,
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray3'])
                self.choice.titleLbl.configure(
                    fg=self.colors[self.tagcolors[self.database(id=id, table='tag')['tag']]])
            else:
                self.choice.clear()
                self.choice.titleLbl.configure(text=anime.title,
                                               bg=self.colors['Gray2'],
                                               fg=self.colors[self.tagcolors[self.database(id=id,
                                                                                           table='tag')['tag']]],
                                               font=("Source Code Pro Medium",
                                                     15))

        # Title - File buttons
        if True:
            titleFrame = Frame(self.choice, bg=self.colors['Gray2'])

            if 'hash' in self.choice.__dict__.keys():
                offRow = 1
                bar = Progressbar(
                    titleFrame, orient=HORIZONTAL, mode='determinate')
                bar.grid(row=0, column=0, columnspan=2,
                         sticky="nsew", padx=2, pady=2)
                text = Label(
                    titleFrame,
                    text="0%",
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray4'],
                    font=(
                        "Source Code Pro Medium",
                        15))
                text.grid(row=0, column=2, padx=10)

                # self.choice.hash = torrent['hash']
                updateLoadingBar(id, bar, text)
            else:
                offRow = 0
            b = Button(
                titleFrame,
                text="Download torrents",
                bd=0,
                height=1,
                relief='solid',
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['White'],
                bg=self.colors['Gray3'],
                fg=self.colors['White'],
                command=lambda id=id: self.ddlWindow(id))
            b.bind("<Button-3>", lambda e, id=id: ddlFromUrl(id))
            b.grid(row=1 + offRow, column=0, sticky="nsew", padx=2, pady=2)

            Button(
                titleFrame,
                text="Manage torrents",
                bd=0,
                height=1,
                relief='solid',
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['White'],
                bg=self.colors['Gray3'],
                fg=self.colors['White'],
                command=lambda id=id: self.torrentFilesWindow(id)
            ).grid(
                row=1 + offRow,
                column=1,
                sticky="nsew",
                padx=2,
                pady=2)

            offCol = 0
            folder = self.getFolder(id)
            showFolderButtons = folder is not None and os.path.isdir(
                os.path.join(self.animePath, folder))
            if showFolderButtons:
                Button(
                    titleFrame,
                    text="Open folder",
                    bd=0,
                    height=1,
                    relief='solid',
                    font=(
                        "Source Code Pro Medium",
                        13),
                    activebackground=self.colors['Gray2'],
                    activeforeground=self.colors['White'],
                    bg=self.colors['Gray3'],
                    fg=self.colors['White'],
                    command=lambda folder=folder: os.system(
                        'explorer "{}"'.format(
                            os.path.normpath(
                                os.path.join(
                                    self.animePath,
                                    folder))))).grid(
                    row=2 + offRow,
                    column=0,
                    sticky="nsew",
                    padx=2,
                    pady=2)

                eps = self.getEpisodes(folder)
                if len(eps) >= 1 and list(eps)[0] is not None:
                    titles = [e['title'] for e in eps]
                    state = "normal"
                else:
                    titles = (None,)
                    state = "disabled"

                var = StringVar()
                var.set("Watch")
                epsList = OptionMenu(
                    titleFrame,
                    var,
                    *titles,
                    command=lambda e,
                    var=var: watch(
                        e,
                        eps,
                        var))
                epsList.configure(
                    state=state,
                    indicatoron=False,
                    highlightthickness=0,
                    borderwidth=0,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    activebackground=self.colors['Gray3'],
                    activeforeground=self.colors['White'],
                    bg=self.colors['Gray3'],
                    fg=self.colors['White'])
                epsList["menu"].configure(
                    bd=0,
                    borderwidth=0,
                    activeborderwidth=0,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    activebackground=self.colors['Gray3'],
                    activeforeground=self.colors['White'],
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'],
                )
                epsList.grid(row=2 + offRow, column=1,
                             sticky="nsew", padx=2, pady=2)

                colorFileEntries(id, eps, epsList)
                epsList.bind("<Button-3>", lambda e,
                             var=var: openEps(e, eps, var))
                epsList.bind("<Button-1>", lambda e, a=id, b=eps, c=epsList: colorFileEntries(a, b, c))

            [titleFrame.grid_columnconfigure(i, weight=1) for i in range(2)]

            iconSize = (50, 50) if showFolderButtons else (30, 30)
            if self.database.exist(id=id, table='like') and bool(
                    self.database(id=id, table='like')['like']):
                image = self.getImage(
                    os.path.join(
                        self.iconPath,
                        "heart.png"),
                    iconSize)
            else:
                image = self.getImage(
                    os.path.join(
                        self.iconPath,
                        "heart(1).png"),
                    iconSize)
            likeButton = Button(
                titleFrame,
                image=image,
                bd=0,
                relief='solid',
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['White'],
                bg=self.colors['Gray2'],
                fg=self.colors['White'],
            )
            likeButton.configure(command=lambda id=id,
                                 b=likeButton: like(id, b))
            likeButton.image = image
            likeButton.grid(row=1 + offRow, column=2,
                            rowspan=2, sticky="nsew", padx=5)
            titleFrame.grid(row=0, column=0, sticky="nsew")

        # Tags
        if True:
            tags = Frame(self.choice, bg=self.colors['Gray2'])
            Label(
                tags,
                text="Tag as:",
                bg=self.colors['Gray2'],
                fg=self.colors['Gray4'],
                font=(
                    "Source Code Pro Medium",
                    15)).grid(
                row=0,
                column=0,
                pady=10)
            Button(
                tags,
                text="Seen",
                bd=0,
                height=1,
                relief='solid',
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['Green'],
                bg=self.colors['Gray2'],
                fg=self.colors['Green'],
                command=lambda id=id: tag(
                    id,
                    'SEEN')).grid(
                row=0,
                column=1,
                sticky="nsew",
                padx=5)
            Button(
                tags,
                text="Watching",
                bd=0,
                height=1,
                relief='solid',
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['Orange'],
                bg=self.colors['Gray2'],
                fg=self.colors['Orange'],
                command=lambda id=id: tag(
                    id,
                    'WATCHING')).grid(
                row=0,
                column=2,
                sticky="nsew",
                padx=5)
            Button(
                tags,
                text="To the Watchlist",
                bd=0,
                height=1,
                relief='solid',
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['White'],
                bg=self.colors['Gray2'],
                fg=self.colors['Blue'],
                command=lambda id=id: tag(
                    id,
                    'WATCHLIST')).grid(
                row=0,
                column=3,
                sticky="nsew",
                padx=5)
            Button(
                tags,
                text="None",
                bd=0,
                height=1,
                relief='solid',
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['White'],
                bg=self.colors['Gray2'],
                fg=self.colors['White'],
                command=lambda id=id: tag(
                    id,
                    'NONE')).grid(
                row=0,
                column=4,
                sticky="nsew",
                padx=5)
            if anime.trailer is not None:
                Label(
                    tags,
                    text="-",
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray4'],
                    font=(
                        "Source Code Pro Medium",
                        13)).grid(
                    row=0,
                    column=5,
                    pady=5)
                Button(
                    tags,
                    text="Watch trailer",
                    bd=0,
                    height=1,
                    relief='solid',
                    font=(
                        "Source Code Pro Medium",
                        13),
                    activebackground=self.colors['Gray2'],
                    activeforeground=self.colors['White'],
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'],
                    command=lambda id=id: trailer(id)).grid(
                    row=0,
                    column=6,
                    sticky="nsew",
                    padx=5)
            tags.grid(row=3, column=0)

        # Synopsis
        if True:
            if anime.synopsis not in ('', None):
                synopsis = Label(
                    self.choice,
                    text=anime.synopsis,
                    wraplength=900,
                    font=(
                        "Source Code Pro Medium",
                        10),
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'])
            else:
                synopsis = Label(
                    self.choice,
                    text="No synopsis",
                    wraplength=900,
                    font=(
                        "Source Code Pro Medium",
                        10),
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'])
            synopsis.grid(row=4, column=0)

        # Secondary infos
        if True:
            secondInfos = Frame(self.choice, bg=self.colors['Gray2'])
            if anime.episodes is not None:
                text = str(anime.episodes) + \
                    " episode{}".format("s" if anime.episodes > 1 else "")
                episodes = Label(
                    secondInfos,
                    text=text,
                    font=(
                        "Source Code Pro Medium",
                        10),
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'])
            else:
                episodes = Label(
                    secondInfos,
                    text="No episodes",
                    font=(
                        "Source Code Pro Medium",
                        10),
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'])
            if anime.rating is not None and anime.rating != 'None':
                rating = Label(
                    secondInfos,
                    text="Rating: " + anime.rating,
                    font=(
                        "Source Code Pro Medium",
                        10),
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'])
            else:
                rating = Label(
                    secondInfos,
                    text="No rating",
                    font=(
                        "Source Code Pro Medium",
                        10),
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'])
            if anime.duration not in (None, 'None', 'Unknown'):
                text = "(" + str(anime.duration) + " min{})".format(
                    " each" if anime.episodes is not None and anime.episodes > 1 else "")
                duration = Label(
                    secondInfos,
                    text=text,
                    font=(
                        "Source Code Pro Medium",
                        10),
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'])
            else:
                duration = Label(
                    secondInfos,
                    text="(Unknown duration)",
                    font=(
                        "Source Code Pro Medium",
                        10),
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'])

            rating.grid(row=0, column=0)
            Label(
                secondInfos,
                text="-",
                font=(
                    "Source Code Pro Medium",
                    10),
                bg=self.colors['Gray2'],
                fg=self.colors['White']).grid(
                row=0,
                column=1)
            episodes.grid(row=0, column=2)
            duration.grid(row=0, column=3)
            secondInfos.grid(row=5, column=0)

        # Genres
        if True:
            genresFrame = Frame(self.choice, bg=self.colors['Gray2'])
            genres = anime.genres
            if genres is not None:
                genres = json.loads(anime.genres)
            else:
                genres = []

            all_genres = dict(self.database.sql("SELECT id, name FROM genres"))

            for genre_id in genres:
                txt = all_genres[genre_id]
                if txt == "NONE":
                    txt = "Unknown"
                Label(
                    genresFrame,
                    text=txt,
                    bd=0,
                    height=1,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray'],
                ).pack(
                    side="left")
                lbl = Label(
                    genresFrame,
                    text=" - ",
                    bd=0,
                    height=1,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray'],
                )
                lbl.pack(side="left")
            if len(genres) >= 1:
                lbl.pack_forget()
            genresFrame.grid(row=6, column=0, pady=10)

        # Relations
        if True:
            relationsFrame = Frame(self.choice, bg=self.colors['Gray2'])
            relations = self.database.sql(
                "SELECT * FROM related WHERE id=?", (id,))
            column = 0
            relations.sort(key=itemgetter(1))
            for relation in relations:
                rel_ids = json.loads(relation[2])
                sql = "SELECT title,id FROM anime WHERE id IN (?" + ",?" * (
                    len(rel_ids) - 1) + ");"
                titles = dict(self.database.sql(sql, rel_ids))
                text = relation[1].capitalize().replace("_", " ")
                if len(titles) == 1:
                    Button(relationsFrame,
                           text=text,
                           bd=0,
                           height=1,
                           relief='solid',
                           font=("Source Code Pro Medium",
                                 13),
                           activebackground=self.colors['Gray2'],
                           activeforeground=self.colors['Red'],
                           bg=self.colors['Gray2'],
                           fg=self.colors[self.tagcolors[self.database(id=rel_ids[0], table='tag')['tag']]],
                           command=lambda ids=rel_ids: switch(ids[0])).grid(row=0,
                                                                            column=column)
                elif len(titles) > 1:
                    var = StringVar()
                    var.set(text)
                    # if len(titles) == 1:
                    epsList = OptionMenu(
                        relationsFrame,
                        var,
                        *titles.keys(),
                        command=lambda e,
                        titles=titles: switch(
                            e,
                            titles))
                    epsList.configure(
                        indicatoron=False,
                        highlightthickness=0,
                        borderwidth=0,
                        font=(
                            "Source Code Pro Medium",
                            13),
                        activebackground=self.colors['Gray2'],
                        activeforeground=self.colors['White'],
                        bg=self.colors['Gray2'],
                        fg=self.colors['White'])
                    epsList["menu"].configure(
                        bd=0,
                        borderwidth=0,
                        activeborderwidth=0,
                        font=(
                            "Source Code Pro Medium",
                            13),
                        activebackground=self.colors['Gray3'],
                        activeforeground=self.colors['White'],
                        bg=self.colors['Gray2'],
                        fg=self.colors['White'],
                    )
                    epsList.grid(row=0, column=column)

                    for i, rel_id in enumerate(rel_ids):
                        epsList['menu'].entryconfig(
                            i, foreground=self.colors[self.tagcolors[self.database(id=rel_id, table="tag")['tag']]])
                else:
                    self.log("ERROR", "id:{}, rel_ids:{}, titles:{}".format(
                        str(id), str(rel_ids), str(titles)))
                    # raise Exception("ERROR - id:{}, rel_ids:{}, titles:{}".format(str(id),str(rel_ids),str(titles)))

                if len(titles) > 0:
                    column += 1
                    lbl = Label(
                        relationsFrame,
                        text="-",
                        bd=0,
                        height=1,
                        font=(
                            "Source Code Pro Medium",
                            13),
                        bg=self.colors['Gray2'],
                        fg=self.colors['Gray'],
                    )
                    lbl.grid(row=0, column=column)
                    column += 1

            if column > 0:
                lbl.grid_forget()

            relationsFrame.grid(row=7, column=0)

        # State
        if True:
            state = Frame(self.choice, bg=self.colors['Gray2'])
            datefrom, dateto = anime.date_from, anime.date_to
            if datefrom is not None:
                datefrom = date.fromisoformat(datefrom)
            if dateto is not None:
                dateto = date.fromisoformat(dateto)

            status = self.getStatus(anime)
            Label(
                state,
                text="Status:",
                bg=self.colors['Gray2'],
                fg=self.colors['Gray4'],
                font=(
                    "Source Code Pro Medium",
                    15)).grid(
                row=0,
                column=0,
                sticky="e")
            statusLbl = Label(state,
                              text=self.dateStates[status]['text'],
                              bg=self.colors['Gray2'],
                              fg=self.colors[self.dateStates[status]['color']],
                              font=("Source Code Pro Medium",
                                    13))
            statusLbl.grid(row=0, column=1, sticky="w")
            dateLbl = Label(state,
                            text="",
                            bg=self.colors['Gray2'],
                            fg=self.colors[self.dateStates[status]['color']],
                            font=("Source Code Pro Medium",
                                  13))
            if status != 'UNKNOWN' and datefrom is not None:
                dateLbl['text'] = getDateText(
                    datefrom, dateto, anime.broadcast)
                dateLbl.grid(row=1, column=0, columnspan=2)
            state.grid(row=8, column=0)

        # Actions
        if True:
            actions = Frame(self.choice, bg=self.colors['Gray2'])
            for i, data in enumerate(self.actionButtons):
                Button(actions,
                       text=data['text'],
                       bd=0,
                       height=1,
                       relief='solid',
                       font=("Source Code Pro Medium",
                             13),
                       activebackground=self.colors['Gray2'],
                       activeforeground=self.colors[data['color']],
                       bg=self.colors['Gray2'],
                       fg=self.colors[data['color']],
                       command=lambda c=data['command'],
                       id=id: c(id)).grid(row=0,
                                          column=i * 2)
                if i < len(self.actionButtons) - 1:
                    Label(
                        actions,
                        text="-",
                        bd=0,
                        height=1,
                        font=(
                            "Source Code Pro Medium",
                            13),
                        bg=self.colors['Gray2'],
                        fg=self.colors['Gray'],
                    ).grid(
                        row=0,
                        column=i * 2 + 1)

            actions.grid(row=9, column=0)

        self.choice.update()
        if 'hash' not in self.choice.__dict__.keys():
            threading.Thread(target=findTorrent, args=(id,), daemon=True).start()

    def copy_title(self, id):
        database = self.getDatabase()
        self.root.clipboard_clear()
        title = database(id=id, table="anime")['title']
        self.root.clipboard_append(title)

    def reload(self, id, update=True):
        def handler(id, que):
            database = self.getDatabase()
            keys = database(id=id, table="indexList")
            data = self.api.anime(id)
            que.put(data)

        if 'TIME' in self.logs:
            self.start = time.time()

        thread_files = threading.Thread(target=self.regroupFiles, daemon=True)
        thread_files.start()

        reloadFen = True
        if update:
            que = queue.Queue()
            thread_data = threading.Thread(target=handler, args=(id, que), daemon=True)
            thread_data.start()

            sql = "DELETE FROM characters WHERE anime_id=?"
            self.database.sql(sql, (id,), save=True)

            while thread_data.is_alive():
                self.root.update()
                if self.choice is None or not self.choice.winfo_exists():
                    reloadFen = False
                time.sleep(0.01)
            data = que.get()
            if data is not None:
                self.database.set(data, table="anime")

        while thread_files.is_alive():
            time.sleep(0.01)
            self.root.update()

        if reloadFen:
            self.choice.clear()
            self.optionsWindow(id)
            self.choice.focus_force()

            self.log('TIME', "Reloading:".ljust(25),
                     round(time.time() - self.start, 2), "sec")

    def deleteFiles(self, id):
        def clearFolder(path):
            if len(os.listdir(path)) >= 1:
                self.log("DISK_ERROR",
                         "Some files haven't been removed from folder", path)
            try:
                os.rmdir(path)
            except BaseException:
                self.log("DISK_ERROR", "Couldn't delete folder", path)
        folder = self.getFolder(id)
        path = os.path.join(
            self.animePath,
            folder) if folder is not None else ""

        if os.path.exists(path):
            anime = self.database(id=id, table="anime")
            torrents = json.loads(
                anime.torrent) if anime.torrent is not None else []

            if self.getQB() == "OK":
                hashes = [self.getTorrentHash(os.path.join(
                    self.torrentPath, torrent)) for torrent in torrents]

                self.log('DB_UPDATE', "Deleting", path, "-",
                         len(hashes), "torrents to remove")

                self.qb.torrents_delete(
                    delete_files=True,
                    torrent_hashes=hashes)

            try:
                # rd /S /Q "\\?\D:\Animes\folder."
                os.system('del /F /S /Q "{}"'.format(path))
                clearFolder(path)
            except Exception:
                self.log('DISK_ERROR', "Error while removing folder", path)
                raise
        else:
            self.log("DISK_ERROR", "Folder path doesn't exist:", path)
        self.log("DB_UPDATE", "Deleted all files")
        self.reload(id, False)

    def delete(self, id):
        self.log('DB_UPDATE', "Deleted", self.database(
            id=id, table="anime")['title'])
        for anime in self.animeList:
            if anime.id == id:
                self.animeList.remove(anime)
        self.database.remove("id", id=id, table="anime")
        self.createList()
        self.choice.exit()

    def deleteSeenEpisodes(self, id):
        folder = self.getFolder(id)
        path = os.path.join(
            self.animePath,
            folder) if folder is not None else ""

        if os.path.exists(path):
            toDelete = []
            anime = self.database(id=id, table="anime")
            last_seen = os.path.normpath(anime.last_seen)

            eps = self.getEpisodes(folder)
            if len(eps) >= 1 and list(eps)[0] is not None:
                pathList = {os.path.normpath(e['path']): e for e in eps}
            else:
                pathList = []
            if last_seen is not None and last_seen in pathList.keys():
                for p, e in pathList.items():
                    if p == os.path.normpath(last_seen):
                        break
                    toDelete.append(p)

            torrents = json.loads(
                anime.torrent) if anime.torrent is not None else []

            if self.getQB() == "OK":
                hashes = [self.getTorrentHash(os.path.join(
                    self.torrentPath, torrent)) for torrent in torrents]
                hashesToDelete = []

                for t_hash in hashes:
                    try:
                        root = self.qb.torrents_properties(t_hash).save_path
                    except qbittorrentapi.exceptions.NotFound404Error:
                        continue

                    for f in self.qb.torrents_files(t_hash):
                        sub_p = os.path.normpath(os.path.join(path, f.name))
                        if sub_p in toDelete:
                            hashesToDelete.append(t_hash)
                            break

                self.log('DB_UPDATE', "Deleting", len(toDelete), "files from", path, "-",
                         len(hashesToDelete), "torrents to remove")

                self.qb.torrents_delete(
                    torrent_hashes=hashes)

                cmd = 'del /F /Q "{}"'.format('" "'.join(toDelete))
                try:
                    os.system(cmd)
                except Exception:
                    self.log('DISK_ERROR', "Error while removing folder", path)
                    raise
            else:
                self.log("MAIN_STATE", "qBittorrent API not found!")
                return
        else:
            self.log("DISK_ERROR", "Folder path doesn't exist:", path)
        self.log("DB_UPDATE", "Deleted all files")
        self.reload(id, False)
