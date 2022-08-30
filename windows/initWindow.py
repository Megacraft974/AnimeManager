import os
import time
import threading
from tkinter import *

import utils
import mobile_server


class initWindow:
    def initWindow(self):
        # Functions
        if True:
            def options(e):
                # Placeholder
                self.menuOptions[e]['command']()

            def filter(e):
                self.searchTerms.set("")
                filter_name = self.filterOptions[e]['filter']
                if filter_name == "SEASON":
                    self.seasonSelector()
                else:
                    self.animeList.from_filter(filter_name)

            def reset_windows(e):
                for c in self.fen.winfo_children():
                    if isinstance(c, Toplevel):
                        c.destroy()

            def bringToTop(e):
                try:
                    self.fen.lift()
                    self.fen.focus_force()
                except Exception:
                    pass
                # self.fen.focus_force()
                self.root.iconify()

            def checkFocus(e):
                if e.widget.winfo_toplevel() == self.fen:
                    for c in self.fen.winfo_children():
                        if isinstance(c, Toplevel):
                            if hasattr(c, "topLevel"):
                                c.topLevel.focus_force()
                            else:
                                c.focus_force()

            def checkServer():
                if threading.main_thread() == threading.current_thread():
                    threading.Thread(target=checkServer, daemon=True).start()
                    return
                if self.enableServer:
                    self.server = mobile_server.startServer(
                        self.hostName, self.serverPort, self.dbPath, self)
                elif self.server is not None:
                    mobile_server.stopServer(self.server, self)
                    self.server = None

            def start_move(event, window):
                window.x = event.x
                window.y = event.y

            def do_move(event, window):
                try:
                    deltax = event.x - window.x
                    deltay = event.y - window.y
                    x = window.winfo_x() + deltax
                    y = window.winfo_y() + deltay
                    window.geometry(f"+{x}+{y}")
                except AttributeError as e:
                    self.log("[ERROR]", "Error while moving main window")

        icon_path = os.path.join(self.iconPath, "app_icon", "icon.ico")

        if self.root is None:
            self.root = Tk()
            mainloop = True
            self.root.iconbitmap(icon_path)
            self.root.title(self.mainWindowTitle)
            # self.root.attributes('-alpha', 0.0)
            self.root.attributes('-topmost', 1)

            img_path = os.path.join(self.iconPath, "app_icon", "256x256", "icon_full.png")
            img = self.getImage(img_path)
            can = Canvas(self.root, width=256, height=256)
            can.create_image((0, 0), image=img, anchor="nw")
            can.pack()

            self.root.protocol("WM_DELETE_WINDOW", self.quit)
            self.root.focus_force()
            self.root.iconify()
            self.root.bind("<Map>", bringToTop)

            self.root.report_callback_exception = self.mainloop_error_handler
        else:
            mainloop = False

        if self.fen is None or not self.fen.winfo_exists():
            self.fen = Toplevel(self.root)
            self.fen.focus_force()
            self.fen.configure(bg=self.colors['Gray3'])
            self.fen.geometry(
                "{}x{}+100+100".format(self.mainWindowWidth, self.mainWindowHeight))
            self.fen.overrideredirect(True)
            self.fen.title(self.mainWindowTitle)
            self.fen.iconbitmap(icon_path)
            self.fen.bind("<FocusIn>", checkFocus)

            self.fen.resizable(False, True)
            dbFrame = Frame(self.fen, bg=self.colors['Gray2'], width=920)
            head = Frame(dbFrame, bg=self.colors['Gray2'])
            head.pack(fill="both")
            head.grid_columnconfigure(1, weight=1)

            # Top bar
            if True:
                droplistIcon = self.getImage(os.path.join(
                    self.iconPath, "menu.png"), (30, 30))
                droplist = OptionMenu(
                    head,
                    StringVar(),
                    *self.menuOptions.keys(),
                    command=options)
                droplist.configure(
                    indicatoron=False,
                    image=droplistIcon,
                    highlightthickness=0,
                    borderwidth=0,
                    activebackground=self.colors['Gray2'],
                    bg=self.colors['Gray2'],
                )
                droplist["menu"].configure(
                    bd=0,
                    borderwidth=0,
                    activeborderwidth=0,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    activebackground=self.colors['Gray2'],
                    activeforeground=self.colors['White'],
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'],
                )
                droplist.image = droplistIcon
                droplist.grid(row=0, column=0, padx=15)

                for i, color in enumerate([c['color']
                                          for c in self.menuOptions.values()]):
                    droplist['menu'].entryconfig(
                        i, foreground=self.colors[color])

                self.searchTerms = StringVar(self.fen)

                searchBar = Entry(
                    head,
                    textvariable=self.searchTerms,
                    highlightthickness=0,
                    borderwidth=0,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'])
                searchBar.grid(row=0, column=1, sticky="nsew", pady=10)
                searchBar.bind("<ButtonPress-1>", lambda e: start_move(e, self.fen))
                searchBar.bind("<B1-Motion>", lambda e: do_move(e, self.fen))
                # self.searchTerms.trace_add("write", self.search)
                searchBar.bind("<KeyRelease>", self.search)
                searchBar.bind("<Return>", self.search)
                # searchBar.bind("<Control-Return>", lambda e: self.search(force_search=True))

                self.giflist = [
                    PhotoImage(
                        file=os.path.join(
                            self.iconPath,
                            'loading.gif'),
                        format='gif -index %i' %
                        (i)) for i in range(30)]
                self.loadCanvas = Canvas(
                    head,
                    bg=self.colors['Gray2'],
                    highlightthickness=0,
                    width=56,
                    height=56)
                self.loadCanvas.giflist = self.giflist
                self.loadCanvas.grid(row=0, column=2)

                filterIcon = self.getImage(os.path.join(
                    self.iconPath, "filter.png"), (35, 35))
                filter = OptionMenu(head, StringVar(), * self.filterOptions.keys(), command=filter)
                filter.configure(
                    indicatoron=False,
                    image=filterIcon,
                    highlightthickness=0,
                    borderwidth=0,
                    activebackground=self.colors['Gray2'],
                    bg=self.colors['Gray2'])
                filter["menu"].configure(
                    bd=0,
                    borderwidth=0,
                    activeborderwidth=0,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    activebackground=self.colors['Gray2'],
                    activeforeground=self.colors['White'],
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'],
                )
                filter.image = filterIcon
                filter.grid(row=0, column=3, padx=0)

                for i, color in enumerate(
                        [c['color'] for c in self.filterOptions.values()]):
                    filter['menu'].entryconfig(
                        i, foreground=self.colors[color])

                closeIcon = self.getImage(os.path.join(
                    self.iconPath, "close.png"), (40, 40))
                closeButton = Button(
                    head,
                    image=closeIcon,
                    bd=0,
                    height=40,
                    relief='solid',
                    activebackground=self.colors['Gray2'],
                    bg=self.colors['Gray2'],
                    command=self.quit
                )
                closeButton.closeIcon = closeIcon
                closeButton.bind("<Button-3>", reset_windows)
                closeButton.grid(
                    row=0,
                    column=4,
                    padx=10)

            self.animeList = utils.AnimeListFrame(
                dbFrame,
                self,
                scrollbar=True,
                fg=self.colors['Gray3'],
                bg=self.colors['Gray2'],
                thickness=15,
                padding=4,
                width=900)
            self.animeList.pack(fill="both", expand=True)

            Label(
                self.animeList,
                text="Loading...",
                bg=self.colors['Gray2'],
                fg=self.colors['Gray4'],
                font=(
                    "Source Code Pro Medium",
                    20)).grid(
                row=0,
                column=0,
                columnspan=4,
                sticky="nsew")

            dbFrame.pack(fill="both", expand=True)
            for i in range(4):
                self.animeList.grid_columnconfigure(i, weight=1)

        self.log('TIME', "Window created:".ljust(25),
                 round(time.time() - self.start, 2), "sec")

        self.animeList.from_filter("DEFAULT")
        checkServer()

        self.log('TIME', "Ready:".ljust(25), round(
            time.time() - self.start, 2), "sec")

        if mainloop:
            self.root.mainloop()
