import json
import os
import re
import threading

from operator import itemgetter
from tkinter.filedialog import askopenfilenames
from tkinter import *

import utils


class torrentFilesWindow:
    def torrentFilesWindow(self, id):
        # Functions
        if True:
            def import_torrent(id):
                def removeOld(self, t_id, t_torrents):
                    return  # Disabled
                    self.log('DB_UPDATE', "Removing torrent duplicates")
                    database = self.getDatabase()
                    with database.get_lock():
                        toRemove = []
                        sql = "SELECT id,value FROM torrents WHERE value IN (" + ",".join("?" * len(t_torrents)) + ") AND id != ?;"
                        for id, torrent in database.sql(sql, (*t_torrents, t_id,)):
                            if id != t_id and torrent in t_torrents:
                                self.log('DB_UPDATE', "Id", id,
                                         "has torrent", t_id, "removing")
                                toRemove.append((id, torrent))
                        if toRemove:
                            for id, torrent in toRemove:
                                database.sql("DELETE FROM torrents WHERE id=? AND value=?;", (id, torrent))
                            database.save()
                    self.log('DB_UPDATE', "Done!")

                torrents = getTorrents(id)
                default = '"' + '" "'.join(torrents) + '"'
                filepaths = askopenfilenames(
                    parent=self.root,
                    title="Select torrents",
                    initialdir=self.torrentPath,
                    initialfile=default,
                    filetypes=[
                        ("Torrents files",
                         (".torrent"))])
                torrents = []
                for path in filepaths:
                    torrents.append(path.rsplit("/")[-1])
                if len(torrents) >= 1:  # Disabled
                    self.database.save_metadata(id, {"torrents": torrents})
                    threading.Thread(target=removeOld, args=(
                        self, id, torrents), daemon=True).start()

                self.torrentFilesWindow(id)

            def getTorrents(id):
                torrents = self.database.get_metadata(id, "torrents")
                return torrents

            def getTorrentsState(id):
                out = {}
                hashes = {}
                torrents = getTorrents(id)
                for t in torrents:
                    path = os.path.join(self.torrentPath, t)
                    if os.path.exists(path):
                        t_hash = self.getTorrentHash(path)
                        hashes[t] = t_hash
                    else:
                        out[t] = "NOT_FOUND"

                d = self.qb.torrents_info(torrent_hashes=hashes.values())
                qb_data, qb_hashes = dict(), set()
                for tmp in d:
                    qb_data[tmp.hash] = tmp
                    qb_hashes.add(tmp.hash)
                for t_name, t_hash in hashes.items():
                    if t_hash in qb_data.keys():
                        t = qb_data[t_hash]
                        if t.state_enum.is_complete:
                            out[t_name] = "COMPLETE"
                        elif t.state_enum.is_downloading:
                            out[t_name] = "DOWNLOADING"
                        else:
                            if t.state == "checkingResumeData":
                                out[t_name] = "DOWNLOADING"
                            else:
                                self.log("MAIN_STATE", "[ERROR] - Unknown torrent state:", t.state, "for torrent:", t.name)
                                out[t_name] = "UNKNOWN"
                    else:
                        out[t_name] = "DELETED"

                def sortkey(item):
                    filename, status = item
                    epsPatternsFormat = (
                        r"-\s(\d+)",
                        r"(?:E|Episode|Ep|Eps)(\d+)",
                        r" (\d+) ")
                    epsPatterns = list(re.compile(p) for p in epsPatternsFormat)

                    seasonPatternsFormat = (
                        r'(?:S|Season|Seasons)\s?([0-9]{1,2})',
                        r'([0-9])(?:|st|nd|rd|th)\s?(?:S|Season|Seasons)')
                    seasonPatterns = list(re.compile(p)
                                          for p in seasonPatternsFormat)
                    episode = "?"

                    for p in epsPatterns:
                        m = re.findall(p, filename)
                        if len(m) > 0:
                            episode = m[0]
                            break
                    if episode == "?":
                        episode = str(len(eps) + 1).zfill(2)  # Hacky

                    season = ""
                    for p in seasonPatterns:
                        result = re.findall(p, filename)
                        if len(result) >= 1:
                            season = result[0]
                            break

                    key = int(str(season).zfill(5) + str(episode).zfill(5))
                    return key

                out = dict(sorted(out.items(), key=sortkey, reverse=True))

                return out

            def download_torrent(id, t):
                # path = os.path.join(self.torrentPath, t)
                self.downloadFile(id, file=t)

                self.torrentFilesChooser.after(1000, self.torrentFilesWindow, id)

            def delete_torrent(id, t, state):
                self.log('DB_UPDATE', "Removing torrent", t, "for id", id)
                path = os.path.join(self.torrentPath, t)

                if state in ("COMPLETE", "DOWNLOADING"):
                    t_hash = self.getTorrentHash(path)
                    if self.getQB() == "OK":
                        self.qb.torrents_delete(
                            delete_files=False,
                            torrent_hashes=(t_hash,))
                else:
                    database = self.getDatabase()
                    torrents = getTorrents(id)

                    if t in torrents and False:  # Disabled
                        torrents.remove(t)
                        if len(torrents) >= 1:
                            data = json.dumps(torrents)
                        else:
                            data = None
                        database.update('torrent', data, id=id, table="anime")

                    if state != "NOT_FOUND":
                        if os.path.exists(path):
                            os.remove(path)

                self.torrentFilesWindow(id)

        # Main window
        if True:
            if self.torrentFilesChooser is None or not self.torrentFilesChooser.winfo_exists():
                size = (self.torrentFilesWindowMinWidth, self.torrentFilesWindowMinHeight)
                self.torrentFilesChooser = utils.RoundTopLevel(
                    self.choice, title="Torrents files",
                    minsize=size, bg=self.colors['Gray2'], fg=self.colors['Gray3']
                )
            else:
                self.torrentFilesChooser.clear()
                self.torrentFilesChooser.focus()
            self.torrentFilesChooser.grid_rowconfigure(1, weight=1)

        # Add torrent button
        if True:
            Button(
                self.torrentFilesChooser,
                text="Locate new torrent",
                bd=0,
                height=1,
                relief='solid',
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['Gray3'],
                bg=self.colors['Gray3'],
                fg=self.colors['White'],
                command=lambda id=id: import_torrent(id)
            ).grid(
                row=0,
                column=0,
                sticky="nse",
                pady=(0, 10),
                padx=(0, 0))

        # Torrents list
        if True:
            torrent_list_frame = utils.ScrollableFrame(
                self.torrentFilesChooser, bg=self.colors['Gray2'], width=900)
            # torrent_list_frame.pack(fill="both", expand=True)
            torrent_list_frame.grid(row=1, column=0, sticky="nsew")
            torrent_list_frame.grid_columnconfigure(0, weight=1)

            downloadIcon = self.getImage(os.path.join(
                self.iconPath, "download.png"), (30, 30))
            torrent_list_frame.downloadIcon = downloadIcon
            deleteIcon = self.getImage(os.path.join(
                self.iconPath, "delete.png"), (30, 30))
            torrent_list_frame.deleteIcon = deleteIcon

            torrents = getTorrentsState(id)
            if len(torrents) > 0:
                for i, item in enumerate(torrents.items()):
                    torrent, state = item
                    # state = getTorrentState(torrent)
                    color = self.torrentsStateColors[state]
                    Label(
                        torrent_list_frame,
                        text=torrent,
                        bd=0,
                        height=1,
                        relief='solid',
                        font=(
                            "Source Code Pro Medium",
                            13),
                        bg=self.colors['Gray3'],
                        fg=self.colors[color],
                    ).grid(
                        row=i,
                        column=0,
                        sticky="nsew",
                        pady=3,
                        ipady=8)
                    Button(
                        torrent_list_frame,
                        image=downloadIcon,
                        bd=0,
                        height=1,
                        relief='solid',
                        activebackground=self.colors['Gray2'],
                        bg=self.colors['Gray3'],
                        command=lambda id=id, t=torrent: download_torrent(id, t)
                    ).grid(
                        row=i,
                        column=1,
                        sticky="nsew",
                        pady=3,
                        ipadx=5)
                    Button(
                        torrent_list_frame,
                        image=deleteIcon,
                        bd=0,
                        height=1,
                        relief='solid',
                        activebackground=self.colors['Gray2'],
                        bg=self.colors['Gray3'],
                        command=lambda id=id, t=torrent, s=state: delete_torrent(id, t, s)
                    ).grid(
                        row=i,
                        column=2,
                        sticky="nsew",
                        pady=3,
                        ipadx=5)

            torrent_list_frame.update()
