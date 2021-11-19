import time
import os
import json
import mobile_server
from tkinter.filedialog import askopenfilename, askdirectory
from tkinter import *

import utils


class settingsWindow:
    def settingsWindow(self):
        # Functions
        if True:
            def exit(e=None):
                # Placeholder for code folding
                self.settings.destroy()
                self.settings = None
                self.fen.focus_force()

            def getDir(title, var, file=False):
                if not file:
                    path = askdirectory(
                        parent=self.root,
                        title=title,
                        initialdir=getattr(
                            self,
                            var))
                else:
                    path = askopenfilename(
                        parent=self.root, title=title, initialdir=os.path.dirname(
                            getattr(
                                self, var)), filetypes=[
                            ("Database", (".db"))])
                if path != "":
                    self.setSettings({var: path})
                    self.start = time.time()
                    self.initWindow()
                try:
                    self.settingsWindow()
                except BaseException:
                    pass

            def checkboxHandler(value, var):
                self.setSettings({var: bool(value.get())})
                self.settings.update()
                self.start = time.time()
                self.initWindow()

            def drawLogs(parent):
                for w in parent.winfo_children():
                    w.destroy()

                columns = 3
                [parent.grid_columnconfigure(i, weight=1)
                 for i in range(columns)]
                allLogs = sorted(
                    self.logs) + sorted((log for log in self.allLogs if log not in self.logs))
                for ind, log in enumerate(allLogs):
                    if log in self.logs:
                        color = "Green"
                    else:
                        color = "Red"
                    column = ind % columns
                    Button(
                        parent,
                        text=log,
                        bd=0,
                        height=1,
                        relief='solid',
                        font=(
                            "Source Code Pro Medium",
                            13),
                        activebackground=self.colors['Gray2'],
                        activeforeground=self.colors['White'],
                        bg=self.colors['Gray3'],
                        fg=self.colors[color],
                        command=lambda log=log,
                        parent=parent: toggleLog(
                            log,
                            parent)).grid(
                        row=ind // columns,
                        column=column,
                        sticky="nsew",
                        pady=2,
                        padx=2)

            def toggleLog(log, parent):
                if log in self.logs:
                    self.logs.remove(log)
                else:
                    self.logs.append(log)

                self.setSettings({"logs": self.logs})
                drawLogs(parent)

            def updateServer(*values):
                for var, field in values:
                    value = var.get()
                    if field == "ADDRESS":
                        self.setSettings({"hostName": value})
                    elif field == "PORT":
                        self.setSettings({"serverPort": int(value)})
                    else:
                        raise Exception

                if self.enableServer:
                    mobile_server.stopServer(self.server, self)
                    self.server = mobile_server.startServer(
                        self.hostName, self.serverPort, self.dbPath, self)

            def updateTorrent(*values, entries=None):
                for var, field in values:
                    value = var.get()
                    if field == "ADDRESS":
                        self.setSettings({"torrentApiAddress": value})
                    elif field == "LOGIN":
                        self.setSettings({"torrentApiLogin": value})
                    elif field == "PASSWORD":
                        self.setSettings({"torrentApiPassword": value})
                    else:
                        raise Exception

                auth = self.getQB(reconnect=True)
                if entries is not None:
                    if auth == "ADDRESS":
                        colA, colC = 'Red', 'White'
                    elif auth == "CREDENTIALS":
                        colA, colC = 'Green', 'Red'
                    elif auth == "OK":
                        colA, colC = 'Green', 'Green'
                    entries['address'].configure(fg=colA)
                    entries['login'].configure(fg=colC)
                    entries['password'].configure(fg=colC)

        # Main window - Events - Fancy corners - Title
        if True:
            try:
                exist = self.settings.winfo_exists() and self.fen.winfo_exists()
            except BaseException:
                exist = False
            if self.settings is None or not exist:
                size = (self.settingsWindowMinWidth,
                        self.settingsWindowMinHeight)
                self.settings = utils.RoundTopLevel(
                    self.fen,
                    title="Settings",
                    minsize=size,
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray4'])
            else:
                self.settings.clear()
                self.settings.focus()
            # self.settings.titleLbl.configure(text="Settings", font=("Source Code Pro Medium",20),
            #         bg= self.colors['Gray2'], fg= self.colors['Gray4'],)

        # Path update frame "iconPath","cache","path","torrentPath","dbPath"
        if True:
            pathFrame = Frame(self.settings, bg=self.colors['Gray2'])
            Button(
                pathFrame,
                text="Change anime folder",
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
                command=lambda id=id: getDir(
                    "Choose anime folder",
                    "animePath")).grid(
                row=0,
                column=0,
                sticky="nsew",
                pady=2,
                padx=2)

            Button(
                pathFrame,
                text="Change torrents folder",
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
                command=lambda id=id: getDir(
                    "Choose torrents folder",
                    "torrentPath")).grid(
                row=1,
                column=0,
                sticky="nsew",
                pady=2,
                padx=2)

            Button(
                pathFrame,
                text="Change cache folder",
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
                command=lambda id=id: getDir(
                    "Choose cache folder",
                    "cache")).grid(
                row=0,
                column=1,
                sticky="nsew",
                pady=2,
                padx=2)

            Button(
                pathFrame,
                text="Change database path",
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
                command=lambda id=id: getDir(
                    "Choose database file",
                    "dbPath",
                    True)).grid(
                row=1,
                column=1,
                sticky="nsew",
                pady=2,
                padx=2)
            pathFrame.grid(row=1, column=0)
            [pathFrame.grid_columnconfigure(i, weight=1) for i in range(2)]

        # Checkboxe "hideRated"
        if True:
            checkboxFrame = Frame(self.settings, bg=self.colors['Gray2'])
            iconSize = (20, 20)
            no_check = self.getImage('./icons/no_check.png', iconSize)
            check = self.getImage('./icons/check.png', iconSize)
            ratedVar = IntVar()
            ratedVar.set(self.hideRated)
            ratedCB = Checkbutton(
                checkboxFrame,
                text=" Hide rated anime (R+/Rx)",
                bd=0,
                relief='solid',
                indicatoron=False,
                image=no_check,
                compound='left',
                selectimage=check,
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray3'],
                activeforeground=self.colors['White'],
                bg=self.colors['Gray2'],
                fg=self.colors['White'],
                selectcolor=self.colors['Gray2'],
                variable=ratedVar,
                command=lambda: checkboxHandler(
                    ratedVar,
                    "hideRated"))
            ratedCB.no_check = no_check
            ratedCB.check = check
            ratedCB.grid(row=0, column=0, sticky="nsew", pady=10)

            # [checkboxFrame.grid_rowconfigure(i,weight=1) for i in range(2)]
            checkboxFrame.grid(row=2, column=0)

        Frame(self.settings, bg=self.colors['Gray'], height=2).grid(
            row=5, column=0, pady=10, sticky="ew")  # Separator

        # Server entries
        if True:
            serverFrame = Frame(self.settings, bg=self.colors['Gray2'])

            Label(
                serverFrame,
                text="Mobile App Server (BETA)",
                justify="center",
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray2'],
                fg=self.colors['White']).grid(
                row=0,
                column=0,
                columnspan=4,
                sticky="nsew",
                pady=(
                    0,
                    7))

            serverVar = IntVar()
            serverVar.set(self.enableServer)
            serverCB = Checkbutton(
                serverFrame,
                text=" Enable server",
                bd=0,
                relief='solid',
                indicatoron=False,
                image=no_check,
                compound='left',
                selectimage=check,
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray3'],
                activeforeground=self.colors['White'],
                bg=self.colors['Gray2'],
                fg=self.colors['White'],
                selectcolor=self.colors['Gray2'],
                variable=serverVar,
                command=lambda: checkboxHandler(
                    serverVar,
                    "enableServer"))
            serverCB.no_check = no_check
            serverCB.check = check
            serverCB.grid(row=1, column=0, columnspan=4,
                          sticky="nsew", pady=(0, 7))

            serverAddress = StringVar()
            serverAddress.set(self.hostName)
            serverEntry = Entry(
                serverFrame,
                textvariable=serverAddress,
                highlightthickness=0,
                width=15,
                justify="center",
                borderwidth=0,
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray3'],
                fg=self.colors['White'])
            serverEntry.bind("<Return>", lambda e,
                             var=serverAddress: updateServer((var, "ADDRESS")))
            serverEntry.grid(row=2, column=0, sticky="nsew")
            self.settings.handles.append(serverEntry)

            tmp = Frame(serverFrame, bg=self.colors['Gray3'])
            Label(
                tmp,
                text=":",
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray3'],
                fg=self.colors['White']).grid(
                row=0,
                column=0,
                pady=(
                    2,
                    0))
            tmp.grid(row=2, column=1, sticky="nsew")

            serverPort = StringVar()
            serverPort.set(self.serverPort)
            serverPortEntry = Entry(
                serverFrame,
                textvariable=serverPort,
                highlightthickness=0,
                width=5,
                justify="center",
                borderwidth=0,
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray3'],
                fg=self.colors['White'])
            serverPortEntry.bind("<Return>", lambda e,
                                 var=serverPort: updateServer((var, "PORT")))
            serverPortEntry.grid(row=2, column=2, sticky="nsew")
            self.settings.handles.append(serverPortEntry)

            Button(
                serverFrame,
                text="Restart server",
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
                command=lambda address=serverAddress,
                port=serverPort: updateServer(
                    (address,
                     "ADDRESS"),
                    (port,
                     "PORT"))).grid(
                row=2,
                column=3,
                sticky="nsew",
                padx=4)

            serverFrame.grid_columnconfigure(0, weight=1)
            serverFrame.grid_columnconfigure(1, weight=1)
            serverFrame.grid(row=6, column=0, padx=2)

        Frame(self.settings, bg=self.colors['Gray'], height=2).grid(
            row=7, column=0, pady=10, sticky="ew")  # Separator

        # Qbittorent entries
        if True:
            torrentFrame = Frame(self.settings, bg=self.colors['Gray2'])
            entries = {}
            auth = self.getQB()
            if auth == "ADDRESS":
                colA, colC = 'Red', 'White'
            elif auth == "CREDENTIALS":
                colA, colC = 'Green', 'Red'
            elif auth == "OK":
                colA, colC = 'Green', 'Green'

            Label(
                torrentFrame,
                text="qBittorrent Client",
                justify="center",
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray2'],
                fg=self.colors['White']).grid(
                row=0,
                column=0,
                columnspan=2,
                sticky="nsew",
                pady=(
                    0,
                    7))
            Label(
                torrentFrame,
                text="Address:",
                justify="right",
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray2'],
                fg=self.colors['White']).grid(
                row=1,
                column=0,
                pady=3)
            torrentApiAddress = StringVar()
            torrentApiAddress.set(self.torrentApiAddress)
            entries['address'] = Entry(
                torrentFrame,
                textvariable=torrentApiAddress,
                highlightthickness=0,
                width=40,
                justify="center",
                borderwidth=0,
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray3'],
                fg=self.colors[colA])
            entries['address'].bind(
                "<Return>", lambda e, var=torrentApiAddress: updateTorrent(
                    (var, "ADDRESS")))
            entries['address'].grid(row=1, column=1, sticky="nsew", pady=3)

            Label(
                torrentFrame,
                text="Login:",
                justify="right",
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray2'],
                fg=self.colors['White']).grid(
                row=2,
                column=0,
                pady=3)
            torrentApiLogin = StringVar()
            torrentApiLogin.set(self.torrentApiLogin)
            entries['login'] = Entry(
                torrentFrame,
                textvariable=torrentApiLogin,
                highlightthickness=0,
                justify="center",
                borderwidth=0,
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray3'],
                fg=self.colors[colC])
            entries['login'].bind(
                "<Return>", lambda e, var=torrentApiLogin: updateTorrent(
                    (var, "LOGIN")))
            entries['login'].grid(row=2, column=1, sticky="nsew", pady=3)

            Label(
                torrentFrame,
                text="Password:",
                justify="right",
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray2'],
                fg=self.colors['White']).grid(
                row=3,
                column=0,
                pady=3)
            torrentPwd = StringVar()
            torrentPwd.set(self.torrentApiPassword)
            entries['password'] = Entry(
                torrentFrame,
                textvariable=torrentPwd,
                highlightthickness=0,
                justify="center",
                borderwidth=0,
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray3'],
                fg=self.colors[colC])
            entries['password'].bind(
                "<Return>", lambda e, var=torrentPwd: updateTorrent(
                    (var, "LOGIN")))
            entries['password'].grid(row=3, column=1, sticky="nsew", pady=3)

            b = Button(
                torrentFrame,
                text="Connect",
                bd=0,
                height=1,
                relief='solid',
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray'],
                activeforeground=self.colors['White'],
                bg=self.colors['Gray3'],
                fg=self.colors['White'],
            )
            b.configure(
                command=lambda address=torrentApiAddress,
                login=torrentApiLogin,
                pwd=torrentPwd,
                b=entries: updateTorrent(
                    (address,
                     "ADDRESS"),
                    (login,
                     "LOGIN"),
                    (pwd,
                     "PASSWORD"),
                    entries=b))
            b.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=3)

            self.settings.handles += list(entries.values())
            torrentFrame.grid_columnconfigure(1, weight=1)
            torrentFrame.grid(row=8, column=0, padx=2)

        Frame(self.settings, bg=self.colors['Gray'], height=2).grid(
            row=9, column=0, pady=10, sticky="ew")  # Separator

        # Logs frame
        if True:
            logsFrame = Frame(self.settings, bg=self.colors['Gray2'])
            Label(
                logsFrame,
                text="Logs",
                justify="center",
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray2'],
                fg=self.colors['White']).grid(
                row=0,
                column=0,
                sticky="nsew",
                pady=(
                    0,
                    7))
            logsParentFrame = Frame(logsFrame, bg=self.colors['Gray2'])
            drawLogs(logsParentFrame)
            logsParentFrame.grid(row=1, column=0, sticky="nsew")
            logsFrame.grid_rowconfigure(1, weight=1)
            logsFrame.grid_columnconfigure(0, weight=1)
            logsFrame.grid(row=10, column=0, sticky="nsew")

        self.settings.update()

    def setSettings(self, settings):
        with open(self.settingsPath, 'r') as f:
            self.settings = json.load(f)
        for updateKey, updateValue in settings.items():
            for cat, values in self.settings.items():
                if updateKey in values.keys():
                    self.settings[cat][updateKey] = updateValue
                    break
            setattr(self, updateKey, updateValue)
        with open(self.settingsPath, 'w') as f:
            json.dump(self.settings, f, sort_keys=True, indent=4)
