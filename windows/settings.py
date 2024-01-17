import shutil
import time
import json
from tkinter.filedialog import asksaveasfilename, askdirectory
from tkinter import *

from .. import file_managers
from .. import mobile_server
from .. import torrent_managers
from .. import utils

# TODO - Froze when not connected to torrent client


class Settings:
    def drawSettingsWindow(self):
        # Functions
        if True:
            def changeFileManager(manager):
                self.getFileManager(manager, update=True)

            def changeTorrentManager(manager):
                self.getTorrentManager(manager, update=True)

            def changePlayer(player):
                player = player.replace(' ', '_').casefold()
                self.player = self.media_players[player]
                if player in self.players_order:
                    self.players_order.remove(player)
                self.players_order.insert(0, player)

                self.setSettings({'playerOrder': self.players_order})
                
                
                try:
                    self.drawSettingsWindow()
                except Exception:
                    pass
            
            def exportDB():
                path = asksaveasfilename(
                    confirmoverwrite=True, 
                    defaultextension='.db', 
                    title='Export database as...', 
                    filetypes=[('Database file', '.db')], 
                    initialfile='database.db'
                )
                if path == '':
                    return

                shutil.copy(self.dbPath, path)
                self.log('DB_UPDATE', f'Exported database to {path}')

            def checkboxHandler(value, var):
                self.setSettings({var: bool(value.get())})
                self.start = time.time()
                # self.drawInitWindow() Why tf is this here??

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
                        raise

                if self.enableServer:
                    mobile_server.stopServer(self.server, self)
                    self.server = mobile_server.startServer(
                        self.hostName, self.serverPort, self.dbPath, self)

        # Main window - Events - Fancy corners - Title
        if True:
            try:
                exist = bool(not self.closing and self.settingsWindow.winfo_exists())
            except Exception:
                exist = False
            if self.settingsWindow is None or not exist:
                size = (self.settingsWindowMinWidth,
                        self.settingsWindowMinHeight)
                self.settingsWindow = utils.RoundTopLevel(
                    self.initWindow,
                    title="Settings",
                    minsize=size,
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray4'])
            else:
                self.settingsWindow.clear()

        # Path update frame "iconPath","cache","path","dbPath"
        if True:
            pathFrame = Frame(self.settingsWindow, bg=self.colors['Gray2'])
            kwargs = {
                'bd': 0,
                'height': 1,
                'relief': 'solid',
                'font': (
                    "Source Code Pro Medium",
                    13),
                'activebackground': self.colors['Gray2'],
                'activeforeground': self.colors['White'],
                'bg': self.colors['Gray3'],
                'fg': self.colors['White']
            }

            # File manager
            if True:
                fms = file_managers.managers.keys()
                var = StringVar()
                var.set("Change file manager")
                fmBtn = utils.DropDownMenu(
                    pathFrame,
                    var,
                    *fms,
                    scrollbar=True,
                    highlightthickness=0,
                    borderwidth=0,
                    command = changeFileManager,
                    **kwargs
                )
                fmBtn.menu.configure(
                    bd=0,
                    borderwidth=0,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    activebackground=self.colors['Gray3'],
                    activeforeground=self.colors['White'],
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'],
                    thickness=20,
                    padx=20,
                    sb_fg=self.colors['Gray3']
                )
                fmBtn.menu.root_configure(
                    borderwidth=2,
                    fg=self.colors['Gray3'],
                    bg=self.colors['Gray2']
                )
                fmBtn.menu.update_values()
                fmBtn.grid(
                    row=0,
                    column=0,
                    sticky="nsew",
                    pady=2,
                    padx=2
                )
                fmBtn.var = var

            # Media player
            if True:
                media_players = self.players_order

                for p in self.media_players.keys():
                    if p not in media_players:
                        media_players.append(p)

                media_players = list(map(lambda m: m.replace('_', ' ').capitalize(), media_players))
                var = StringVar()
                var.set("Change media player")
                mediaBtn = utils.DropDownMenu(
                    pathFrame,
                    var,
                    *media_players,
                    scrollbar=True,
                    highlightthickness=0,
                    borderwidth=0,
                    command = changePlayer,
                    **kwargs
                )
                mediaBtn.menu.configure(
                    bd=0,
                    borderwidth=0,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    activebackground=self.colors['Gray3'],
                    activeforeground=self.colors['White'],
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'],
                    thickness=20,
                    padx=20,
                    sb_fg=self.colors['Gray3']
                )
                mediaBtn.menu.root_configure(
                    borderwidth=2,
                    fg=self.colors['Gray3'],
                    bg=self.colors['Gray2']
                )
                mediaBtn.menu.update_values()
                mediaBtn.grid(
                    row=1,
                    column=0,
                    sticky="nsew",
                    pady=2,
                    padx=2
                )
                mediaBtn.var = var

            # Data folder
            if True:
                tms = torrent_managers.managers.keys()
                var = StringVar()
                var.set("Change torrent client")
                tmBtn = utils.DropDownMenu(
                    pathFrame,
                    var,
                    *tms,
                    scrollbar=True,
                    highlightthickness=0,
                    borderwidth=0,
                    command = changeTorrentManager,
                    **kwargs
                )
                tmBtn.menu.configure(
                    bd=0,
                    borderwidth=0,
                    font=(
                        "Source Code Pro Medium",
                        13),
                    activebackground=self.colors['Gray3'],
                    activeforeground=self.colors['White'],
                    bg=self.colors['Gray2'],
                    fg=self.colors['White'],
                    thickness=20,
                    padx=20,
                    sb_fg=self.colors['Gray3']
                )
                tmBtn.menu.root_configure(
                    borderwidth=2,
                    fg=self.colors['Gray3'],
                    bg=self.colors['Gray2']
                )
                tmBtn.menu.update_values()
                tmBtn.grid(
                    row=0,
                    column=1,
                    sticky="nsew",
                    pady=2,
                    padx=2
                )
                tmBtn.var = var

            # Export database
            Button(
                pathFrame,
                text="Export database",
                command=exportDB,
                **kwargs
            ).grid(
                row=1,
                column=1,
                sticky="nsew",
                pady=2,
                padx=2
            )
            
            pathFrame.grid(row=1, column=0)
            [pathFrame.grid_columnconfigure(i, weight=1) for i in range(2)]

        # Checkboxe "hideRated"
        if True:
            checkboxFrame = Frame(self.settingsWindow, bg=self.colors['Gray2'])
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

        Frame(self.settingsWindow, bg=self.colors['Gray'], height=2).grid(
            row=5, column=0, pady=10, sticky="ew")  # Separator

        # Server entries
        if False: # Disabled
            serverFrame = Frame(self.settingsWindow, bg=self.colors['Gray2'])

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
                     "PORT"))
            ).grid(
                row=2,
                column=3,
                sticky="nsew",
                padx=4)

            serverFrame.grid_columnconfigure(0, weight=1)
            serverFrame.grid_columnconfigure(1, weight=1)
            serverFrame.grid(row=6, column=0, padx=2)

            Frame(self.settingsWindow, bg=self.colors['Gray'], height=2).grid(
                row=7, column=0, pady=10, sticky="ew")  # Separator

        # Logs frame
        if True:
            logsFrame = Frame(self.settingsWindow, bg=self.colors['Gray2'])
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

        self.settingsWindow.update_events()
            
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
