import os
import threading
import time
import json
import queue
import sys
import traceback
import urllib.error

from tkinter import *
from PIL import Image, ImageTk
from ctypes import windll, Structure, c_long, byref
from multiprocessing import Process, freeze_support

from pytube import YouTube
import pytube.exceptions

from dbManager import thread_safe_db
from logger import log


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
            threading.Thread(target=self.callback_handler, args=(callback, p)).start()

        elif self.method == "THREAD":
            # Start player in new thread
            t = threading.Thread(target=self.start, args=args, kwargs=kwargs)
            t.start()
            threading.Thread(target=self.callback_handler, args=(callback, t)).start()

        else:
            # Start player in same thread
            # /!\ - Blocking!
            self.start(*args, **kwargs)
            if callback is not None:
                callback()

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
        self.is_iconified = False
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
        self.mouseHandler() # Start the loop immediately
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

    def mouseHandler(self, e=None):
        self.parent.config(cursor="arrow")
        self.lastMovement = time.time()

        if self.movementCheck is not None:
            self.parent.after_cancel(self.movementCheck)

        self.movementCheck = self.parent.after(
            self.hideCursorDelay * 1000, self.hideCursor)

    def queryMousePosition(self):
        pt = POINT()
        windll.user32.GetCursorPos(byref(pt))
        return pt.x, pt.y

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

    def getPlaylist(self, from_url, playlist):
        # Get titles and stream urls from playlist
        # Return a threading.Event, set when data is ready
        event = threading.Event()

        if from_url:
            # Fetch from urls in playlist
            que = queue.Queue()
            threads = []

            # Start threads
            for i, v in enumerate(playlist):
                t = threading.Thread(
                    target=self.getVideoUrl, 
                    args=(que, i, v)
                )
                threads.append(t)
                t.start()
            
            def condition(threads):
                while threads and not threads[0].is_alive():
                    # If thread is done, remove from list
                    threads.pop(0)
                
                return len(threads) == 0

            def callback(que, event):
                # Get threads output

                data = []
                while not que.empty():
                    data.append(que.get())

                data.sort(key=lambda e: e[0])

                self.titles, self.playlist = [], []
                
                for i, title, url in data:
                    self.titles.append(title)
                    self.playlist.append(url)
                
                event.set()

            self.condition_waiter(lambda t=threads: condition(t), lambda q=que, e=event: callback(q, e))
            return event

        else:
            # From filepaths
            # Simply parse filename to extract a title

            self.playlist = playlist
            self.titles = [os.path.basename(f).rpartition(".")[
                0] for f in self.playlist]

            event.set()
            return event

    @classmethod
    def getVideoUrl(self, que, i, v):
        def getTitle(v, q):
            # Avoid blocking main thread
            try:
                q.put(v.title)
            except Exception:
                q.put(None)

        video = YouTube(v)

        # Get title
        title = queue.Queue() # TODO - Use Value instead of Queue?
        threading.Thread(target=getTitle, args=(
            video, title), daemon=True).start()

        # Get streams
        try:
            streams = list(video.streams.filter(file_extension='mp4'))
        except pytube.exceptions.VideoUnavailable:
            log("Video not found for url", v)
            return
        except pytube.exceptions.RegexMatchError:
            log("Video not found for url", v)
            return
        except urllib.error.URLError:
            log("No internet connection!")
        except Exception as e:
            log("Error while fetching youtube video for url:",
                v, "-", e, "-", traceback.format_exc())
        else:
            # Filter streams
            def stream_filter(stream):
                score = 0
                if stream.resolution is not None:
                    score += int(stream.resolution[:-1]) # '360p' -> 360
                if stream.includes_audio_track:
                    score += 1
                return score

            streams.sort(key=stream_filter, reverse=True)
            stream = streams[0]
            que.put((i, stream.url, title.get()))

    def condition_waiter(self, condition, callback, delay=100):
        # Wait for condition() to return True, without blocking the window
        if condition():
            return callback()
        else:
            self.parent.after(delay, self.condition_waiter, condition, callback, delay)

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


if __name__ == "__main__":
    freeze_support()
