from tkinter import *
import requests
import threading
import json
import time
import ssl
import os
from ctypes import windll, Structure, c_long, byref
from dbManager import db
# from jikanpy.exceptions import APIException


class RoundTopLevel(Frame):
    def __init__(self, parent, minsize=None, title="Title",
                 radius=25, bd=2, fg="#FFFFFF", bg="#000000", **kwargs):
        self.parent = parent
        if minsize is None:
            self.minFensize = (radius * 3, radius * 3)
        else:
            self.minFensize = minsize
        self.titleText = title
        self.radius = radius
        self.bd = bd
        self.fg = fg
        self.bg = bg
        self.windowX, self.windowY = None, None

        self.fen = Toplevel(self.parent)
        # Toplevel.__init__(self,self.parent)
        self.fen.overrideredirect(True)
        self.fen.wm_attributes("-transparentcolor", "pink")
        # self.fen.attributes('-topmost', 'true')
        self.fen.geometry(
            "+{}+{}".format(50 + self.fen.winfo_x(), 50 + self.fen.winfo_y()))
        self.fen.minsize(*self.minFensize)
        self.fen.grid_columnconfigure(0, weight=1)

        container = self.getCorners(self.fen)
        container_row = int(self.titleText is not None)

        super().__init__(container, bg=self.bg)
        # self.mainFrame = Frame(container,bg=self.bg)
        self.mainFrame = self
        self.fen.topLevel = self
        self.mainFrame.grid(row=container_row, column=0, sticky="nsew")
        self.mainFrame.grid_columnconfigure(0, weight=1)

        if self.titleText is not None:

            self.titleFrame = Frame(container, bg=self.bg)
            self.titleFrame.grid(row=0, column=0, pady=(0, self.radius))
            self.titleFrame.grid_columnconfigure(0, weight=1)

            self.titleLbl = Label(self.titleFrame, text=self.titleText,
                                  bg=self.bg, fg=self.fg, font=("Source Code Pro Medium", 18))
            self.titleLbl.grid(row=0, column=0)

            self.titleLbl.bind("<ButtonPress-1>", self.start_move)
            self.titleLbl.bind("<B1-Motion>", self.do_move)
        else:
            self.titleLbl = None

        self.handles = [self.titleLbl]

        container.grid_rowconfigure(container_row, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.update()

    def get(self):
        return self.mainFrame.get()

    def getCorners(self, parent):
        corners = Frame(parent, bg=self.fg)
        for x in range(3):
            for y in range(3):
                if x == 1 or y == 1:
                    frame = Frame(corners, bg=self.bg)

                    padx = (self.bd if x == 0 else 0, self.bd if x == 2 else 0)
                    pady = (self.bd if y == 0 else 0, self.bd if y == 2 else 0)
                    frame.grid(column=x, row=y, sticky="nsew",
                               padx=padx, pady=pady)
                    if x == y == 1:
                        mainFrame = frame
                else:
                    can = Canvas(corners, width=self.radius,
                                 height=self.radius, bg='pink', highlightthickness=0)
                    can.grid(column=x, row=y, sticky="nsew")
                    width = self.radius * 2
                    posx = 0 if x == 0 else -self.radius
                    posy = 0 if y == 0 else -self.radius
                    can.create_oval(posx, posy, posx + width,
                                    posy + width, fill=self.fg, outline="")
                    can.create_oval(posx + self.bd, posy + self.bd, posx + width -
                                    self.bd, posy + width - self.bd, fill=self.bg, outline="")
        corners.grid_rowconfigure(1, weight=1)
        corners.grid_columnconfigure(1, weight=1)
        corners.pack(expand=True, fill="both")

        return mainFrame

    def getChild(self, w):
        out = []
        if not type(w) in (Button, Checkbutton, Toplevel, OptionMenu):
            out.append(w)
        if type(w) in [Toplevel, Canvas, Frame, RoundTopLevel, type(self)]:
            try:
                for w in w.winfo_children():
                    out += self.getChild(w)
            except BaseException:
                pass
        return out

    def clear(self):
        try:
            for w in self.mainFrame.winfo_children():
                if type(w) != RoundTopLevel:
                    w.destroy()
        except BaseException:
            pass

    def focus_force(self):
        # self.parent.focus_force()
        # self.parent.lift()
        self.fen.lift()
        # self.fen.focus_force()
        for c in self.mainFrame.winfo_children():
            if type(c) == Toplevel:
                if hasattr(c, "topLevel"):
                    c.topLevel.focus_force()
                else:
                    c.focus_force()

    def exit(self, e=None):
        for c in self.mainFrame.winfo_children():
            if type(c) == Toplevel:
                if hasattr(c, "topLevel"):
                    c.topLevel.focus_force()
                else:
                    c.focus_force()
                return
        self.fen.destroy()
        self.parent.focus_force()

    def start_move(self, event):
        self.windowX = event.x
        self.windowY = event.y

    def do_move(self, event):
        if self.windowX is None or self.windowY is None:
            self.windowX = event.x
            self.windowY = event.y
        try:
            deltax = event.x - self.windowX
            deltay = event.y - self.windowY
            x = self.fen.winfo_x() + deltax
            y = self.fen.winfo_y() + deltay
            self.fen.geometry(f"+{x}+{y}")
            for c in self.mainFrame.winfo_children():
                if type(c) == Toplevel:
                    if hasattr(c, "topLevel"):
                        c.topLevel.focus_force()
                    else:
                        c.focus_force()
        except Exception as e:
            print("Error while moving window", e)

    def update(self):
        super().update()
        try:
            self.titleLbl.bind("<ButtonPress-1>", self.start_move)
            self.titleLbl.bind("<B1-Motion>", self.do_move)
        except BaseException:
            pass
        for wid in self.getChild(self.fen):
            if wid not in self.handles:
                wid.bind("<Button-1>", self.exit)
        self.fen.update()


class ScrollableFrame(Frame):
    def __init__(self, parent, **kwargs):
        self.parent = parent

        self.canvas = Canvas(self.parent, highlightthickness=0, **kwargs)
        # self.canvas.pack(fill="both",expand=True,padx=10)#grid(row=1,column=0,columnspan=3,sticky="nsew")
        self.canvas.grid_columnconfigure(0, weight=1)

        super().__init__(self.canvas, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        frame_id = self.canvas.create_window((0, 0), window=self, anchor="nw")

        self.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ))
        self.canvas.bind(
            "<Configure>",
            lambda e:
            self.canvas.itemconfig(frame_id, width=e.width))
        # self.parent.unbind_all('<MouseWheel>')
        for w in self.canvas.winfo_children():
            w.bind(
                "<MouseWheel>",
                lambda e, a=self, b=self.canvas: self.scroll(e, a, b))

    def scroll(self, event, scroll_frame, canvas):
        if self.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        super().update()

    def pack(self, *args, **kwargs):
        # Placeholder
        self.canvas.pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        # Placeholder
        self.canvas.grid(*args, **kwargs)

    def place(self, *args, **kwargs):
        # Placeholder
        self.canvas.place(*args, **kwargs)

    def getChild(self, parent):
        out = []
        try:
            for w in parent.winfo_children():
                out.append(w)
                out += self.getChild(w)
        except BaseException:
            pass
        return out

    def update(self):
        for w in self.getChild(self.canvas):
            w.bind(
                "<MouseWheel>",
                lambda e, a=self, b=self.canvas: self.scroll(e, a, b))
        super().update()


class LoadingBar(Frame):
    def __init__(self, parent, valueGetter, radius, fg, bg, **kwargs):
        self.parent = parent
        self.radius = radius
        self.fg = fg
        self.bg = bg
        self.valueGetter = valueGetter

        super().__init__(self.parent, height=self.radius * 2, **kwargs)
        self.configure(bg=self.bg)
        self.grid_columnconfigure(0, weight=1)

        self.main = Frame(self, bg=bg, width=500, height=self.radius * 2)
        self.main.pack(fill="both", expand=True)
        self.wrapper = Frame(self.main, bg=bg)
        self.wrapper.place(anchor="nw", relheight=1, relwidth=valueGetter())
        self.wrapper.grid_columnconfigure(1, weight=1)

        left = Canvas(self.wrapper, highlightthickness=0,
                      height=self.radius * 2, width=self.radius, bg=bg, **kwargs)
        left.create_oval(0, 0, self.radius * 2, self.radius *
                         2, fill=self.fg, outline="")
        left.grid(row=0, column=0, sticky="nsw")

        bar = Frame(self.wrapper, bg=fg)
        bar.grid(row=0, column=1, sticky="nsew")

        right = Canvas(self.wrapper, highlightthickness=0,
                       height=self.radius * 2, width=self.radius, bg=bg, **kwargs)
        right.create_oval(-self.radius, 0, self.radius,
                          self.radius * 2, fill=self.fg, outline="")
        right.grid(row=0, column=2, sticky="nse")

        self.updateSize()

    def updateSize(self, e=None):
        self.wrapper.place_forget()
        value = self.valueGetter()
        self.wrapper.place(anchor="nw", relheight=1, relwidth=value)
        self.after(500, self.updateSize)
        self.parent.focus_force()


def startServer(hostName, serverPort, dbPath, manager):
    def serve_thread(webServer):
        try:
            webServer.serve_forever()
        except OSError:
            pass
    handler = GetHandler(dbPath, manager)
    httpd = HTTPServer((hostName, serverPort), handler)
    keyFile, certFile = "./key.pem", "./cert.pem"
    usessl = os.path.exists(keyFile) and os.path.exists(certFile)
    if usessl:
        httpd.socket = ssl.wrap_socket(httpd.socket,
                                       keyfile="./key.pem",
                                       certfile='./cert.pem', server_side=True)

    manager.log("SERVER", "Server started http%s://%s:%s" %
                ("s" if usessl else "", hostName, serverPort))

    # webServer.serve_forever()
    t = threading.Thread(target=serve_thread, args=(httpd,), daemon=True)
    t.start()

    return httpd


def stopServer(webServer, manager):
    webServer.server_close()
    manager.log("SERVER", "Server stopped.")


def GetHandler(dbPath, manager):
    class DbServer(BaseHTTPRequestHandler):
        def do_GET(self):
            code = 200
            content = "application/json"

            self.database = db(dbPath)
            self.log("SERVER", "Received GET request from address {}".format(
                self.client_address))
            # database = db("D:/Animes/Torrents/Scripts/jikan.moe.db")
            # self.wfile.write(bytes("<p>Request: %s</p>" % self.path, "utf-8"))
            request = self.path.split("/")[1:]
            if request[0] != "":
                table = request.pop(0)
                if len(request) >= 1:
                    id = request.pop(0)
                else:
                    id = None
            else:
                table = None
                id = None

            if table is not None:
                if table == "sync":
                    data = self.getAnimesToSync()
                    content = "application/json"
                elif id is not None:
                    data = dict(self.database(id=id, table=table))
                    if data['id'] == "NONE":
                        # data = "404 - Id not in db"
                        # code = 404
                        # content = "text/plain"
                        self.send_error(
                            400, "Id not in db", "The id {} is not in the database.".format(id))
                        return
                else:
                    try:
                        data = dict(self.database.sql(
                            "SELECT * FROM {}".format(table)))
                    except BaseException:
                        code = 404
                        content = "text/html; charset=UTF-8"
                        data = "404 - Invalid table"

            else:
                content = "text/html;charset='utf-8'"
                data = "<!DOCTYPE html><html><header><meta charset='utf-8'><title>Heyyy</title><body><h1>Main page</h1><p>I need something here</p></body></html>"

            self.send_response(code)
            self.send_header("Content-type", content)
            self.end_headers()
            self.send(data, content)

        def do_POST(self):
            length = int(self.headers['Content-length'])
            rep = json.loads(self.rfile.read(length))
            self.log("SERVER", "Received sync request (POST) from address {}, {} animes.".format(
                self.client_address, len(rep)))
            self.saveAnimes(rep)
            self.send_response(200, "OK")
            self.end_headers()

            rep = self.getAnimesToSync()

            self.send(rep, "application/json")
            # self.wfile.write(bytes(json.dumps(rep),"utf-8"))

        def log(self, *args):
            print(*args, flush=True)

        def saveAnimes(self, rep):
            self.database = db("D:/Animes/Torrents/Scripts/jikan.moe.db")
            self.manager = manager
            for anime in rep:
                id, tag, like = anime.values()
                if not self.database(id=id, table="anime").exist():
                    try:
                        self.log("SERVER", "Fetching data for id", id)
                        data = self.manager.getData(id)
                        self.database(id=id, table="anime").set(
                            data, save=False)
                    except BaseException:
                        pass

                if not self.database(id=id, table="tag").exist():
                    try:
                        self.database(id=id, table="tag").set(
                            {"id": id, "tag": tag}, save=False)
                    except BaseException:
                        pass
                    dbTag = tag
                else:
                    dbTag = self.database(id=id, table="tag").get("tag")

                if not self.database(id=id, table="like").exist():
                    try:
                        self.database(id=id, table="like").set(
                            {"id": id, "like": like}, save=False)
                    except BaseException:
                        pass
                    dbLike = like
                else:
                    dbLike = self.database(id=id, table="like").get("like")

            self.database.save()

        def getAnimesToSync(self):
            self.database = db("D:/Animes/Torrents/Scripts/jikan.moe.db")
            content = self.database.sql(
                'SELECT anime.id, title, title_synonyms, picture, synopsis, episodes, duration, rating, status, broadcast, trailer,tag.tag,like.like FROM anime LEFT JOIN tag USING(id) LEFT JOIN like USING(id) WHERE tag.tag in ("WATCHLIST","WATCHING","SEEN")')
            rep = []
            keys = ("mal_id", "title", "title_synonyms", "image_url", "synopsis", "episodes",
                    "duration", "rating", "status", "broadcast", "trailer_url", "tag", "like")

            for c in content:
                value = dict(zip(keys, c))
                value['title_synonyms'] = json.loads(value['title_synonyms'])
                rep.append(value)

            return rep

        def send(self, data, content):
            if content == "application/json":
                data = json.dumps(data)
            self.wfile.write(bytes(data, "utf-8"))

    return DbServer


class Timer():
    def __init__(self, name):
        self.startTime = time.time()
        self.name = name

        self.timer = None
        self.timeList = []

    def start(self):
        self.timer = time.time()

    def stop(self):
        if self.timer is not None:
            self.timeList.append(time.time() - self.timer)
            self.timer = None

    def stats(self):
        nameBracks = "[{}]".format(self.name.center(10))
        print(nameBracks, "Total:", time.time() - self.startTime)
        if len(self.timeList) > 0:
            print(nameBracks, "Average:", sum(self.timeList) /
                  len(self.timeList), "- Loops:", len(self.timeList))


class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]


def queryMousePosition():
    pt = POINT()
    windll.user32.GetCursorPos(byref(pt))
    return pt.x, pt.y


def new_iter(first, iter):
    yield first
    for i in iter:
        yield i


def merge_iter(a, b):
    for i in a:
        yield i
    for i in b:
        yield i


def peek(iter):
    try:
        first = next(iter, None)
    except StopIteration:
        return None, ()
    except Exception as e:
        return e, iter
    else:
        return first, new_iter(first, iter)


if __name__ == "__main__":
    from animeManager import Manager
    m = Manager()
