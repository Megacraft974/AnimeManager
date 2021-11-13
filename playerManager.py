import os
import threading
import time
import json
from tkinter import *
from PIL import Image, ImageTk
from dbManager import db
from utils import queryMousePosition
from multiprocessing import Process

try:
    import vlc
    from multiprocessing import Value, Manager
    import urllib
except BaseException:
    pass
try:
    from ffpyplayer.player import MediaPlayer
    import subprocess
    import re
except BaseException:
    pass
try:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
    os.environ['PATH'] = path + ";" + os.environ["PATH"]
    import mpv
    import sys
    import queue
    from pytube import YouTube
    import pytube.exceptions
except BaseException:
    pass


class Player:
    def __init__(self, *args, **kwargs):
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
            cwd = os.path.dirname(os.path.realpath(__file__))
        except NameError:
            cwd = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.iconPath = os.path.join(cwd, "icons")
        appdata = os.path.join(os.getenv('APPDATA'), "AnimeManager")
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
        return ImageTk.PhotoImage(Image.open(os.path.join(self.iconPath, file)).resize(
            size, Image.ANTIALIAS), master=self.parent)

    def initWindow(self):
        if self.root is None:
            self.parent = Tk()  # Toplevel(root)
        else:
            self.parent = Toplevel(self.root)
        self.parent.title("Mpv Media Player")

        self.videopanel = Frame(self.parent)
        Label(self.videopanel, text="Loading...", bg="#181915", fg="#373734", font=("Source Code Pro Medium", 20)
              ).pack(fill=BOTH, expand=True)
        self.videopanel.pack(fill=BOTH, expand=1)

        self.initPanel()

        size = (1600, 900)
        x = int(self.parent.winfo_screenwidth() / 2 - size[0] / 2)
        y = int(self.parent.winfo_screenheight() / 2 - size[1] / 2)
        self.parent.geometry("{}x{}+{}+{}".format(*size, x, y))

        self.parent.update()
        self.parent.minsize(width=550, height=300)
        self.parent.bind('<Escape>', lambda e: self.toggleFullscreen())
        self.parent.bind('<KeyPress>', self.keyHandler)
        self.parent.bind('<Motion>', self.mouseHandler)
        self.parent.protocol("WM_DELETE_WINDOW", self.OnClose)
        self.parent.lift()

    def initPanel(self):
        # TODO - Add icon
        self.hidingFrame = Frame(self.parent, bg="#282923")

        self.infoLblFrame = Frame(self.hidingFrame, bg="#181915")
        self.subLbl = Label(self.infoLblFrame, text="", bd=0, height=1, relief='solid',
                            font=("Source Code Pro Medium", 13), bg="#181915", fg="#FFFFFF")
        self.subLbl.pack(side=TOP, expand=True, fill="both")

        self.audioLbl = Label(self.infoLblFrame, text="", bd=0, height=1, relief='solid',
                              font=("Source Code Pro Medium", 13), bg="#181915", fg="#FFFFFF")
        self.audioLbl.pack(side=BOTTOM, expand=True, fill="both")
        self.infoLblFrame.pack(side=TOP, expand=True, fill="both")

        img = self.image("back.png", (25, 25))
        b = Button(self.hidingFrame, image=img, bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground="#282923", activeforeground="#FFFFFF", bg="#181915", fg="#FFFFFF",
                   command=self.timeBack)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("pause.png", (25, 25))
        self.playButton = Button(self.hidingFrame, image=img, bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                                 activebackground="#282923", activeforeground="#FFFFFF", bg="#181915", fg="#FFFFFF",
                                 command=self.togglePause)
        self.playButton.image = img
        self.playButton.pack(side=LEFT, expand=True, fill="both")

        img = self.image("next.png", (25, 25))
        b = Button(self.hidingFrame, image=img, bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground="#282923", activeforeground="#FFFFFF", bg="#181915", fg="#FFFFFF",
                   command=self.timeForward)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("left.png", (25, 25))
        b = Button(self.hidingFrame, image=img, bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground="#282923", activeforeground="#FFFFFF", bg="#181915", fg="#FFFFFF",
                   command=self.playlistNext)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("fullscreen.png", (25, 25))
        b = Button(self.hidingFrame, image=img, bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground="#282923", activeforeground="#FFFFFF", bg="#181915", fg="#FFFFFF",
                   command=self.toggleFullscreen)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        img = self.image("right.png", (25, 25))
        b = Button(self.hidingFrame, image=img, bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
                   activebackground="#282923", activeforeground="#FFFFFF", bg="#181915", fg="#FFFFFF",
                   command=self.playlistBack)
        b.image = img
        b.pack(side=LEFT, expand=True, fill="both")

        self.posLbl = Label(self.hidingFrame, text="00:00", font=(
            "Source Code Pro Medium", 13), bg="#282923", fg="#FFFFFF")
        self.posLbl.pack(side=LEFT, fill="both", padx=10)

        Button(self.hidingFrame, text="-", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
               activebackground="#282923", activeforeground="#FFFFFF", bg="#181915", fg="#FFFFFF",
               command=self.volumeDown).pack(side=LEFT, expand=True, fill="both")

        self.soundLbl = Label(self.hidingFrame, text="100%", font=(
            "Source Code Pro Medium", 13), bg="#282923", fg="#FFFFFF")
        self.soundLbl.pack(side=LEFT, fill="both", padx=10)

        Button(self.hidingFrame, text="+", bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 13),
               activebackground="#282923", activeforeground="#FFFFFF", bg="#181915", fg="#FFFFFF",
               command=self.volumeUp).pack(side=LEFT, expand=True, fill="both")

        self.titleLabel = Label(self.parent, text="", font=(
            "Source Code Pro Medium", 20), bg="#282923", fg="#FFFFFF")
        # self.hidingFrame.place(anchor="s",relx=0.5,rely=1,width=500,relheight=0.05)

    def keyHandler(self, e):
        if type(e) == Event:
            c = e.keysym
            s = e.state
        elif type(e) == tuple:
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

        # print(debug,flush=True)

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
        self.movementCheck = self.parent.after(5 * 1000, self.hideCursor)

    def hideCursor(self):
        if time.time() - self.lastMovement >= self.hideCursorDelay:
            self.parent.config(cursor="none")


class VlcPlayer(Player):
    def __init__(self, *args, **kwargs):
        self.method = "NONE"
        super().__init__(*args, **kwargs)

    def start(self, *args, **kwargs):
        states = Manager().dict()
        states['running'] = 0
        states['index'] = args[1]
        states['fullscreen'] = False
        state = Value("i", -1, lock=False)
        videoIndex = Value("i", args[1], lock=False)

        while states['running'] != -1:
            # VlcPlayer(*args,**(kwargs|{"stopFlag":state,"indexFlag":videoIndex}))
            p = Process(target=self._start, args=args,
                        kwargs=kwargs | {'states': states})
            p.start()
            p.join()
            print(states)
            # time.sleep(5)

    def _start(self, playlist, video=0, id=None, dbPath=None,
               stopFlag=None, indexFlag=None, states=None, root=None):
        super().setup(root)

        self.playlist = playlist
        # self.video = self.playlist[video]
        self.index = video
        self.id = id
        self.database = dbPath

        self.hidden = False
        # self.fullscreen = False
        self.paused = False
        self.ctrl = False
        self.alt = False
        self.threadLock = False
        self.titleLock = False
        self.stopped = False
        if states is None:
            self.states = {"running": -1,
                           "index": self.indexFlag, "fullscreen": False}
        else:
            self.states = states

        self.fullscreen = self.states['fullscreen']

        if self.states['index'] != self.index:
            self.index = self.states['index']

        self.spuTrack = -1
        self.audioTrack = -1

        self.initWindow()

        self.getNewPlayer()

        self.volume = 100
        self.OnVolume()

        devices = []
        mods = self.player.audio_output_device_enum()
        if mods:
            mod = mods
            while mod:
                mod = mod.contents
                if 'Casque (2- JBL TUNE510BT Stereo)' in str(mod.description):
                    self.player.audio_output_device_set(None, mod.device)
                    break
                mod = mod.next

        vlc.libvlc_audio_output_device_list_release(mods)

        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())

        print("Playing")

        # if self.stopFlag.value != -1:
        if self.states['running'] != -1:
            self.player.set_time(self.states['running'])

        self.showTitle()
        self.updateDb()
        self.updateSubLbl()
        self.updateAudioLbl()

        self.parent.after(100, self.OnTick)

        if self.root is None:
            self.parent.mainloop()

    def toggleFullscreen(self, *_):
        self.fullscreen = not self.fullscreen
        self.states['fullscreen'] = self.fullscreen
        self.parent.attributes("-fullscreen", self.fullscreen)
        self.parent.update()
        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())

    def getSubsList(self):
        return dict(self.player.video_get_spu_description())
        # subs = []
        # mods = self.player.video_get_spu_description()
        # if mods:
        #	 mod = mods
        #	 while mod:
        #		 mod = mod.contents
        #		 subs.append(mod.id)
        #		 mod = mod.next
        # print(subs)
        # return subs

    def getAudioList(self):
        return dict(self.player.audio_get_track_description())
        # print(mods)
        # if mods:
        #	 mod = mods
        #	 while mod:
        #		 mod = mod.contents
        #		 tracks.append(mod.id)
        #		 mod = mod.next
        # return tracks

    def changeSubs(self, sub):
        # self.spuTrack = sub
        vlc.libvlc_video_set_spu(self.player, sub)
        self.updateSubLbl()

    def updateSubLbl(self):
        i = self.player.video_get_spu()
        subDesc = self.getSubsList()
        if len(subDesc) > 1:
            text = subDesc[i].decode()
            self.subLbl['text'] = "Sub {}/{} - {}".format(
                list(subDesc.keys()).index(i) + 1, len(subDesc), text)
            self.subLbl.update()
        else:
            self.parent.after(100, self.updateSubLbl)

    def changeAudio(self, track):
        vlc.libvlc_audio_set_track(self.player, track)
        self.updateAudioLbl()

    def updateAudioLbl(self):
        i = self.player.audio_get_track()
        desc = self.getAudioList()
        # desc = self.player.audio_get_track_description()
        if len(desc) > 0:
            # desc = desc[i][1].decode()
            text = desc[i].decode()
            self.audioLbl['text'] = "Audio {}/{} - {}".format(
                list(desc.keys()).index(i) + 1, len(desc), text)
        else:
            self.parent.after(1000, self.updateAudioLbl)

    # --
    def audioTrackNext(self):
        audio = self.getSubsList()
        current = self.player.audio_get_track()
        audioIndex = list(audio.keys()).index(current)
        audioIndex = (audioIndex + 2) % len(audio) - 1
        self.changeAudio(list(audio.keys())[audioIndex])

    def audioTrackBack(self):
        audio = self.getSubsList()
        current = self.player.audio_get_track()
        audioIndex = list(audio.keys()).index(current)
        audioIndex = (audioIndex) % len(audio) - 1
        self.changeAudio(list(audio.keys())[audioIndex])

    def subTrackNext(self):
        subs = self.getSubsList()
        current = self.player.video_get_spu()
        subsIndex = list(subs.keys()).index(current)
        subsIndex = (subsIndex + 2) % len(subs) - 1
        self.changeSubs(list(subs.keys())[subsIndex])

    def subTrackBack(self):
        subs = self.getSubsList()
        current = self.player.video_get_spu()
        subsIndex = list(subs.keys()).index(current)
        subsIndex = (subsIndex) % len(subs) - 1
        self.changeSubs(list(subs.keys())[subsIndex])

    def playlistBack(self):
        self.changeVideo(-1)

    def playlistNext(self):
        self.changeVideo(1)

    def chapterBack(self):
        pass  # TODO

    def chapterNext(self):
        pass  # TODO

    def timeForward(self, t=0):
        self.OnTime(t)

    def timeBack(self, t=0):
        self.OnTime(-t)

    def volumeUp(self, value=0):
        self.OnVolume(value)

    def volumeDown(self, value=0):
        self.OnVolume(-value)

    def togglePause(self):
        self.OnPlay()
    # --

    def getNewPlayer(self):
        try:
            self.player.stop()
        except BaseException:
            pass
        try:
            self.Instance.release()
            del self.Instance
        except BaseException:
            pass
        self.Instance = vlc.Instance()
        self.Instance.log_unset()
        self.player = self.Instance.media_player_new()
        self.player.set_mrl(self.playlist[self.index])
        self.player.play()

        h = self.videopanel.winfo_id()
        self.player.set_hwnd(h)

        def cb(e):
            threading.Thread(target=self.changeVideo, args=(1,)).start()
        events = self.player.event_manager()
        # lambda e:self.changeVideo(1))
        events.event_attach(vlc.EventType().MediaPlayerEndReached, cb)

    def changeVideo(self, i):
        if self.threadLock:
            return
        self.threadLock = True
        self.updateDb()

        subs = self.getSubsList()
        current = self.player.video_get_spu()
        if current != -1:
            subsIndex = list(subs.keys()).index(current)
        else:
            subsIndex = -1

        audio = self.getAudioList()
        current = self.player.audio_get_track()
        if current != -1:
            audioIndex = list(audio.keys()).index(current)
        else:
            audioIndex = -1

        if self.index + i >= len(self.playlist):
            self.OnClose()
            return
        self.index = self.index + i
        self.states['running'] = 0
        self.states['index'] = self.index

        self.getNewPlayer()

        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())
        time.sleep(2)

        self.showTitle()
        subs = self.getSubsList()
        if len(subs) > subsIndex:
            self.changeSubs(list(subs.keys())[subsIndex])

        audio = self.getAudioList()
        if len(audio) > audioIndex:
            self.changeAudio(list(audio.keys())[audioIndex])
        self.threadLock = False

    def showTitle(self, animations=True):
        def animate(start, stop, time, fps=60, p=0):
            step = 100 / (time * fps)
            current = int((stop - start) * p / 100 + start)

            self.titleLabel.place(anchor="n", relx=0.5,
                                  y=current, relwidth=1, height=50)
            self.parent.update()
            p += step

            if start < stop:
                check = current < stop
            else:
                check = current > stop
            if not self.stopped and check:
                self.parent.after(
                    int(1000 / fps), lambda: animate(start, stop, time, fps, p))
            else:
                if start > stop:
                    self.titleLock = False

        if self.titleLock:
            return
        self.titleLock = True
        title = urllib.parse.unquote(self.player.get_media().get_mrl()).rsplit(
            "/", 1)[1].rsplit(".", 1)[0]
        # print(title)
        self.titleLabel['text'] = title
        # lbl.place(anchor="n",relx=0.5,rely=0,relwidth=1,height=50)
        if animations:
            try:
                animate(-50, 0, 1)
                self.parent.after(3000, lambda: animate(0, -50, 1))
            except BaseException:
                pass
        try:
            if not self.stopped:
                self.parent.after(5000, lbl.place_forget)
        except BaseException:
            pass

    def OnTime(self, t=0):
        # a
        self.player.set_time(int(t * 1e3) + self.player.get_time())

    def OnTick(self):
        currentTime = self.player.get_time()
        sec = int(currentTime / 1000)
        mins = (sec // 60) % 60
        hours = sec // 3600
        currentTimeText = (str(hours) + ":" if hours > 0 else "") + \
            str(mins).zfill(2) + ":" + str(sec % 60).zfill(2)
        totalTime = self.player.get_length()
        sec = int(totalTime / 1000)
        mins = (sec // 60) % 60
        hours = sec // 3600
        totalTimeText = (str(hours) + ":" if hours > 0 else "") + \
            str(mins).zfill(2) + ":" + str(sec % 60).zfill(2)

        try:
            self.posLbl['text'] = currentTimeText + " - " + totalTimeText
        except BaseException:
            pass

        # cursor = vlc.libvlc_video_get_cursor(self.player,0)[1]
        try:
            cursorX, cursorY = queryMousePosition()
        except BaseException:
            cursorX, cursorY = 0, 0
        cursorX, cursorY = cursorX - self.videopanel.winfo_rootx(), cursorY - \
            self.videopanel.winfo_rooty()
        # print(cursor)

        if 0.95 < cursorY / \
                self.videoSize[1] < 1 and 0 < cursorX < self.videoSize[0]:
            if self.hidden:
                self.hidingFrame.place(
                    anchor="s", relx=0.5, rely=1, width=500, relheight=0.08)
                self.hidden = False
                self.showTitle()
        else:
            if not self.hidden:
                self.hidingFrame.place_forget()
                self.hidden = True

        if not self.stopped:
            self.parent.after(100, self.OnTick)

    def OnPlay(self):
        self.paused = not self.paused
        self.player.pause()
        icon = "play" if self.paused else "pause"
        img = ImageTk.PhotoImage(file=os.path.join(
            self.iconPath, "{}.png".format(icon), size=(25, 25)))
        self.playButton['image'] = img
        self.playButton.image = img
        # self.playButton['text'] = "Pause" if self.paused else "Play"

    def OnVolume(self, value=0):
        self.volume = max(0, min(self.volume + value, 200))
        self.player.audio_set_volume(self.volume)
        self.soundLbl['text'] = str(self.volume) + "%"

    def updateDb(self):
        # print("Updating last_seen db",flush=True)
        def handler(self):
            if self.id is not None and self.database is not None:
                filename = self.playlist[self.index]
                db(self.database)(table="anime").set(
                    {'id': self.id, 'last_seen': str(filename)})
        self.thread = threading.Thread(target=handler, args=(self,))
        self.thread.start()

    def OnClose(self):
        print("Closing")
        if self.stopped:
            return
        self.stopped = True
        # self.stopFlag.value = 0
        self.states['running'] = -1
        self.parent.destroy()
        self.updateDb()
        try:
            self.player.stop()
        except BaseException:
            pass
        # self.parent.quit()


class FFPlayer(Player):
    def start(self, playlist, video=0, id=None, dbPath=None, root=None):
        super().setup(root)

        self.playlist = playlist
        self.index = video
        self.id = id
        self.database = dbPath

        self.hidden = False
        self.fullscreen = True
        self.paused = False
        self.ctrl = False
        self.alt = False
        self.threadLock = False
        self.titleLock = False
        self.stopped = False

        self.spuTrack = -1
        self.audioTrack = -1
        for s in self.getMetadata(self.playlist[self.index]).values():
            if s['DISPOSITION:default'] == "1":
                if s['codec_type'] == "audio":
                    self.audioTrack = int(s['index'])
                elif s['codec_type'] == "subtitle":
                    self.spuTrack = int(s['index'])

        self.initWindow()
        for c in self.videopanel.winfo_children():
            c.destroy()
        self.canvas = Canvas(self.videopanel)
        self.canvas.pack(fill=BOTH, expand=1)

        self.player_args = {}  # {'callback':self.playerCallback,'ff_opts':{'sync':'video'}}
        print(self.playlist[self.index])
        self.player = MediaPlayer(
            self.playlist[self.index], **self.player_args)

        self.volume = 100
        self.OnVolume()

        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())
        self.center = (self.videoSize[0] // 2, self.videoSize[1] // 2)

        self.showTitle()
        self.updateDb()
        self.updateSubLbl()
        self.updateAudioLbl()

        self.waitForFrames()

        print("Playing")

        self.play()

        self.parent.after(100, self.OnTick)

        if self.root is None:
            self.parent.mainloop()

    def play(self):
        frame, val = self.player.get_frame()
        # print(val)
        loop = self.parent.after(int(val * 1000), self.play)
        if val == 'eof':
            self.parent.after_cancel(loop)
            return
        elif frame is None:
            time.sleep(0.01)
        elif val != 0:
            img, t = frame
            self.updateImg(img, val)

    def playerCallback(self, selector, value):
        if selector == "display_sub":
            for i, v in enumerate(value):
                pass
                # print(i,v)

    def waitForFrames(self):
        frame = None
        while frame is None:
            frame = self.player.get_frame(True, True)[0]
            time.sleep(0.01)
        orgSize = self.player.get_metadata()['src_vid_size']
        self.ratio = orgSize[0] / orgSize[1]

    def resize(self, e):
        x, y = e.width, e.height
        self.center = (x // 2, y // 2)
        if x / y > self.ratio:
            x = -1
        else:
            y = -1
        self.player.set_size(width=x, height=y)
        self.videoSize = (x, y)

    def toggleFullscreen(self, *_):
        self.fullscreen = not self.fullscreen
        self.parent.attributes("-fullscreen", self.fullscreen)
        self.parent.update()
        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())

    def getSubsList(self):
        streams = {-1: {'TAG:title': 'Disabled'}}
        streams |= self.getMetadata(self.playlist[self.index], 'subtitle')
        return streams

    def getAudioList(self):
        streams = {-1: {'TAG:language': 'Disabled'}}
        streams |= self.getMetadata(self.playlist[self.index], 'audio')
        return streams

    def getMetadata(self, file, filter=""):
        cmd = "ffprobe -v error -show_entries stream=index,codec_name,codec_type:stream_tags=title,language:stream_disposition=default"
        output = subprocess.check_output(cmd.split(" ") + [file])
        # print(output.decode())
        pattern = r'(.*)=(.*)'
        matchs = re.findall(pattern, output.decode().replace("\r", ""))

        streams = {}
        for k, v in matchs:
            if v.isnumeric():
                v = int(v)
            if k == 'index':
                index = v
                streams[index] = {k: v}
            else:
                streams[index][k] = v

        for s in list(streams.keys()):
            if not filter in streams[s]['codec_type']:
                del streams[s]
        return streams

    def changeSubs(self, sub):
        self.spuTrack = sub
        self.player.request_channel('subtitle', 'close')
        if sub != -1:
            self.player.request_channel('subtitle', 'open', sub)
        self.updateSubLbl()

    def updateSubLbl(self):
        streams = self.getSubsList()
        desc = streams[self.spuTrack]['TAG:title']
        text = "Sub {}/{} - {}".format(list(streams.keys()
                                            ).index(self.spuTrack) + 1, len(streams), desc)
        self.subLbl['text'] = text

    def changeAudio(self, track):
        self.audioTrack = track
        self.player.request_channel('audio', 'close')
        if track != -1:
            self.player.request_channel('audio', 'open', track)
        self.updateAudioLbl()

    def updateAudioLbl(self):
        streams = self.getAudioList()
        desc = streams[self.audioTrack]['TAG:language']
        text = "Audio {}/{} - {}".format(list(streams.keys()
                                              ).index(self.audioTrack) + 1, len(streams), desc)
        self.audioLbl['text'] = text

    def changeVideo(self, i):
        self.updateDb()

        if self.index + 1 == len(self.playlist):
            self.OnClose()
            return
        self.index = (self.index + i) % len(self.playlist)
        self.player.close_player()
        self.player = MediaPlayer(
            self.playlist[self.index], **self.player_args)

        self.showTitle()
        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())
        self.waitForFrames()

    # --
    def audioTrackNext(self):
        i = self.player.audio
        if i == False:
            i = 0
        track = i + 1
        if track > len(self.audioTracks):
            track = False
        self.player.audio = track
        self.updateAudioLbl()

    def audioTrackBack(self):
        i = self.player.audio
        if i == False:
            i = len(self.audioTracks) + 1
        track = i - 1
        if track < 0:
            track = False
        self.player.audio = track
        self.updateAudioLbl()

    def subTrackNext(self):
        subs = self.getSubsList()
        sub = (self.spuTrack + 1) % len(subs) - 1
        self.changeSubs(subs)

    def subTrackBack(self):
        subs = self.getSubsList()
        sub = (self.spuTrack - 1) % len(subs) - 1
        self.changeSubs(subs)

    def changeVideo(self, i):
        if self.threadLock:
            return
        self.threadLock = True
        self.updateDb()

        sub, audio = self.player.sub, self.player.audio

        if self.index + i >= len(self.playlist):
            self.OnClose()
            return
        self.index = self.index + i

        self.player.play(self.playlist[self.index])

        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())
        time.sleep(2)

        self.showTitle()
        self.player.sub, self.player.audio = sub, audio
        self.threadLock = False

    def playlistBack(self):
        self.changeVideo(-1)

    def playlistNext(self):
        self.changeVideo(1)

    def chapterBack(self):
        c, maxC = self.player.chapter, self.player.chapters
        if maxC == 0:
            return
        if c is None:
            c = 0
        self.player.chapter = (c - 1) % self.player.chapters

    def chapterNext(self):
        c, maxC = self.player.chapter, self.player.chapters
        if maxC == 0:
            return
        if c is None:
            c = 0
        self.player.chapter = (c + 1) % self.player.chapters

    def timeForward(self, t=0):
        t = int(t)
        self.player.seek(t)

    def timeBack(self, t=0):
        t = int(t)
        self.player.seek(-t)

    def volumeUp(self, value=0):
        value = int(value)
        self.volume = max(0, min(self.volume + value, 200))
        self.player.volume = self.volume
        self.soundLbl['text'] = str(self.volume) + "%"

    def volumeDown(self, value=0):
        value = int(value)
        self.volume = max(0, min(self.volume - value, 200))
        self.player.volume = self.volume
        self.soundLbl['text'] = str(self.volume) + "%"

    def togglePause(self):
        self.paused = not self.paused
        self.player.pause = self.paused
        icon = "play" if self.paused else "pause"
        img = self.image("{}.png".format(icon), (25, 25))
        self.playButton['image'] = img
        self.playButton.image = img
        # self.playButton['text'] = "Pause" if self.paused else "Play"
    # --

    def showTitle(self, animations=True):
        def animate(start, stop, time, fps=60, p=0):
            step = 100 / (time * fps)
            current = int((stop - start) * p / 100 + start)

            self.titleLabel.place(anchor="n", relx=0.5,
                                  y=current, relwidth=1, height=50)
            self.parent.update()
            p += step

            if start < stop:
                check = current < stop
            else:
                check = current > stop
            if not self.stopped and check:
                self.parent.after(
                    int(1000 / fps), lambda: animate(start, stop, time, fps, p))
            else:
                if start > stop:
                    self.titleLock = False

        if self.titleLock:
            return
        self.titleLock = True
        title = self.playlist[self.index].rsplit("/", 1)[1].rsplit(".", 1)[0]
        # print(title)
        self.titleLabel['text'] = title
        # lbl.place(anchor="n",relx=0.5,rely=0,relwidth=1,height=50)
        if animations:
            try:
                animate(-50, 0, 1)
                self.parent.after(3000, lambda: animate(0, -50, 1))
            except BaseException:
                pass
        try:
            if not self.stopped:
                self.parent.after(5000, lbl.place_forget)
        except BaseException:
            pass

    def OnTime(self, t=0):
        # a
        self.player.seek(t, True)

    def OnPlay(self):
        self.paused = not self.paused
        self.player.set_pause(self.paused)
        icon = "play" if self.paused else "pause"
        img = ImageTk.PhotoImage(file=os.path.join(
            self.iconPath, "{}.png".format(icon)), size=(25, 25))
        self.playButton['image'] = img
        self.playButton.image = img
        # self.playButton['text'] = "Pause" if self.paused else "Play"

    def OnVolume(self, value=0):
        self.volume = max(0, min(self.volume + value, 200))
        self.player.set_volume(self.volume / 100)
        self.soundLbl['text'] = str(self.volume) + "%"

    def OnTick(self):
        frame = self.player.get_frame(True, True)
        currentTime = frame[0][1] if frame is not None else 0
        sec = int(currentTime / 1000)
        mins = (sec // 60) % 60
        hours = mins // 60
        currentTimeText = str(hours) if hours > 0 else "" + \
            str(mins).zfill(2) + ":" + str(sec % 60).zfill(2)
        totalTime = self.player.get_metadata()['duration']
        if totalTime is None:
            totalTime = 0
        sec = int(totalTime / 1000)
        mins = (sec // 60) % 60
        hours = mins // 60
        totalTimeText = str(hours) if hours > 0 else "" + \
            str(mins).zfill(2) + ":" + str(sec % 60).zfill(2)

        try:
            self.posLbl['text'] = currentTimeText + " - " + totalTimeText
        except BaseException:
            pass

        cursorX, cursorY = queryMousePosition()
        # cursorX, cursorY = cursorX-self.videopanel.winfo_rootx(), cursorY-self.videopanel.winfo_rooty()
        # print(cursor)

        if 0.95 < cursorY / \
                self.videoSize[1] < 1 and 0 < cursorX < self.videoSize[0]:
            if self.hidden:
                self.hidingFrame.place(
                    anchor="s", relx=0.5, rely=1, width=500, relheight=0.08)
                self.hidden = False
                self.showTitle()
        else:
            if not self.hidden:
                self.hidingFrame.place_forget()
                self.hidden = True

        if not self.stopped:
            self.parent.after(100, self.OnTick)

    def updateImg(self, img, delay):
        data = img.to_bytearray()[0]
        img2 = Image.frombytes("RGB", img.get_size(), bytes(data))

        tkImg = ImageTk.PhotoImage(img2)
        self.canvas.delete("all")
        self.canvas.create_image(self.center, image=tkImg)
        self.canvas.img = tkImg
        self.parent.update()
        # sleep(delay)

    def updateDb(self):
        print("Updating last_seen db", flush=True)

        def handler(self):
            if self.id is not None and self.database is not None:
                filename = self.playlist[self.index]
                db(self.database)(id=self.id, table="anime").set(
                    {'last_seen': str(filename)})
        self.thread = threading.Thread(target=handler, args=(self,))
        self.thread.start()

    def OnClose(self):
        print("Closing")
        if self.stopped:
            return
        self.stopped = True
        # self.stopFlag.value = 0
        self.updateDb()
        self.player.set_pause(True)
        self.parent.destroy()


class MpvPlayer(Player):
    def start(self, playlist, video=0, id=None,
              dbPath=None, url=False, root=None):
        super().setup(root)

        self.index = video % len(playlist)
        self.id = id
        self.database = dbPath

        self.hidden = False
        self.fullscreen = False
        self.paused = False
        self.ctrl = False
        self.alt = False
        self.threadLock = False
        self.titleLock = False
        self.stopped = False

        self.spuTrack = -1
        self.audioTrack = -1

        self.initWindow()

        self.getPlaylist(url, playlist)

        if len(self.playlist) == 0:
            print("No video found!")
            self.OnClose()
            return

        h = self.videopanel.winfo_id()
        self.player = mpv.MPV(wid=str(int(h)), ytdl=url)
        # print(self.player.property_observer('time-remaining')(self.auto_loop),flush=True) - TODO
        self.player.play(self.playlist[self.index])

        self.volume = 100
        self.volumeUp()

        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())

        print("Playing")

        self.showTitle()
        self.updateDb()
        self.updateSubLbl()
        self.updateAudioLbl()

        self.parent.after(100, self.OnTick)

        if self.root is None:
            self.parent.mainloop()

    def getAudio(self, i=None):
        self.audioTracks = [
            t for t in self.player.track_list if t['type'] == "audio"]
        if i is None:
            i = self.player.audio
        else:
            i = i % len(self.audioTracks)
        track = None
        for t in self.audioTracks:
            if t['id'] == i:
                track = t
                break
        return track

    def updateAudioLbl(self):
        track = self.getAudio()
        if track is not None:
            if 'title' in track.keys():
                text = track['title']
            else:
                text = "Unknown"
            self.audioLbl['text'] = "Audio {}/{} - {}".format(
                track["id"], len(self.audioTracks), text)
        else:
            self.audioLbl['text'] = "Audio 0/{} - Disabled".format(
                len(self.audioTracks))
        self.audioLbl.update()

    def audioTrackNext(self):
        i = self.player.audio
        if i == False:
            i = 0
        track = i + 1
        if track > len(self.audioTracks):
            track = False
        self.player.audio = track
        self.updateAudioLbl()

    def audioTrackBack(self):
        i = self.player.audio
        if i == False:
            i = len(self.audioTracks) + 1
        track = i - 1
        if track < 0:
            track = False
        self.player.audio = track
        self.updateAudioLbl()

    def getSub(self, i=None):
        self.subTracks = [
            t for t in self.player.track_list if t['type'] == "sub"]
        if i is None:
            i = self.player.sub
        else:
            i = i % self.subTracks
        track = None
        for t in self.subTracks:
            if t['id'] == i:
                track = t
                break
        return track

    def updateSubLbl(self):
        track = self.getSub()
        if track is not None:
            if 'title' in track.keys():
                text = track['title']
            else:
                text = "Unknown"
            self.subLbl['text'] = "Sub {}/{} - {}".format(
                track["id"], len(self.subTracks), text)
        else:
            self.subLbl['text'] = "Sub 0/{} - Disabled".format(
                len(self.subTracks))
        self.subLbl.update()

    def subTrackNext(self):
        i = self.player.sub
        if i == False:
            i = 0
        track = i + 1
        if track > len(self.subTracks):
            track = False
        self.player.sub = track
        self.updateSubLbl()

    def subTrackBack(self):
        i = self.player.sub
        if i == False:
            i = len(self.subTracks) + 1
        track = i - 1
        if track < 0:
            track = False
        self.player.sub = track
        self.updateSubLbl()

    def changeVideo(self, i):
        if self.threadLock:
            return
        self.threadLock = True
        self.updateDb()

        sub, audio = self.player.sub, self.player.audio

        if self.index + i >= len(self.playlist):
            self.OnClose()
            return
        self.index = self.index + i

        self.player.play(self.playlist[self.index])

        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())
        time.sleep(2)

        self.showTitle()
        self.player.sub, self.player.audio = sub, audio
        self.threadLock = False

    def playlistBack(self):
        self.changeVideo(-1)

    def playlistNext(self):
        self.changeVideo(1)

    def chapterBack(self):
        c, maxC = self.player.chapter, self.player.chapters
        if maxC == 0:
            return
        if c is None:
            c = 0
        self.player.chapter = (c + 1) % self.player.chapters

    def chapterNext(self):
        c, maxC = self.player.chapter, self.player.chapters
        if maxC == 0:
            return
        if c is None:
            c = 0
        self.player.chapter = (c + 1) % self.player.chapters

    def timeForward(self, t=0):
        t = int(t)
        self.player.seek(t)

    def timeBack(self, t=0):
        t = int(t)
        self.player.seek(-t)

    def volumeUp(self, value=0):
        value = int(value)
        self.volume = max(0, min(self.volume + value, 200))
        self.player.volume = self.volume
        self.soundLbl['text'] = str(self.volume) + "%"

    def volumeDown(self, value=0):
        value = int(value)
        self.volume = max(0, min(self.volume - value, 200))
        self.player.volume = self.volume
        self.soundLbl['text'] = str(self.volume) + "%"

    def togglePause(self):
        self.paused = not self.paused
        self.player.pause = self.paused
        icon = "play" if self.paused else "pause"
        img = self.image("{}.png".format(icon), (25, 25))
        self.playButton['image'] = img
        self.playButton.image = img
        # self.playButton['text'] = "Pause" if self.paused else "Play"

    def toggleFullscreen(self):
        self.fullscreen = not self.fullscreen
        self.parent.attributes("-fullscreen", self.fullscreen)
        self.parent.update()
        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())

    def showTitle(self, animations=True):
        # TODO - Use time.time instead of a counter -> better usage of the fps
        def animate(start, stop, time, fps=60, p=0):
            step = 100 / (time * fps)
            current = int((stop - start) * p / 100 + start)

            self.titleLabel.place(anchor="n", relx=0.5,
                                  y=current, relwidth=1, height=50)
            self.parent.update()
            p += step

            if start < stop:
                check = current < stop
            else:
                check = current > stop
            if not self.stopped and check:
                self.parent.after(
                    int(1000 / fps), lambda: animate(start, stop, time, fps, p))
            else:
                if start > stop:
                    self.titleLock = False

        # title = self.player.filename
        title = self.titles[self.index]
        if title is None:
            return self.parent.after(100, lambda: self.showTitle(animations))
        self.titleLabel['text'] = title

        if self.titleLock:
            return
        self.titleLock = True
        # lbl.place(anchor="n",relx=0.5,rely=0,relwidth=1,height=50)
        if animations:
            try:
                animate(-50, 0, 1)
                self.parent.after(3000, lambda: animate(0, -50, 1))
            except BaseException:
                pass
        try:
            if not self.stopped:
                self.parent.after(5000, lbl.place_forget)
        except BaseException:
            pass

    def OnTick(self):
        if self.stopped:
            return
        currentTime = self.player.time_pos
        if currentTime is None:
            currentTime = 0
        totalTime = self.player.duration
        if totalTime is None:
            leftTime = self.player.time_remaining
            if leftTime is None:
                leftTime = 0
            totalTime = currentTime + leftTime

        sec = int(currentTime)
        mins = (sec // 60) % 60
        hours = sec // 3600
        currentTimeText = (str(hours) + ":" if hours > 0 else "") + \
            str(mins).zfill(2) + ":" + str(sec % 60).zfill(2)

        sec = int(totalTime)
        mins = (sec // 60) % 60
        hours = sec // 3600
        totalTimeText = (str(hours) + ":" if hours > 0 else "") + \
            str(mins).zfill(2) + ":" + str(sec % 60).zfill(2)

        try:
            self.posLbl['text'] = currentTimeText + " - " + totalTimeText
        except BaseException:
            pass

        # cursor = vlc.libvlc_video_get_cursor(self.player,0)[1]
        try:
            cursorX, cursorY = queryMousePosition()
        except BaseException:
            cursorX, cursorY = 0, 0
        cursorX, cursorY = cursorX - self.videopanel.winfo_rootx(), cursorY - \
            self.videopanel.winfo_rooty()
        # print(cursor)

        if 0.95 < cursorY / \
                self.videoSize[1] < 1 and 0 < cursorX < self.videoSize[0]:
            if self.hidden:
                self.updateSubLbl()
                self.updateAudioLbl()
                self.hidingFrame.place(
                    anchor="s", relx=0.5, rely=1, width=500, relheight=0.08)
                self.hidden = False
                self.showTitle()
        else:
            if not self.hidden:
                self.hidingFrame.place_forget()
                self.hidden = True

        self.parent.after(100, self.OnTick)

    def auto_loop(self, _name, time):
        if time is None:
            return
        print(time, flush=True)
        if time < 0.5:
            print("NEXT FILE")
            self.playlistNext()

    def updateDb(self):
        # print("Updating last_seen db",flush=True)
        def handler(self):
            if self.id is not None and self.database is not None:
                filename = self.playlist[self.index]
                db(self.database)(table="anime").set(
                    {'id': self.id, 'last_seen': str(filename)})
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
                    self.parent.after(1, self.OnClose())
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

    def getVideoUrl(self, que, i, v):
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
            print("Video not found for url", v)
            return
        except pytube.exceptions.VideoPrivate:
            print("The video is private!")
            return
        else:
            streams.sort(key=lambda s: int(
                s.resolution[:-1]) if s.resolution is not None and s.includes_audio_track else 0, reverse=True)
            stream = streams[0]
            que.put((i, stream.url, title.get()))

    def OnClose(self):
        if self.stopped:
            return
        print("Closing")
        self.stopped = True
        self.parent.destroy()
        self.updateDb()
        try:
            self.player.stop()
        except Exception as e:
            print("Error while stopping player:", type(e), e)
        print("Closed")
        # self.parent.quit()


if __name__ == "__main__":
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
    print("Root folder: {} - Files: {} - Videos: {}".format(path,
          len(files), len(playlist)))

    # MpvPlayer(["https://youtu.be/tlTKTTt47WE"],0,url=True)
    fen = Tk()
    Button(fen, text="yoooo", command=print).pack()
    MpvPlayer(playlist, 0, root=fen)
    fen.mainloop()
    # VlcPlayer(playlist,0)
    # FFPlayer(playlist,0)
