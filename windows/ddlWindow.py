import queue
import threading
import time

from tkinter import *

import utils


class ddlWindow:
    def ddlWindow(self, id, fetcher=None, parent=None):
        # Functions
        if True:
            def updateTable(fetcher, table):
                def handler(fetcher, que):
                    while True:
                        try:
                            titles = next(fetcher)
                        except StopIteration:
                            que.put("STOP")
                            break
                        else:
                            que.put(titles)

                que = queue.Queue()
                is_empty = True
                t = threading.Thread(target=handler, args=(fetcher, que), daemon=True)
                t.start()
                while t.is_alive() or not que.empty():
                    while que.empty():
                        try:
                            self.root.update()
                        except AttributeError:
                            pass
                        time.sleep(0.01)

                    titles = que.get()
                    if titles == "STOP":
                        if is_empty:
                            draw_table([])
                        return
                    else:
                        if is_empty:
                            is_empty = False

                    try:
                        for w in table.winfo_children():
                            w.destroy()
                    except BaseException:
                        pass
                    draw_table(titles)

            def draw_table(titles):
                rowHeight = 25
                empty = True

                for i, data in enumerate(titles):
                    if empty:
                        empty = False
                    publisher, data = data
                    marked = ('dual', 'dub')
                    for title in [d['filename'] for d in data]:
                        fg = self.getTorrentColor(title)
                        if fg != self.colors['White']:
                            break
                    bg = (self.colors['Gray2'], self.colors['Gray3'])[i % 2]
                    if publisher is None:
                        publisher = 'None'
                    if self.closing or not self.publisherChooser.winfo_exists():
                        return
                    Button(
                        table,
                        text=publisher,
                        bd=0,
                        height=1,
                        relief='solid',
                        font=(
                            "Source Code Pro Medium",
                            13),
                        activebackground=self.colors['Gray3'],
                        activeforeground=fg,
                        bg=bg,
                        fg=fg,
                        command=lambda a=data,
                        b=id: self.ddlFileListWindow(
                            a,
                            b)).grid(
                        row=i,
                        column=0,
                        sticky="nsew")

                try:
                    if empty:
                        self.publisherChooser.titleLbl['text'] = "No files\nfound!"
                    else:
                        self.publisherChooser.titleLbl['text'] = "Publisher:"
                except _tkinter.TclError:
                    pass

                table.update()
                self.publisherChooser.update()

        # Window init - Fancy corners - Main frame - Events
        if True:
            size = (self.publisherDDLWindowMinWidth,
                    self.publisherDDLWindowMinHeight)
            if self.publisherChooser is None or not self.publisherChooser.winfo_exists():
                if parent is None:
                    parent = self.choice
                self.publisherChooser = utils.RoundTopLevel(
                    parent,
                    title="Loading...",
                    minsize=size,
                    bg=self.colors['Gray3'],
                    fg=self.colors['Gray2'])
            else:
                self.publisherChooser.clear()
                self.publisherChooser.titleLbl.configure(
                    text="Loading...",
                    bg=self.colors['Gray3'],
                    fg=self.colors['Gray2'],
                    font=(
                        "Source Code Pro Medium",
                        18))

            table = utils.ScrollableFrame(
                self.publisherChooser, bg=self.colors['Gray3'])
            table.grid_columnconfigure(0, weight=1)
            table.grid()

            if self.closing or not self.publisherChooser.winfo_exists():
                return
            self.publisherChooser.update()

        # Torrent publisher list
        if True:
            if fetcher is None:
                self.log("FILE_SEARCH", "Looking files for id:", id)
                fetcher = self.searchTorrents(id)
            updateTable(fetcher, table)
