import queue
import threading
import time

from tkinter import *
from turtle import pu

import utils


class ddlWindow:
    def ddlWindow(self, id, fetcher=None, parent=None):
        # Functions
        if True:
            def fetcher_handler(fetcher, que, id):
                # Simply transfer the torrents from the iterator 
                # to the queue without blocking

                # Starts fetcher
                if fetcher is None:
                    self.log("FILE_SEARCH", "Looking for torrents with id:", id)
                    fetcher = self.searchTorrents(id)

                for torrent in fetcher:
                    que.put(torrent)
                que.put('STOP')

            def handler_loop(table, t, que, is_empty):
                torrents = None
                while t.is_alive() or not que.empty():
                    if que.empty(): 
                        # Don't block the mainloop and come back later
                        self.publisherChooser.after(
                            2000, handler_loop, table, t, que, is_empty)
                        # Don't return yet because we might need to draw the new torrents
                        break

                    torrents = que.get()
                    if torrents == "STOP":
                        self.log('FILE_SEARCH', 'All torrents found')
                        if is_empty:
                            # Show the 'no torrents found' message
                            self.publisherChooser.after(1, draw_table, table, [])
                        return
               
                    # Don't show the 'no torrents found' message
                    if is_empty:
                        is_empty = False

                if torrents is not None:
                    self.log('FILE_SEARCH', 'Overriding torrents')
                    self.publisherChooser.after(1, draw_table, table, torrents)

            def draw_table(table, torrents):
                torrent = None
                start = time.time()
                
                # Delete previous torrents
                # try:
                #     for w in table.winfo_children():
                #         w.destroy()
                # except Exception:
                #     pass

                for i, torrent in enumerate(torrents):
                    publisher, data = torrent

                    if publisher is None:
                        publisher = 'None'

                    self.publisherChooser.publisherData[publisher] = data # Save data
                    
                    button = self.publisherChooser.publisherButtons.get(i, None)
                    if button:
                        if button[0] == publisher:
                            continue # No need to create a button
                        else:
                            button[1].destroy()

                    # Get color for button - fetch first color from corresponding torrents
                    for filename in [d['filename'] for d in data]:
                        fg = self.getTorrentColor(filename)
                        if fg != self.colors['White']: # White is default color, ignore it
                            break

                    # Alternating bg color
                    bg = (self.colors['Gray2'], self.colors['Gray3'])[i % 2]

                    # Avoid raising an error when the window is closing
                    if self.closing or not self.publisherChooser.winfo_exists():
                        return

                    b = Button(
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
                        command=lambda publisher=publisher, id=id: 
                            self.ddlFileListWindow(publisher, id)
                    )
                    b.grid(
                        row=i,
                        column=0,
                        sticky="nsew"
                    )

                    self.publisherChooser.publisherButtons[i] = (publisher, b)

                try:
                    if torrent is None:
                        self.publisherChooser.titleLbl['text'] = "No files\nfound!"
                    else:
                        self.publisherChooser.titleLbl['text'] = "Publisher:"
                except TclError:
                    pass
                table.update_scrollzone()
                self.log('FILE_SEARCH', f'Updated torrent table in {round(time.time()-start, 2)}s')

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
            self.publisherChooser.publisherData = {}
            self.publisherChooser.publisherButtons = {}
            que = queue.Queue()
            is_empty = True
            t = threading.Thread(
                target=fetcher_handler, args=(fetcher, que, id), daemon=True)
            t.start()
            handler_loop(table, t, que, is_empty)