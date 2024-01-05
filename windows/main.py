import os
import time
import threading
from tkinter import *

<<<<<<< HEAD:windows/initWindow.py
from .. import utils
from .. import mobile_server
=======
import utils
>>>>>>> 43be623630f22885a05bbf6ade4c78c75cc26b26:windows/main.py


class Main:
    def drawInitWindow(self):
        # Functions
        if True:
            def options(e):
                # Placeholder
                self.menuOptions[e]['command']()

            def filter(e):
                self.searchTerms.set("")
                filter_name = self.filterOptions[e]['filter']
                if filter_name == "SEASON":
                    self.drawSeasonSelector()
                else:
                    self.animeList.from_filter(filter_name)

            def reset_windows(e):
                for c in self.initWindow.winfo_children():
                    if isinstance(c, Toplevel):
                        c.destroy()

            def bringToTop(e):
                try:
                    self.initWindow.lift()
                    self.initWindow.focus_force()
                except Exception:
                    pass
                # self.initWindow.focus_force()
                self.root.iconify()

            def checkFocus(e):
                if e.widget.winfo_toplevel() == self.initWindow:
                    for c in self.initWindow.winfo_children():
                        if isinstance(c, Toplevel):
                            if hasattr(c, "topLevel"):
                                c.topLevel.focus_force()
                            else:
                                c.focus_force()

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
            if os.path.exists(icon_path):
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

        if self.initWindow is None or not self.initWindow.winfo_exists():
            self.initWindow = Toplevel(self.root)
            self.initWindow.focus_force()
            self.initWindow.configure(bg=self.colors['Gray3'])
            self.initWindow.geometry(
                "{}x{}+100+100".format(self.mainWindowWidth, self.mainWindowHeight))
            self.initWindow.overrideredirect(True)
            self.initWindow.title(self.mainWindowTitle)
            if os.path.exists(icon_path):
                self.initWindow.iconbitmap(icon_path)
            self.initWindow.bind("<FocusIn>", checkFocus)

            self.initWindow.resizable(False, True)
            dbFrame = Frame(self.initWindow, bg=self.colors['Gray2'], width=920)
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

                self.searchTerms = StringVar(self.initWindow, '')

                searchBar = utils.EntryWithPlaceholder(
                    head,
                    placeholder="Search...",
                    textvariable=self.searchTerms,
                    highlightthickness=0,
                    borderwidth=0,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'])
                searchBar.grid(row=0, column=1, sticky="nsew", pady=10)

                searchBar.bind("<ButtonPress-1>", lambda e: start_move(e, self.initWindow))
                searchBar.bind("<B1-Motion>", lambda e: do_move(e, self.initWindow))
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
                filter_menu = OptionMenu(head, StringVar(), * self.filterOptions.keys(), command=filter)
                filter_menu.configure(
                    indicatoron=False,
                    image=filterIcon,
                    highlightthickness=0,
                    borderwidth=0,
                    activebackground=self.colors['Gray2'],
                    bg=self.colors['Gray2'])
                filter_menu["menu"].configure(
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
                filter_menu.image = filterIcon
                filter_menu.grid(row=0, column=3, padx=0)

                for i, color in enumerate(
                        [c['color'] for c in self.filterOptions.values()]):
                    filter_menu['menu'].entryconfig(
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

        self.root.after(1, self.late_startup)

        if mainloop:
            self.root.mainloop()
