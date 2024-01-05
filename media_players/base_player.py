import os
import threading
import time
import json
import sys

from tkinter import *
from PIL import Image, ImageTk
from ctypes import windll, Structure, c_long, byref
from multiprocessing import Process, freeze_support

<<<<<<< HEAD
from pytube import YouTube
import pytube.exceptions

from ..dbManager import thread_safe_db
from ..logger import log
=======
from dbManager import thread_safe_db
from logger import log
>>>>>>> 43be623630f22885a05bbf6ade4c78c75cc26b26


class BasePlayer:
    def __init__(self, *args, **kwargs):
        self.log = log

        if "callback" in kwargs:
            callback = kwargs.pop("callback")
        else:
            callback = None

        if not hasattr(self, "method"):
            if "root" in kwargs:
                # If player must inherit from a parent, stay in same thread,
                # as Tk windows must all be running in the same thread
                self.method = "NONE"
            else:
                self.method = "PROCESS"

        if self.method == "PROCESS":
            # Start player in new process
            p = Process(target=self.start, args=args, kwargs=kwargs)
            p.start()
            threading.Thread(target=self.callback_handler,
                             args=(callback, p)).start()

        elif self.method == "THREAD":
            # Start player in new thread
            t = threading.Thread(target=self.start, args=args, kwargs=kwargs)
            t.start()
            threading.Thread(target=self.callback_handler,
                             args=(callback, t)).start()

        else:
            # Start player in current thread
            # /!\ - Will block the thread!
            self.start(*args, **kwargs)
            if callback is not None:
                callback()

    def setup(self, root):
        player = self.__module__.split('.')[-1].replace('_', ' ').capitalize()
        self.log(f'Starting {player}')
        try:
            cwd = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        except NameError:
            cwd = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.iconPath = os.path.join(cwd, "icons")
        appdata = os.path.join(os.getenv('APPDATA'), "Anime Manager")
        if os.path.exists(os.path.normpath("settings.json")):
            self.settingsPath = os.path.normpath("settings.json")
        else:
            self.settingsPath = os.path.join(appdata, "settings.json")
        with open(self.settingsPath, 'r') as f:
            self.settings = json.load(f)
        self.lastMovement = 0
        self.videoSize = (0, 0, 0)
        self.movementCheck = None
        self.is_iconified = False
        self.hideCursorDelay = 3
        self.root = root

    def image(self, file, size):
        return ImageTk.PhotoImage(
            Image.open(
                os.path.join(self.iconPath, file)
            ).resize(size, Image.LANCZOS),
            master=self.parent)

    def initWindow(self):
        if self.root is None:
            self.parent = Tk()  # Toplevel(root)
        else:
            self.parent = Toplevel(self.root)
        self.name = str(type(self)).split(
            '.', 1)[-1].rsplit("_player", 1)[0].capitalize()
        self.parent.title("{} Media Player".format(self.name))

        self.videopanel = Frame(self.parent)
        Label(
            self.videopanel,
            text="Loading...",
            bg="#181915",
            fg="#373734",
            font=(
                "Source Code Pro Medium",
                20)).pack(
            fill=BOTH,
            expand=True)
        self.videopanel.pack(fill=BOTH, expand=1)

        self.initPanel()

        size = (1600, 900)
        x = int(self.parent.winfo_screenwidth() / 2 - size[0] / 2)
        y = int(self.parent.winfo_screenheight() / 2 - size[1] / 2)
        self.parent.geometry("{}x{}+{}+{}".format(*size, x, y))
        self.parent.iconbitmap("icons/app_icon/icon.ico")
        # self.parent.iconphoto(False, self.image("app_icon/icon.ico", (128, 128)))

        self.parent.minsize(width=550, height=300)
        self.parent.bind('<Escape>', lambda e: self.toggleFullscreen())
        self.parent.bind('<KeyPress>', self.keyHandler)
        self.parent.bind('<Motion>', self.mouseHandler)
        self.mouseHandler()  # Start the loop immediately
        self.parent.protocol("WM_DELETE_WINDOW", self.OnClose)
        self.parent.lift()

    def initPanel(self):
        self.hidingFrame = Frame(self.parent, bg="#282923")

        self.infoLblFrame = Frame(self.hidingFrame, bg="#181915")
        self.subLbl = Label(
            self.infoLblFrame,
            text="",
            bd=0,
            height=1,
            relief='solid',
            font=(
                "Source Code Pro Medium",
                13),
            bg="#181915",
            fg="#FFFFFF")
        self.subLbl.pack(side=TOP, expand=True, fill="both")

        self.audioLbl = Label(
            self.infoLblFrame,
            text="",
            bd=0,
            height=1,
            relief='solid',
            font=(
                "Source Code Pro Medium",
                13),
            bg="#181915",
            fg="#FFFFFF")
        self.audioLbl.pack(side=BOTTOM, expand=True, fill="both")
        self.infoLblFrame.pack(side=TOP, expand=True, fill="both")

        kwargs = {
            'bd': 0,
            'height': 1,
            'relief': 'solid',
            'font': (
                "Source Code Pro Medium",
                13),
            'activebackground': "#282923",
            'activeforeground': "#FFFFFF",
            'bg': "#181915",
            'fg': "#FFFFFF",
        }

        img = self.image("back.png", (25, 25))
        b = Button(
            self.hidingFrame,
            image=img,
            command=self.timeBack,
            **kwargs)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("pause.png", (25, 25))
        self.playButton = Button(
            self.hidingFrame,
            image=img,
            command=self.togglePause,
            **kwargs)
        self.playButton.image = img
        self.playButton.pack(side=LEFT, expand=True, fill="both")

        img = self.image("next.png", (25, 25))
        b = Button(
            self.hidingFrame,
            image=img,
            command=self.timeForward,
            **kwargs)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("left.png", (25, 25))
        b = Button(
            self.hidingFrame,
            image=img,
            command=self.playlistNext,
            **kwargs)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("fullscreen.png", (25, 25))
        b = Button(
            self.hidingFrame,
            image=img,
            command=self.toggleFullscreen,
            **kwargs)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("right.png", (25, 25))
        b = Button(
            self.hidingFrame,
            image=img,
            command=self.playlistBack,
            **kwargs)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        self.posLbl = Label(self.hidingFrame, text="00:00", font=(
            "Source Code Pro Medium", 13), bg="#282923", fg="#FFFFFF")
        self.posLbl.pack(side=LEFT, fill="both", padx=10)

        Button(
            self.hidingFrame,
            text="-",
            command=self.volumeDown,
            **kwargs
        ).pack(
            side=LEFT,
            expand=True,
            fill="both")

        self.soundLbl = Label(self.hidingFrame, text="100%", font=(
            "Source Code Pro Medium", 13), bg="#282923", fg="#FFFFFF")
        self.soundLbl.pack(side=LEFT, fill="both", padx=10)

        Button(
            self.hidingFrame,
            text="+",
            command=self.volumeUp, 
            **kwargs
        ).pack(
            side=LEFT,
            expand=True,
            fill="both")

        self.titleLabel = Label(self.parent, text="", font=(
            "Source Code Pro Medium", 20), bg="#282923", fg="#FFFFFF")
        # self.hidingFrame.place(anchor="s",relx=0.5,rely=1,width=500,relheight=0.05)

    def keyHandler(self, e):
        if isinstance(e, Event):
            c = e.keysym
            s = e.state
        elif isinstance(e, tuple):
            c, s = e
            s = {None: 262152, 'ctrl': 262156,
                 'alt': 393224, 'shift': 262153}[s]
        else:
            return

        ctrl = (s & 0x4) != 0
        alt = (s & 0x20000) != 0
        shift = (s & 0x1) != 0

        settings = self.settings['player']['playerKeyBindings']

        keys = settings['None']

        if ctrl:
            ctrlKeys = settings['Ctrl']
            keys = dict_merge(keys, ctrlKeys)
            debug = 'ctrl+' + c
        elif alt:
            altKeys = settings['Alt']
            keys = dict_merge(keys, altKeys)
            debug = 'alt+' + c
        elif shift:
            shiftKeys = settings['Shift']
            keys = dict_merge(keys, shiftKeys)
            debug = 'shift+' + c
        else:
            debug = c

        if c in keys.keys():
            opt = map(lambda e: e.strip(), keys[c].split("-"))
            funcName, arg = next(opt), next(opt, None)
            if hasattr(self, funcName):
                func = getattr(self, funcName)
                if arg is None:
                    func()
                else:
                    func(arg)

    def mouseHandler(self, e=None):
        self.parent.config(cursor="arrow")
        self.lastMovement = time.time()

        if self.movementCheck is not None:
            self.parent.after_cancel(self.movementCheck)

        self.movementCheck = self.parent.after(
            self.hideCursorDelay * 1000, self.hideCursor)

        if e is not None:
            x, y = e.x_root - self.parent.winfo_rootx(), e.y_root - self.parent.winfo_rooty()
            
            t = time.time()
            if self.videoSize[2] + 1 < t: # Update screen size every 1 sec
                self.videoSize = (self.videopanel.winfo_width(), self.videopanel.winfo_height(), t)
    
            if 0 < x < self.videoSize[0] and 0.95 < y / self.videoSize[1] < 1:
                if self.hidden:
                    self.hidingFrame.place(
                        anchor="s", relx=0.5, rely=1, width=500, relheight=0.08)
                    self.hidden = False
                    self.showTitle()
            else:
                if not self.hidden and not str(e.widget).startswith(str(self.hidingFrame)):
                    self.hidingFrame.place_forget()
                    self.hidden = True

    def queryMousePosition(self):
        pt = POINT()
        windll.user32.GetCursorPos(byref(pt))
        root_x, root_y = (int(s) for s in self.parent.geometry().split("+")[1:])
        return pt.x-root_x, pt.y-root_y

    def hideCursor(self):
        # Hide mouse cursor when it's not moving
        if time.time() - self.lastMovement >= self.hideCursorDelay:
            self.parent.config(cursor="none")
        else:
            if self.movementCheck is not None:
                self.parent.after_cancel(self.movementCheck)
            self.movementCheck = self.parent.after(int(
                (self.hideCursorDelay - (time.time() - self.lastMovement)) * 1000), self.hideCursor)

    def updateDb(self):
        # Update last seen episode in db

        # self.log("Updating last_seen db",flush=True)
        def handler(self):
            if self.id is not None and self.database is not None:
                filename = self.playlist[self.index]
                thread_safe_db(self.database).set({
                    'id': self.id,
                    'last_seen': str(filename)
                },
                    table="anime"
                )

        threading.Thread(
            target=handler,
            args=(self,),
            daemon=True
        ).start()

    def getPlaylist(self, playlist):
        # Get titles and stream urls from playlist
        # Return a threading.Event, set when data is ready
        event = threading.Event()

        # From filepaths
        # Simply parse filename to extract a title

        self.playlist = playlist
        self.titles = [os.path.basename(f).rpartition(".")[
            0] for f in self.playlist]

        event.set()
        return event

    def condition_waiter(self, condition, callback, delay=100):
        # Wait for condition() to return True, without blocking the window
        if condition():
            return callback()
        else:
            self.parent.after(delay, self.condition_waiter,
                              condition, callback, delay)

    def toggle_iconify(self):
        # Hide player
        if self.is_iconified:
            self.parent.deiconify()
            self.togglePause(playing=True)
        else:
            self.parent.iconify()
            self.togglePause(playing=False)
        self.is_iconified = not self.is_iconified

    def callback_handler(self, cb, p):
        # Call callback when player exits
        p.join()
        if cb is not None:
            cb()

    def log(self, *args, **kwargs):
        # Simple wrapper for the log function
        return log(*args, **kwargs)


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


def dict_merge(a, b):
    "Used in place of the | operator in 3.10 for compatibility"
    new_dict = {}
    for d in (a, b):
        for k, v in d.items():
            new_dict[k] = v
    return new_dict


if __name__ == "__main__":
    freeze_support()
