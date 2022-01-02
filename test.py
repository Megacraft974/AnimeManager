# import re,requests,urllib,socket

# url = "magnet:?xt=urn:btih:RRN4MNLGBHMAVYU372YXQ46NU3WVZ5WR&dn=%5BSubsPlease%5D%20Mushoku%20Tensei%20-%2015%20%28720p%29%20%5B14A68BE1%5D.mkv&xl=686477749&tr=http%3A%2F%2Fnyaa.tracker.wf%3A7777%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2F9.rarbg.to%3A2710%2Fannounce&tr=udp%3A%2F%2F9.rarbg.me%3A2710%2Fannounce&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.internetwarriors.net%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.cyberia.is%3A6969%2Fannounce&tr=udp%3A%2F%2Fexodus.desync.com%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker3.itzmx.com%3A6961%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce&tr=udp%3A%2F%2Ftracker.tiny-vps.com%3A6969%2Fannounce&tr=udp%3A%2F%2Fretracker.lanta-net.ru%3A2710%2Fannounce&tr=http%3A%2F%2Fopen.acgnxtracker.com%3A80%2Fannounce&tr=wss%3A%2F%2Ftracker.openwebtorrent.com"
# pattern = re.compile(r"^magnet:?")

# print(str("0x41727101980"))

# def getTracker(protocol,url,port,info_hash,size):
#     params = {
#         'info_hash': info_hash,
#         'peer_id': "weshweshcava12345678",
#         'port': port,
#         'uploaded': '0',
#         'downloaded': '0',
#         'left': str(size),
#         'compact': '1',
#         'no_peer_id': '0',
#         'event': 'started'
#     }
#     if protocol == "http":
#         try:
#             page = requests.get(url, params=params)
#         except ConnectionResetError as e:
#             print(e)
#         except requests.exceptions.ConnectionError as e:
#             print(2,e)
#         except requests.exceptions.InvalidSchema as e:
#             print(3,e)
#         else:
#             print("---",page.text)
#     elif protocol == "udp":
#         sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
#         sock.sendto(bytes(MESSAGE, "utf-8"), (UDP_IP, UDP_PORT))
#     else:
#         print(protocol,"not supported")

# if pattern.match(url):
#     print("Magnet!")

#     parameters = re.compile(r"(\w{2})=([^&]+)")
#     data = list((a,urllib.parse.unquote(b)) for a,b in parameters.findall(url))
#     for i,d in enumerate(data):
#         k,v = d
#         if k == "tr":
#             try:
#                 v = urllib.parse.urlparse(v)
#             except Exception as e:
#                 print(e)
#         else:
#             print(k,v)
#         data[i] = (k,v)

#     print("___________")
#     info_hash = [d[1] for d in data if d[0] == "xt"][0].split(":")[-1]
#     size = [d[1] for d in data if d[0] == "xl"][0]
#     print(info_hash,size)
#     for k,v in (d for d in data if d[0] == "tr"):
#         url = urllib.parse.urlunparse(v)
#         print(url)
#         getTracker(v.scheme,url,v.port,info_hash,size)

from tkinter import *
from PIL import Image, ImageTk, ImageDraw


class CustomScrollbar(Frame):
    def __init__(self, parent, orient='V', **kwargs):
        self.parent = parent
        if orient in ('V', 'H'):
            self.orient = orient
        else:
            raise ValueError("Orient must be either 'V' or 'H'.")

        self.padding = 5
        self.thickness = 30
        self.fg = "#000000"
        self.bg = "#FFFFFF"
        self.command = None

        super().__init__(self.parent, bg="#00FF00")

        self.frame = Canvas(self, width=self.thickness, bg=self.bg, bd=0, highlightthickness=0)

        self.frame.bind("<B1-Motion>", self.move_thumb)

        self.configure(**kwargs)
        self.frame.pack()

    def configure(self, **kwargs):
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if "thickness" in kwargs:
            self.thickness = kwargs.pop("thickness")
            kwargs["width" if self.orient == "V" else "height"] = self.thickness
        if "padding" in kwargs:
            self.padding = kwargs.pop("padding")
        if "fg" in kwargs:
            self.fg = kwargs.pop("fg")
        if "bg" in kwargs:
            self.bg = kwargs["bg"]

        self.frame.configure(**kwargs)

    def get(self):
        return self.start, self.stop

    def set(self, a, b):
        self.start, self.stop = float(a), float(b)
        self.draw_thumb(self.start, self.stop)

    def draw_thumb(self, start, stop):
        width = self.frame.winfo_width()
        height = self.frame.winfo_height()
        if self.orient == "H":
            width, height = height, width

        self.frame.delete(ALL)
        scale = 10
        img_size = ((width - self.padding * 2) * scale, int(((stop - start) * height - self.padding * 2) * scale))
        img_width = img_size[0 if self.orient == "V" else 1]
        img_height = img_size[1 if self.orient == "V" else 0]

        if img_height <= img_width:
            image = Image.new('RGB', (img_width, img_width), self.bg)
            draw = ImageDraw.Draw(image)
            draw.ellipse((0, 0, img_width, img_width), fill=self.fg, outline=None)
        else:
            image = Image.new('RGB', img_size, self.bg)
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, img_width / 2, img_width, img_height - img_width / 2), fill=self.fg, outline=None)
            draw.ellipse((0, 0, img_width, img_width), fill=self.fg, outline=None)
            draw.ellipse((0, img_height - img_width - 1, img_width, img_height - 1), fill=self.fg, outline=None)

        self.thumb = image.resize((img_size[0] // scale, img_size[1] // scale), Image.ANTIALIAS)
        thumb_img = ImageTk.PhotoImage(self.thumb, master=self.frame)

        pos = start * height + self.padding
        self.frame.create_image(self.padding, pos, image=thumb_img, anchor="nw")
        self.frame.image = thumb_img

    def move_thumb(self, event):
        if self.orient == "V":
            fensize = self.frame.winfo_height()
            pos = event.y / fensize
        else:
            fensize = self.frame.winfo_width()
            pos = event.x / fensize

        if self.command is not None:
            self.command('moveto', str(pos))


root = Tk()
scrollbar = CustomScrollbar(root, width=20, fg="#383935", bg="#AAAAAA")
scrollbar.pack(side=RIGHT, fill=Y)

mylist = Listbox(root, yscrollcommand=scrollbar.set)
for line in range(100):
    mylist.insert(END, "This is line number " + str(line))

mylist.pack(side=LEFT, fill=BOTH)
scrollbar.configure(command=mylist.yview)  # lambda *args: print(args))

mainloop()
