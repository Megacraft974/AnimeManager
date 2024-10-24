import time
import os
from .base_player import BasePlayer, dict_merge

try:
    lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'lib', 'libvlc.dll')
    import sys
    # TODO - Find it another way
    sys.path.append('C:\\Program Files (x86)\\VideoLAN\\VLC')
    
    os.environ['PATH'] += 'C:\\Program Files (x86)\\VideoLAN\\VLC' + os.sep + os.environ['PATH'] # TF??
    # is64bit = sys.maxsize > 2**32
    import vlc
except FileNotFoundError as e:
    vlc = None
except Exception as e:
    vlc = None
except SystemExit as e:
    vlc = None

import urllib.parse
from multiprocessing import Manager, Process


class VlcPlayer(BasePlayer):
    def __init__(self, *args, **kwargs):
        if vlc is None:
            # Couldn't import library
            self.log("Couldn't import vlc library!")
            return

        self.method = "NONE"
        super().__init__(*args, **kwargs)

    def start(self, *args, **kwargs):
        with Manager() as manager:
            states = manager.dict()
            states['running'] = 0
            states['index'] = args[1]
            states['fullscreen'] = False
            # state = manager.Value("i", -1, lock=False)
            # videoIndex = manager.Value("i", args[1], lock=False)

            start = time.time()
            while states['running'] != -1:
                if "root" in kwargs.keys():
                    del kwargs["root"]
                p = Process(target=self._start, args=args,
                            kwargs=dict_merge(kwargs, {'states': states}))
                p.start()
                p.join()
                self.log(states)
                time.sleep(max(0, time.time() - start + 10))

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

        # devices = []
        # mods = self.player.audio_output_device_enum()
        # if mods:
        #     mod = mods
        #     while mod:
        #         mod = mod.contents
        #         if 'Casque (2- JBL TUNE510BT Stereo)' in str(mod.description):
        #             self.player.audio_output_device_set(None, mod.device)
        #             break
        #         mod = mod.next

        # vlc.libvlc_audio_output_device_list_release(mods)

        self.log("Playing", self.playlist[self.index])

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

    def getSubsList(self):
        return dict(self.player.video_get_spu_description())
        # subs = []
        # mods = self.player.video_get_spu_description()
        # if mods:
        #     mod = mods
        #     while mod:
        #         mod = mod.contents
        #         subs.append(mod.id)
        #         mod = mod.next
        # self.log(subs)
        # return subs

    def getAudioList(self):
        return dict(self.player.audio_get_track_description())
        # self.log(mods)
        # if mods:
        #     mod = mods
        #     while mod:
        #         mod = mod.contents
        #         tracks.append(mod.id)
        #         mod = mod.next
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

    def togglePause(self, playing=None):
        self.OnPlay(playing=None)
    # --

    def getNewPlayer(self):
        try:
            self.player.stop()
        except Exception:
            pass
        try:
            self.Instance.release()
            del self.Instance
        except Exception:
            pass
        self.Instance = vlc.Instance('--verbose 3')
        self.Instance.log_unset()
        self.player = self.Instance.media_player_new()
        self.player.set_mrl(self.playlist[self.index])
        self.player.play()

        h = self.videopanel.winfo_id()
        self.player.set_hwnd(h)

        events = self.player.event_manager()
        
        events.event_attach(
            vlc.EventType().MediaPlayerEndReached, 
            lambda e:self.changeVideo(1))


    def changeVideo(self, i):
        if self.threadLock:
            return
        self.threadLock = True

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
        self.updateDb()
        
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
        # self.log(title)
        self.titleLabel['text'] = title

        if animations:
            try:
                animate(-50, 0, 1)
                self.parent.after(3000, lambda: animate(0, -50, 1))
            except Exception:
                pass
        try:
            if not self.stopped:
                self.parent.after(5000, self.titleLabel.place_forget)
        except Exception:
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
        except Exception:
            pass

        if not self.stopped:
            self.parent.after(100, self.OnTick)

    def OnPlay(self, playing=None):
        if playing is not None and not playing == self.paused:
            return
        self.paused = not self.paused
        self.player.pause()

        icon = "play" if self.paused else "pause"
        img = self.image(f"{icon}.png", (25, 25))

        self.playButton['image'] = img
        self.playButton.image = img
        # self.playButton['text'] = "Pause" if self.paused else "Play"

    def OnVolume(self, value=0):
        self.volume = max(0, min(self.volume + value, 200))
        self.player.audio_set_volume(self.volume)
        self.soundLbl['text'] = str(self.volume) + "%"

    def OnClose(self):
        self.log("Closing")
        if self.stopped:
            return
        self.stopped = True
        # self.stopFlag.value = 0
        self.states['running'] = -1
        self.parent.destroy()
        self.updateDb()
        try:
            self.player.stop()
        except Exception:
            pass
