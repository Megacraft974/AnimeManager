import shutil
import os
from tkinter import *

import utils


class diskWindow:
    def diskWindow(self):
        # Functions
        if True:
            def getFiles(folder):
                files, folders = [], []
                for f in os.listdir(folder):
                    if os.path.isfile(folder + "/" + f):
                        files.append(f)
                    else:
                        if f != "Torrents":
                            folders.append(f)
                            a, b = getFiles(folder + "/" + f)
                            files += a
                            folders += b
                return files, folders

            def exit(e=None):
                self.diskfen.destroy()

        # Window init - Fancy corners - Events
        if True:
            disk = self.animePath.split("/")[0]
            if self.diskfen is None or not self.diskfen.winfo_exists():
                size = (self.diskWindowMinWidth, self.diskWindowMinHeight)
                self.diskfen = utils.RoundTopLevel(
                    self.fen,
                    title="Disk " + disk,
                    minsize=size,
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray4'])
            else:
                self.diskfen.clear()
                self.diskfen.focus()

        # Bars
        if True:
            barFrame = Frame(self.diskfen, bg=self.colors['Gray2'])
            length = 500
            radius = 25
            usageColors = {75: 'Green', 90: 'Orange', 100: 'Red'}
            total, used, free = shutil.disk_usage(disk)
            usedSize = length * used / total
            usedPrct = used / total * 100
            for p, c in list(usageColors.items())[::-1]:
                if usedPrct <= p:
                    color = c

            # self.diskfen.titleLbl.configure(text="Disk "+disk, font=("Source Code Pro Medium",20),
            #         bg= self.colors['Gray2'], fg= self.colors['Gray4'],)

            bar = Canvas(
                barFrame,
                bg=self.colors['Gray2'],
                width=length,
                height=radius * 2,
                highlightthickness=0,
            )
            bar.create_line(
                radius,
                radius,
                length - radius,
                radius,
                capstyle='round',
                fill=self.colors['Gray4'],
                width=radius)
            bar.create_line(
                radius,
                radius,
                usedSize - radius,
                radius,
                capstyle='round',
                fill=self.colors[color],
                width=radius)
            bar.grid(row=1, column=0, columnspan=3)
            Label(barFrame,
                  text="%d GB used" % (used // (2**30)),
                  wraplength=900,
                  font=("Source Code Pro Medium",
                        12),
                  bg=self.colors['Gray2'],
                  fg=self.colors['Gray4']).grid(row=2,
                                                column=0)
            Label(barFrame,
                  text="%d GB total" % (total // (2**30)),
                  wraplength=900,
                  font=("Source Code Pro Medium",
                        12),
                  bg=self.colors['Gray2'],
                  fg=self.colors['Gray4']).grid(row=2,
                                                column=1)
            Label(barFrame,
                  text="%d GB free" % (free // (2**30)),
                  wraplength=900,
                  font=("Source Code Pro Medium",
                        12),
                  bg=self.colors['Gray2'],
                  fg=self.colors['Gray4']).grid(row=2,
                                                column=2)
            barFrame.grid_columnconfigure(1, weight=1)
            barFrame.pack(pady=20)

        # Stats info
        if True:
            fileFrame = Frame(self.diskfen, bg=self.colors['Gray2'])
            t = Label(
                fileFrame,
                text="Animes folder:",
                wraplength=900,
                font=(
                    "Source Code Pro Medium",
                    20),
                bg=self.colors['Gray2'],
                fg=self.colors['Gray4'])
            t.grid(row=0, column=0, columnspan=2)
            files, folders = getFiles(self.animePath)
            Label(
                fileFrame,
                text="%d files - %d folders" %
                (len(files),
                 len(folders)),
                wraplength=900,
                font=(
                    "Source Code Pro Medium",
                    15),
                bg=self.colors['Gray2'],
                fg=self.colors['Gray4']).grid(
                row=1,
                column=0,
                sticky="nsew")
            # [fileFrame.grid_columnconfigure(i,weight=1) for i in range(2)]
            fileFrame.pack(pady=20)

        self.diskfen.update()
