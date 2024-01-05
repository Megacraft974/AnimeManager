import os
import queue
import re
import threading

from tkinter.filedialog import askopenfilenames
from tkinter import *
from .. import search_engines

from .. import utils


class torrentFilesWindow:
    def torrentFilesWindow(self, id):
        # Functions
        if True:
            def import_torrent(id):

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
                if len(torrents) >= 1:
                    with self.database.get_lock():
                        self.database.save_metadata(id, {"torrents": torrents})
                        self.database.save()

                self.torrentFilesWindow(id)

            def search_torrent(id):
                def callback(var, id):
                    text = var.get()
                    self.popupWindow.exit()

                    web_reg = re.compile(r"^(http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)$")
                    mag_reg = re.compile(r"^magnet:\?xt=urn:\S+$")
                    if re.match(web_reg, text):
                        # Web url
                        self.downloadFile(id, url=text)
                    elif re.match(mag_reg, text):
                        # Magnet url
                        self.downloadFile(id, url=text)
                    else:
                        # Torrent title
                        self.addSearchTerms(id, text)
                        fetcher = search_engines.search([text])
                        self.drawDdlWindow(id, fetcher, parent=self.torrentFilesChooser)

                self.textPopupWindow(
                    self.torrentFilesChooser,
                    "Search torrents with name:",
                    lambda var,
                    id=id: callback(var, id),
                    fentype="TEXT")

            def getTorrents(id):
                return self.database.get_metadata(id, "torrents")

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

                if self.getQB() == "OK":
                    d = self.qb.torrents_info(torrent_hashes=hashes.values())
                else:
                    self.log("MAIN_STATE", "[ERROR] - qBittorent not found!")
                    return {}
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

                return out

            def updateTorrentsList():
                def handler(id, que):
                    try:
                        out = getTorrentsState(id)
                    except:
                        que.put([])
                    else:
                        que.put(out)

                if self.torrentFilesChooser.torrent_thread is None:
                    que = queue.Queue()
                    t = threading.Thread(target=handler, args=(id, que))
                    t.start()
                    self.torrentFilesChooser.torrent_thread = t
                    self.torrentFilesChooser.torrent_que = que
                
                if self.torrentFilesChooser.torrent_que.empty():
                    self.torrentFilesChooser.after(100, updateTorrentsList)
                    return

                torrents = self.torrentFilesChooser.torrent_que.get()
                self.torrentFilesChooser.loading_label.destroy()
                if len(torrents) > 0:
                    for i, item in enumerate(torrents.items()):
                        torrent, state = item
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
                else:
                    Label(
                        torrent_list_frame,
                        text="No torrents yet",
                        bd=0,
                        height=1,
                        relief='solid',
                        font=(
                            "Source Code Pro Medium",
                            15),
                        bg=self.colors['Gray2'],
                        fg=self.colors['Gray4'],
                    ).grid(
                        row=0,
                        column=0,
                        sticky="nsew",
                        pady=15,
                        ipady=8)
                
                torrent_list_frame.update_scrollzone()

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
                            delete_files=True,
                            torrent_hashes=(t_hash,))
                else:
                    database = self.getDatabase()
                    torrents = getTorrents(id)

                    if t in torrents:  # Disabled
                        with database.get_lock():
                            database.sql("DELETE FROM torrents WHERE id=? AND value=?", (id, t))
                            database.save()

                    if state != "NOT_FOUND":
                        if os.path.exists(path):
                            os.remove(path)

                self.torrentFilesWindow(id)

        # Main window
        if True:
            if self.torrentFilesChooser is None or not self.torrentFilesChooser.winfo_exists():
                size = (self.torrentFilesWindowMinWidth, self.torrentFilesWindowMinHeight)
                self.torrentFilesChooser = utils.RoundTopLevel(
                    self.optionsWindow, title="Torrents files",
                    minsize=size, bg=self.colors['Gray2'], fg=self.colors['Gray3']
                )
            else:
                self.torrentFilesChooser.clear()
                self.torrentFilesChooser.focus()
            self.torrentFilesChooser.grid_rowconfigure(1, weight=1)
            [self.torrentFilesChooser.grid_columnconfigure(i, weight=1) for i in range(2)]

        # Add/search torrent buttons
        if True:
            Button(
                self.torrentFilesChooser,
                text="Search torrent online",
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
                command=lambda id=id: search_torrent(id)
            ).grid(
                row=0,
                column=0,
                sticky="nsew",
                pady=3,
                padx=(0, 2))

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
                column=1,
                sticky="nsew",
                pady=3,
                padx=(2, 0))

        # Torrents list
        if True:
            torrent_list_frame = utils.ScrollableFrame(
                self.torrentFilesChooser, bg=self.colors['Gray2'], width=900)
            torrent_list_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
            torrent_list_frame.grid_columnconfigure(0, weight=1)

            downloadIcon = self.getImage(os.path.join(
                self.iconPath, "download.png"), (30, 30))
            torrent_list_frame.downloadIcon = downloadIcon
            deleteIcon = self.getImage(os.path.join(
                self.iconPath, "delete.png"), (30, 30))
            torrent_list_frame.deleteIcon = deleteIcon

            self.torrentFilesChooser.loading_label = Label(
                    torrent_list_frame,
                    text="Looking for torrents...",
                    bd=0,
                    height=1,
                    relief='solid',
                    font=(
                        "Source Code Pro Medium",
                        15),
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray4'],
                )
            self.torrentFilesChooser.loading_label.grid(
                    row=0,
                    column=0,
                    sticky="nsew",
                    pady=15,
                    ipady=8)

            self.torrentFilesChooser.torrent_thread = None
            updateTorrentsList()