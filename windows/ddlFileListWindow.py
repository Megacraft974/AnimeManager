import time
from tkinter import *

import utils


class ddlFileListWindow:
    def ddlFileListWindow(self, publisher, id):
        # Function
        def startDownload(labels, url, id):
            out = self.downloadFile(id, url=url)
            for label in labels:
                try:
                    label.configure(fg=self.colors['Gray4'])
                except Exception:
                    pass
            table.update_scrollzone()
            download_cb(out, labels)

        def download_cb(out, labels):
            if out.empty():
                self.fileChooser.after(10, download_cb, out, labels)
                return
            value = out.get()
            color = 'Blue' if value is True else 'Red'
            for label in labels:
                try:
                    label.configure(fg=self.colors[color])
                except Exception:
                    pass

        # Window init - Fancy corners - Main frame - Events
        if True:
            size = (self.torrentDDLWindowMinWidth,
                    self.torrentDDLWindowMinHeight)
            if self.fileChooser is None or not self.fileChooser.winfo_exists():
                self.fileChooser = utils.RoundTopLevel(
                    self.ddlWindow,
                    title="Torrents:",
                    minsize=size,
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray3'])
            else:
                self.fileChooser.clear()

            table = utils.ScrollableFrame(
                self.fileChooser, bg=self.colors['Gray2'])
            table.pack(expand=True, fill="both", padx=20)

            # keys = {"Title": "filename", "Seeds": "seeds", "Leechs": "leechs", "Size": "filesize"}
            # table = TableFrame(scroll_frame, keys, )
            table.grid_columnconfigure(0, weight=1)

        # Torrent list
        if True:
            data = self.ddlWindow.publisherData[publisher]

            maxTitleLength = len(
                sorted(
                    (d['filename'] for d in data),
                    key=len,
                    reverse=True)[0])
            maxSizeLength = len(
                str(sorted((d['file_size'] for d in data), reverse=True)[0]))

            for row, d in enumerate(data):
                title = d['filename']
                fg = self.getTorrentColor(title)
                # title = d['name'].ljust(maxLength) + "-" + d['size']
                bg = (self.colors['Gray3'], self.colors['Gray2'])[row % 2]
                titleLbl = Label(
                    table, text=title.ljust(maxTitleLength), font=(
                        "Source Code Pro Medium", 13), bg=bg, fg=fg)
                titleLbl.grid(row=row, column=0, sticky="nsew")

                seedsLbl = Label(table,
                                 text=(str(d['seeds']) + "▲").rjust(5) + "   ",
                                 font=("Source Code Pro Medium",
                                       13),
                                 bg=bg,
                                 fg=fg)
                seedsLbl.grid(row=row, column=1, sticky="nsew")
                leechsLbl = Label(table,
                                  text=(str(d['leechs']) + "▼").rjust(5) + "   ",
                                  font=("Source Code Pro Medium",
                                        13),
                                  bg=bg,
                                  fg=fg)
                leechsLbl.grid(row=row, column=2, sticky="nsew")
                sizeLbl = Label(
                    table, text=str(
                        d['file_size']).rjust(maxSizeLength), font=(
                        "Source Code Pro Medium", 13), bg=bg, fg=fg)
                sizeLbl.grid(row=row, column=3, sticky="nsew")

                def command(e, labels=(titleLbl, sizeLbl, seedsLbl, leechsLbl), url=d['torrent_url'], id=id):
                    return startDownload(labels, url, id)
                titleLbl.bind("<Button-1>", command)
                seedsLbl.bind("<Button-1>", command)
                leechsLbl.bind("<Button-1>", command)
                sizeLbl.bind("<Button-1>", command)
                # Label(table, text=d['seeders'], font=("Source Code Pro Medium",13), bg=bg, fg=self.colors['White']
                #     ).grid(row=row,column=2,sticky="nsew")
            table.update_scrollzone()
