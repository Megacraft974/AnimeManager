import os
import threading
import time
import json
import queue
import re
import sys
import traceback
import urllib.error

from tkinter import *
from PIL import Image, ImageTk
from ctypes import windll, Structure, c_long, byref
from multiprocessing import Process

from pytube import YouTube
import pytube.exceptions

from dbManager import db
from logger import log


class BasePlayer:
    def __init__(self, *args, **kwargs):
        self.log = log
        if not hasattr(self, "method"):
            if "root" in kwargs:
                self.method = "NONE"
            else:
                self.method = "PROCESS"
        if self.method == "PROCESS":
            p = Process(target=self.start, args=args, kwargs=kwargs)
            p.start()
        elif self.method == "THREAD":
            t = threading.Thread(target=self.start, args=args, kwargs=kwargs)
            t.start()
        else:
            self.start(*args, **kwargs)

    def setup(self, root):
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
        self.movementCheck = None
        self.hideCursorDelay = 3
        self.root = root

    def image(self, file, size):
        return ImageTk.PhotoImage(
            Image.open(
                os.path.join(self.iconPath, file)
            ).resize(size, Image.ANTIALIAS),
            master=self.parent)

    def initWindow(self):
        if self.root is None:
            self.parent = Tk()  # Toplevel(root)
        else:
            self.parent = Toplevel(self.root)
        self.name = str(type(self)).split('.', 1)[-1].rsplit("_player", 1)[0].capitalize()
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
        self.parent.iconphoto(False, self.image("favicon.png", (128, 128)))

        self.parent.update()
        self.parent.minsize(width=550, height=300)
        self.parent.bind('<Escape>', lambda e: self.toggleFullscreen())
        self.parent.bind('<KeyPress>', self.keyHandler)
        self.parent.bind('<Motion>', self.mouseHandler)
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

        img = self.image("back.png", (25, 25))
        b = Button(
            self.hidingFrame,
            image=img,
            bd=0,
            height=1,
            relief='solid',
            font=(
                "Source Code Pro Medium",
                13),
            activebackground="#282923",
            activeforeground="#FFFFFF",
            bg="#181915",
            fg="#FFFFFF",
            command=self.timeBack)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("pause.png", (25, 25))
        self.playButton = Button(
            self.hidingFrame,
            image=img,
            bd=0,
            height=1,
            relief='solid',
            font=(
                "Source Code Pro Medium",
                13),
            activebackground="#282923",
            activeforeground="#FFFFFF",
            bg="#181915",
            fg="#FFFFFF",
            command=self.togglePause)
        self.playButton.image = img
        self.playButton.pack(side=LEFT, expand=True, fill="both")

        img = self.image("next.png", (25, 25))
        b = Button(
            self.hidingFrame,
            image=img,
            bd=0,
            height=1,
            relief='solid',
            font=(
                "Source Code Pro Medium",
                13),
            activebackground="#282923",
            activeforeground="#FFFFFF",
            bg="#181915",
            fg="#FFFFFF",
            command=self.timeForward)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("left.png", (25, 25))
        b = Button(
            self.hidingFrame,
            image=img,
            bd=0,
            height=1,
            relief='solid',
            font=(
                "Source Code Pro Medium",
                13),
            activebackground="#282923",
            activeforeground="#FFFFFF",
            bg="#181915",
            fg="#FFFFFF",
            command=self.playlistNext)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("fullscreen.png", (25, 25))
        b = Button(
            self.hidingFrame,
            image=img,
            bd=0,
            height=1,
            relief='solid',
            font=(
                "Source Code Pro Medium",
                13),
            activebackground="#282923",
            activeforeground="#FFFFFF",
            bg="#181915",
            fg="#FFFFFF",
            command=self.toggleFullscreen)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("right.png", (25, 25))
        b = Button(
            self.hidingFrame,
            image=img,
            bd=0,
            height=1,
            relief='solid',
            font=(
                "Source Code Pro Medium",
                13),
            activebackground="#282923",
            activeforeground="#FFFFFF",
            bg="#181915",
            fg="#FFFFFF",
            command=self.playlistBack)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        self.posLbl = Label(self.hidingFrame, text="00:00", font=(
            "Source Code Pro Medium", 13), bg="#282923", fg="#FFFFFF")
        self.posLbl.pack(side=LEFT, fill="both", padx=10)

        Button(
            self.hidingFrame,
            text="-",
            bd=0,
            height=1,
            relief='solid',
            font=(
                "Source Code Pro Medium",
                13),
            activebackground="#282923",
            activeforeground="#FFFFFF",
            bg="#181915",
            fg="#FFFFFF",
            command=self.volumeDown).pack(
            side=LEFT,
            expand=True,
            fill="both")

        self.soundLbl = Label(self.hidingFrame, text="100%", font=(
            "Source Code Pro Medium", 13), bg="#282923", fg="#FFFFFF")
        self.soundLbl.pack(side=LEFT, fill="both", padx=10)

        Button(
            self.hidingFrame,
            text="+",
            bd=0,
            height=1,
            relief='solid',
            font=(
                "Source Code Pro Medium",
                13),
            activebackground="#282923",
            activeforeground="#FFFFFF",
            bg="#181915",
            fg="#FFFFFF",
            command=self.volumeUp).pack(
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
            keys = keys | ctrlKeys
            debug = 'ctrl+' + c
        elif alt:
            altKeys = settings['Alt']
            keys = keys | altKeys
            debug = 'alt+' + c
        elif shift:
            shiftKeys = settings['Shift']
            keys = keys | shiftKeys
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

    def mouseHandler(self, e):
        self.parent.config(cursor="arrow")
        self.lastMovement = time.time()
        if self.movementCheck is not None:
            self.parent.after_cancel(self.movementCheck)
        self.movementCheck = self.parent.after(3 * 1000, self.hideCursor)

    def queryMousePosition(self):
        pt = POINT()
        windll.user32.GetCursorPos(byref(pt))
        return pt.x, pt.y

    def hideCursor(self):
        if time.time() - self.lastMovement >= self.hideCursorDelay:
            self.parent.config(cursor="none")

    def updateDb(self):
        # self.log("Updating last_seen db",flush=True)
        def handler(self):
            if self.id is not None and self.database is not None:
                filename = self.playlist[self.index]
                db(self.database).set(
                    {'id': self.id, 'last_seen': str(filename)}, table="anime")
        self.thread = threading.Thread(target=handler, args=(self,))
        self.thread.start()

    def getPlaylist(self, url, playlist):
        if url:
            que = queue.Queue()
            threads = []
            for i, v in enumerate(playlist):
                t = threading.Thread(target=self.getVideoUrl, args=(que, i, v))
                threads.append(t)
                t.start()
            for t in threads:
                try:
                    while t.is_alive():
                        time.sleep(1 / 60)
                        self.parent.update()
                except BaseException:
                    self.parent.after(1, self.OnClose)  # TODO - Really useful?
                    break
            self.playlist = []
            while not que.empty():
                self.playlist.append(que.get())
            self.playlist.sort(key=lambda e: e[0])
            self.titles = [e[2] for e in self.playlist]
            self.playlist = [e[1] for e in self.playlist]
        else:
            self.playlist = playlist
            self.titles = [os.path.basename(f).rpartition(".")[
                0] for f in self.playlist]

    def getVideoUrl(self, que, i, v):  # TODO - Ignore self
        def getTitle(v, q):
            try:
                q.put(v.title)
            except BaseException:
                q.put(None)
        video = YouTube(v)
        title = queue.Queue()
        threading.Thread(target=getTitle, args=(video, title)).start()

        try:
            streams = list(video.streams.filter(file_extension='mp4'))
        except pytube.exceptions.VideoUnavailable:
            log("Video not found for url", v)
            return
        except pytube.exceptions.VideoPrivate:
            log("The video is private!")
            return
        except urllib.error.URLError:
            log("No internet connection!")
        except BaseException as e:
            log("Error while fetching youtube video for url:", v, "-", e, "- Streams:\n   ", "\n   ".join(video.streams), "\n-", traceback.format_exc())
        else:
            streams.sort(key=lambda s: int(
                s.resolution[:-1]) if s.resolution is not None and s.includes_audio_track else 0, reverse=True)
            stream = streams[0]
            que.put((i, stream.url, title.get()))


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


if __name__ == "__main__":  # TODO - Move somewhere else
    path = "D:/Animes/"
    if not os.path.isdir(path):
        from tkinter.filedialog import askdirectory
        fen = Tk()
        fen.withdraw()
        path = askdirectory(parent=fen, title="Choose anime folder")
        fen.destroy()
        if path == "":
            raise SystemExit("No folder selected!")

    folders = [path]
    files = []
    while len(folders) > 0:
        folder = folders.pop()
        for f in os.listdir(folder):
            f = os.path.join(folder, f)
            if os.path.isdir(f):
                folders.append(f)
            elif os.path.isfile(f):
                files.append(f)
    fileFormats = ('mkv', 'mp4')
    playlist = []
    playlist = [f for f in files if f.rsplit('.', 1)[-1] in fileFormats]
    log("Root folder: {} - Files: {} - Videos: {}".format(path,
                                                          len(files), len(playlist)))

    # MpvPlayer(["https://youtu.be/tlTKTTt47WE"],0,url=True)
    fen = Tk()
    Button(fen, text="yoooo", command=log).pack()
    # MpvPlayer(playlist, 0, root=fen)
    VlcPlayer(playlist, 0)
    # FFPlayer(playlist,0)
    fen.mainloop()
