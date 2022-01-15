from .base_player import BasePlayer
import os
import time
import traceback

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if not os.path.exists(path):
    raise ImportError("mpv lib folder not found!")
os.environ['PATH'] = path + ";" + os.environ["PATH"]
import mpv


class MpvPlayer(BasePlayer):
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
            self.log("No video found!")
            self.player = None
            self.OnClose()
            return

        h = self.videopanel.winfo_id()
        self.player = mpv.MPV(wid=str(int(h)), ytdl=url)

        @self.player.property_observer('time-remaining')
        def auto_loop(_name, time):
            if time is None:
                return
            if time == 0.0:
                self.log("NEXT FILE")
                self.playlistNext()

        self.player.play(self.playlist[self.index])

        self.volume = 100
        self.volumeUp()

        self.videoSize = (self.videopanel.winfo_width(),
                          self.videopanel.winfo_height())

        self.log("Playing", self.playlist[self.index])

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
        if not i:
            i = 0
        track = i + 1
        if track > len(self.audioTracks):
            track = False
        self.player.audio = track
        self.updateAudioLbl()

    def audioTrackBack(self):
        i = self.player.audio
        if not i:
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
        if not i:
            i = 0
        track = i + 1
        if track > len(self.subTracks):
            track = False
        self.player.sub = track
        self.updateSubLbl()

    def subTrackBack(self):
        i = self.player.sub
        if not i:
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
        try:
            self.player.seek(t)
        except SystemError as e:
            self.log(e)

    def timeBack(self, t=0):
        t = int(t)
        try:
            self.player.seek(-t)
        except SystemError as e:
            self.log(e)

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

    def togglePause(self, playing=None):
        if playing is not None and not playing == self.paused:
            return
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
            except Exception:
                pass
        try:
            if not self.stopped:
                self.parent.after(5000, lbl.place_forget)
        except Exception:
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
        except Exception:
            pass

        # cursor = vlc.libvlc_video_get_cursor(self.player,0)[1]
        try:
            cursorX, cursorY = self.queryMousePosition()
        except Exception:
            cursorX, cursorY = 0, 0
        cursorX, cursorY = cursorX - self.videopanel.winfo_rootx(), cursorY - \
            self.videopanel.winfo_rooty()
        # self.log(cursor)

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

    def OnClose(self):
        if self.stopped:
            return
        self.stopped = True
        self.parent.destroy()
        self.updateDb()
        try:
            if self.player:
                self.player.stop()
        except Exception as e:
            self.log("Error while stopping player:", traceback.format_exc())
        self.log("Closed media player")
