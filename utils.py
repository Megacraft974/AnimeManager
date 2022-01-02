import auto_launch

import threading
import json
import time
import os
import re
from ctypes import windll, Structure, c_long, byref
from logger import log
from tkinter import *
from PIL import Image, ImageTk, ImageDraw


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

            self.titleLbl = Label(
                self.titleFrame,
                text=self.titleText,
                bg=self.bg,
                fg=self.fg,
                font=(
                    "Source Code Pro Medium",
                    18))
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
                    can = Canvas(
                        corners,
                        width=self.radius,
                        height=self.radius,
                        bg='pink',
                        highlightthickness=0)
                    can.grid(column=x, row=y, sticky="nsew")
                    width = self.radius * 2
                    posx = 0 if x == 0 else -self.radius
                    posy = 0 if y == 0 else -self.radius
                    can.create_oval(posx, posy, posx + width,
                                    posy + width, fill=self.fg, outline="")
                    can.create_oval(
                        posx + self.bd,
                        posy + self.bd,
                        posx + width - self.bd,
                        posy + width - self.bd,
                        fill=self.bg,
                        outline="")
        corners.grid_rowconfigure(1, weight=1)
        corners.grid_columnconfigure(1, weight=1)
        corners.pack(expand=True, fill="both")

        return mainFrame

    def getChild(self, w):
        out = []
        if not type(w) in (Button, Checkbutton, Toplevel, OptionMenu, DropDownMenu):
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
                if not isinstance(w, RoundTopLevel):
                    w.destroy()
        except BaseException:
            pass

    def focus_force(self):
        self.fen.lift()
        for c in self.mainFrame.winfo_children():
            if isinstance(c, Toplevel):
                if hasattr(c, "topLevel"):
                    c.topLevel.focus_force()
                else:
                    c.focus_force()

    def exit(self, e=None):
        for c in self.mainFrame.winfo_children():
            if isinstance(c, Toplevel):
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
                if isinstance(c, Toplevel):
                    if hasattr(c, "topLevel"):
                        c.topLevel.focus_force()
                    else:
                        c.focus_force()
        except Exception as e:
            log("Error while moving window", e)

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


class ScrollableFrame(Frame):
    def __init__(self, root, axis="V", scrollbar=False, **kwargs):
        self.parent = Frame(root)
        if axis not in ("H", "V"):
            raise TypeError
        self.axis = axis  # Either "H" or "V"

        self.canvas = Canvas(self.parent, highlightthickness=0, **kwargs)
        self.canvas.pack(fill="both", expand=True, side="left")  # grid(row=1,column=0,columnspan=3,sticky="nsew")
        self.canvas.grid_columnconfigure(0, weight=1)

        super().__init__(self.canvas, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        frame_id = self.canvas.create_window((0, 0), window=self, anchor="nw")

        self.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ))
        if axis == "V":
            self.canvas.bind(
                "<Configure>",
                lambda e:
                self.canvas.itemconfig(frame_id, width=e.width))
        else:
            self.canvas.bind(
                "<Configure>",
                lambda e:
                self.canvas.itemconfig(frame_id, height=e.height))

        if scrollbar:
            # self.scrollbar = Scrollbar(self.parent)
            self.scrollbar = CustomScrollbar(self.parent, **kwargs)
            if axis == "V":
                self.scrollbar.config(command=self.canvas.yview, orient="vertical")
                self.canvas.configure(yscrollcommand=self.scrollbar.set)
                fill = "y"
            else:
                self.scrollbar.config(command=self.canvas.xview, orient="horizontal")
                self.canvas.configure(xscrollcommand=self.scrollbar.set)
                fill = "x"
            self.scrollbar.pack(fill=fill, expand=True, side="right")

        self.update()

    def scroll(self, event, scroll_frame, canvas):
        if self.axis == "V":
            if self.winfo_height() > self.canvas.winfo_height():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            if self.winfo_width() > self.canvas.winfo_width():
                self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
        super().update()

    def pack(self, *args, **kwargs):
        # Placeholder
        self.parent.pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        # Placeholder
        self.parent.grid(*args, **kwargs)

    def place(self, *args, **kwargs):
        # Placeholder
        self.parent.place(*args, **kwargs)

    def getChild(self, parent):
        out = []
        try:
            for w in parent.winfo_children():
                out.append(w)
                out += self.getChild(w)
        except BaseException:
            pass
        return out

    def bbox(self, *args, **kwargs):
        return self.canvas.bbox(*args, **kwargs)

    def update(self):
        super().update()
        for w in self.getChild(self.canvas):
            w.bind(
                "<MouseWheel>",
                lambda e, a=self, b=self.canvas: self.scroll(e, a, b))


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

        left = Canvas(
            self.wrapper,
            highlightthickness=0,
            height=self.radius * 2,
            width=self.radius,
            bg=bg,
            **kwargs)
        left.create_oval(0, 0, self.radius * 2, self.radius * 2, fill=self.fg, outline="")
        left.grid(row=0, column=0, sticky="nsw")

        bar = Frame(self.wrapper, bg=fg)
        bar.grid(row=0, column=1, sticky="nsew")

        right = Canvas(
            self.wrapper,
            highlightthickness=0,
            height=self.radius * 2,
            width=self.radius,
            bg=bg,
            **kwargs)
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


class DropDownMenu(Button):
    def __init__(self, master, var, *values, **kwargs):
        self.var = var
        self.values = values
        menu_config = {}
        for k in set(kwargs.keys()):
            if k in ("command", "elem_per_row"):
                menu_config[k] = kwargs.pop(k)
        # kwargs["text"] = var.get()
        super().__init__(master, **kwargs)
        self.menu = DropDown(self, self.var, *self.values, **menu_config)
        # kwargs["command"] = self.menu.show
        self.config(text=var.get(), command=self.menu.show)


class DropDown(Toplevel):
    def __init__(self, master, var, *values, command=None, elem_per_row=20):
        self.master = master
        self.var = var
        self.values = values
        self.command = command
        self.elem_per_row = elem_per_row

        self.main_frame = None
        self.rows = []
        self.config = {}

        self.column_width = 100
        self.row_height = 30

        self.sep_bg = "#FFFFFF"
        self.fg = "#FFFFFF"
        self.bg = "#FF00FF"

        super().__init__(self.master)
        self.overrideredirect(True)
        self.withdraw()
        self.bind("<FocusOut>", self.hide)

    def show(self):
        x, y = self.master.winfo_rootx(), self.master.winfo_rooty() + self.master.winfo_height()
        max_x, max_y = self.master.winfo_screenwidth() - x, self.master.winfo_screenheight() - y
        self.maxsize(max_x, max_y)
        self.geometry("+{}+{}".format(x, y))
        self.deiconify()
        self.focus_force()
        self.minsize(self.master.winfo_width() * 2, min(self.main_frame.winfo_height(), len(self.values) * self.row_height))

    def hide(self, arg=None):
        self.withdraw()
        # self.destroy()

    def configure(self, **kwargs):
        self.config = kwargs

    def root_configure(self, **kwargs):
        if "fg" in kwargs:
            self.fg = kwargs.pop("fg")
        if "bg" in kwargs:
            self.bg = kwargs.pop("bg")
        kwargs['bg'] = self.fg
        super().configure(**kwargs)

    def update(self):
        self.update_values()
        super().update()

    def entryconfig(self, i, **kwargs):
        self.rows[i].configure(**kwargs)

    def update_values(self):
        if self.main_frame is not None:
            self.main_frame.destroy()
        self.main_frame = ScrollableFrame(self, axis="H", bg=self.bg)
        self.main_frame.pack(expand=True, fill="both")

        columns, rows = len(self.values) // self.elem_per_row + 1, min(self.elem_per_row, len(self.values))
        # self.minsize(self.column_width * columns, self.row_height * rows)
        for i in range(columns):
            self.main_frame.grid_columnconfigure(i * 2, weight=1)
        for i in range(rows):
            self.main_frame.grid_rowconfigure(i, weight=1, minsize=self.row_height)

        self.rows = []
        for i, val in enumerate(self.values):
            row = Button(self.main_frame, text=val, command=self.handle_command(val), anchor="w", **self.config)
            row.grid(row=i % self.elem_per_row, column=i // self.elem_per_row * 2, sticky="nsew")
            self.rows.append(row)
        for i in range(columns - 1):
            sep = Frame(self.main_frame, bg=self.fg, width=2)
            sep.grid(row=0, column=i * 2 + 1, rowspan=self.elem_per_row, sticky="ns", pady=10)

        self.main_frame.update()

    def handle_command(self, val):
        def handler():
            self.var.set(val)
            if self.command is not None:
                self.command(val)
        return handler


class CustomScrollbar(Frame):
    def __init__(self, parent, orient='V', **kwargs):
        self.parent = parent
        if orient in {'V', 'H', 'v', 'h', 'vertical', 'horizontal'}:
            self.orient = orient[0].upper()
        else:
            raise ValueError("Orient must be either 'V' or 'H'.")

        self.padding = 5
        self.thickness = 30
        self.fg = "#000000"
        self.bg = "#FFFFFF"
        self.command = None

        super().__init__(self.parent, bg="#00FF00")

        if self.orient == "V":
            tmp = {"width": self.thickness}
        else:
            tmp = {"height": self.thickness}
        self.frame = Canvas(self, **tmp, bg=self.bg, bd=0, highlightthickness=0)

        self.frame.bind("<B1-Motion>", self.move_thumb)

        self.configure(**kwargs)
        self.frame.pack(fill="y" if self.orient == "V" else "x", expand=True)

    def configure(self, **kwargs):
        if "orient" in kwargs:
            orient = kwargs.pop("orient")
            if orient in {'V', 'H', 'v', 'h', 'vertical', 'horizontal'}:
                orient = orient[0].upper()
            else:
                raise ValueError("Orient must be either 'V' or 'H'.")
            if orient != self.orient:
                self.destroy()
                self.__init__(self.parent, orient, **kwargs)
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

    def config(self, **kwargs):
        return self.configure(**kwargs)

    def get(self):
        return self.start, self.stop

    def set(self, a, b):
        self.start, self.stop = float(a), float(b)
        self.draw_thumb(self.start, self.stop)

    def draw_thumb(self, start, stop):
        self.update()
        width = self.frame.winfo_width()
        height = self.frame.winfo_height()
        if self.orient == "H":
            width, height = height, width

        self.frame.delete(ALL)
        scale = 10
        img_size = (max(1, (width - self.padding * 2)) * scale, max(1, int(((stop - start) * height - self.padding * 2)) * scale))
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

        self.thumb = image.resize((max(1, img_size[0] // scale), max(1, img_size[1] // scale)), Image.ANTIALIAS)
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
        log(nameBracks, "Total:", time.time() - self.startTime)
        if len(self.timeList) > 0:
            log(nameBracks, "Average:", sum(self.timeList) / len(self.timeList), "- Loops:", len(self.timeList))


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


def project_modules(root="./"):
    ignore = ("__pycache__", ".git", "venv")
    modules = {}
    pattern = re.compile(r"(?:from ([\w_\.]*) import \S*)|(?:import ([\w_\.]*))")
    for f in os.listdir(root):
        if f in ignore:
            continue
        path = os.path.realpath(os.path.join(root, f))
        if os.path.isdir(path):
            modules |= project_modules(path)
            continue
        end = f.split(".")[-1]
        if end == "py":
            with open(path, encoding="utf-8") as file:
                for i, line in enumerate(file):
                    for match in re.finditer(pattern, line):
                        groups = match.groups()
                        if groups[0]:
                            m = groups[0]
                            if m in modules.keys():
                                modules[m].append((path, i + 1))
                            else:
                                modules[m] = [(path, i + 1)]
                        elif groups[1]:
                            if "," in groups[1]:
                                for m in groups[1].split(','):
                                    if m in modules.keys():
                                        modules[m].append((path, i + 1))
                                    else:
                                        modules[m] = [(path, i + 1)]
                            else:
                                m = groups[1]
                                if m in modules.keys():
                                    modules[m].append((path, i + 1))
                                else:
                                    modules[m] = [(path, i + 1)]
    return dict(sorted(modules.items()))


def project_stats(root="./"):
    def pp_bytes(size):
        units = ('o', 'Ko', 'Mo', 'Go', 'To')
        i = 0
        while size / 1000 > 1:
            size = size // 1000
            i += 1
        return str(size) + " " + units[i]
    ignore = ("__pycache__", ".git", "venv")
    lines, files, folders, size = 0, 0, 0, 0
    for f in os.listdir(root):
        if f in ignore:
            continue
        end = f.split(".")[-1]
        path = os.path.join(root, f)
        if os.path.isfile(path):
            size += os.path.getsize(path)
            if end == "py":
                files += 1
                with open(path, encoding="utf-8") as file:
                    lines += len(file.readlines()) + 1
        elif os.path.isdir(path):
            t_lines, t_files, t_folders, t_size = project_stats(path)
            lines += t_lines
            files += t_files
            folders += t_folders + 1
            size += t_size
    if root == "./":
        print("{} lines in the project, {} files, {} folders, total size: {}".format(lines, files, folders, pp_bytes(size)))
    return lines, files, folders, size


if __name__ == "__main__":
    for k, v in project_modules().items():
        print(k, ":")
        for p in v:
            print('   File "{}", line {}'.format(*p))
    project_stats()
