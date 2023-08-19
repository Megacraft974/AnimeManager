import time
import queue
import os
import re

from datetime import datetime, timedelta, timezone

from classes import AnimeList, DefaultDict

# from ctypes import windll, Structure, c_long, byref
from logger import log
from tkinter import *
from tkinter.simpledialog import Dialog
from tkinter.messagebox import showwarning
from PIL import Image, ImageTk, ImageDraw

class RoundTopLevel(Frame):
    def __init__(self, parent, minsize=None, title="Title",
                 radius=25, bd=2, fg="#FFFFFF", bg="#000000", **kwargs):
        self.parent = parent
        self.minFensize = minsize or (radius * 3, radius * 3)
        self.titleText = title
        self.radius = radius
        self.bd = bd
        self.fg = fg
        self.bg = bg
        self.windowX, self.windowY = None, None

        self.window = Toplevel(self.parent)
        self.window.overrideredirect(True)
        self.window.wm_attributes("-transparentcolor", "pink")
        self.window.geometry(
            "+{}+{}".format(50 + self.parent.winfo_x(), 50 + self.parent.winfo_y()))
        self.window.minsize(*self.minFensize)
        self.window.grid_columnconfigure(0, weight=1)

        container = self.getCorners(self.window)
        container_row = int(self.titleText is not None)

        super().__init__(container, bg=self.bg)
        # self.mainFrame = Frame(container,bg=self.bg)
        self.mainFrame = self
        self.window.topLevel = self
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

        self.update_events()

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
        # ScrollableFrame
        if not isinstance(w, (Button, Checkbutton, Toplevel, OptionMenu, DropDownMenu, CustomScrollbar)):
            out.append(w)

        # RoundTopLevel, ScrollableFrame
        if isinstance(w, (Toplevel, Canvas, Frame)):
            try:
                for sub_w in w.winfo_children():
                    out += self.getChild(sub_w)
            except Exception:
                pass
        return out

    def clear(self):
        try:
            for w in self.mainFrame.winfo_children():
                if not isinstance(w, RoundTopLevel):
                    w.destroy()
        except Exception:
            pass

    def focus_force(self):
        self.window.lift()
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
        self.window.destroy()
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
            x = self.window.winfo_x() + deltax
            y = self.window.winfo_y() + deltay
            self.window.geometry(f"+{x}+{y}")
            for c in self.mainFrame.winfo_children():
                if isinstance(c, Toplevel):
                    if hasattr(c, "topLevel"):
                        c.topLevel.focus_force()
                    else:
                        c.focus_force()
        except Exception as e:
            log("Error while moving window", e)

    def update_events(self):
        for handle in self.handles:
            try:
                handle.bind("<ButtonPress-1>", self.start_move)
                handle.bind("<B1-Motion>", self.do_move)
            except Exception:
                pass

        children = self.getChild(self.window)
        for wid in children:
            if wid not in self.handles:
                wid.bind("<Button-1>", self.exit)


class ScrollableFrame(Frame):
    def __init__(self, root, axis="V", scrollbar=False, **kwargs):
        self.root = Frame(root)
        if axis not in ("H", "V"):
            raise TypeError("Axis must be either 'H' or 'V'")
        self.axis = axis  # Either "H" or "V"

        self.ARROW_SCROLL_SPEED = 1  # TODO - Put in constants?

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.canvas = Canvas(self.root, highlightthickness=0)
        self.canvas.configure(**parse_args(self.canvas, kwargs))
        self.canvas.grid(row=0, column=0, sticky="nsew")

        super().__init__(self.canvas)
        self.config(**parse_args(self, kwargs))
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
            self.scrollbar = CustomScrollbar(self.root, **kwargs)
            if axis == "V":
                self.scrollbar.config(
                    command=self.canvas.yview, orient="vertical")
                self.canvas.configure(yscrollcommand=self.scrollbar.set)
                self.scrollbar.grid(row=0, column=1, sticky="ns")
            else:
                self.scrollbar.config(
                    command=self.canvas.xview, orient="horizontal")
                self.canvas.configure(xscrollcommand=self.scrollbar.set)
                self.scrollbar.grid(row=1, column=0, sticky="ew")
            self.root.grid_columnconfigure(0, weight=1)
            self.root.grid_rowconfigure(0, weight=1)

        self.update_scrollzone()

    def scroll(self, delta):
        if self.axis == "V":
            if self.winfo_height() > self.canvas.winfo_height():
                self.canvas.yview_scroll(
                    int(-1 * (delta / 120)), "units")
        else:
            if self.winfo_width() > self.canvas.winfo_width():
                self.canvas.xview_scroll(
                    int(-1 * (delta / 120)), "units")

    def pack(self, *args, **kwargs):
        # Placeholder
        self.root.pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        # Placeholder
        self.root.grid(*args, **kwargs)

    def place(self, *args, **kwargs):
        # Placeholder
        self.root.place(*args, **kwargs)

    def getChild(self, parent):
        out = []
        try:
            for w in parent.winfo_children():
                out.append(w)
                out += self.getChild(w)
        except Exception:
            pass
        return out

    def bbox(self, *args, **kwargs):
        return self.canvas.bbox(*args, **kwargs)

    def update_scrollzone(self, childs=None):
        if childs is None:
            childs = self.getChild(self.canvas)

        for w in childs:
            w.bind(
                "<MouseWheel>",
                lambda e: self.scroll(e.delta))
            # w.bind(
            #     "<Up>",
            #     lambda e: self.scroll(-self.ARROW_SCROLL_SPEED))
            # w.bind(
            #     "<Down>",
            #     lambda e: self.scroll(self.ARROW_SCROLL_SPEED))


class CustomScrollbar(Frame):
    def __init__(self, parent, orient='V', **kwargs):
        self.root = parent
        if orient in {'V', 'H', 'v', 'h', 'vertical', 'horizontal'}:
            self.orient = orient[0].upper()
        else:
            raise ValueError("Orient must be either 'V' or 'H'.")

        self.padding = 5
        self.thickness = 30
        self.fg = "#000000"
        self.bg = "#FFFFFF"
        self.command = None
        self._config = {}

        super().__init__(self.root, bg="#00FF00")

        if self.orient == "V":
            tmp = {"width": self.thickness}
        else:
            tmp = {"height": self.thickness}

        self.frame = Canvas(self, **tmp, bg=self.bg,
                            bd=0, highlightthickness=0)

        self.frame.bind("<B1-Motion>", self.move_thumb)

        self.configure(**kwargs)
        self.frame.pack(fill="y" if self.orient == "V" else "x", expand=True)

    def configure(self, **kwargs):
        self._config = dict_merge(self._config, kwargs)
        if "orient" in kwargs:
            orient = kwargs.pop("orient")
            if orient in {'V', 'H', 'v', 'h', 'vertical', 'horizontal'}:
                orient = orient[0].upper()
            else:
                raise ValueError("Orient must be either 'V' or 'H'.")
            if orient != self.orient:
                self.destroy()
                self.__init__(self.root, **self._config)
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if "thickness" in kwargs:
            self.thickness = kwargs.pop("thickness")
            kwargs["width" if self.orient ==
                   "V" else "height"] = self.thickness
        if "padding" in kwargs:
            self.padding = kwargs.pop("padding")
        if "sb_fg" in kwargs:
            self.fg = kwargs.pop("sb_fg")
        elif "fg" in kwargs:
            self.fg = kwargs.pop("fg")
        if "bg" in kwargs:
            self.bg = kwargs["bg"]

        for k in set(kwargs.keys()):
            if k not in self.frame.config().keys():
                kwargs.pop(k)

        self.frame.configure(**kwargs)

    def config(self, **kwargs):
        return self.configure(**kwargs)

    def get(self):
        return self.start, self.stop

    def set(self, a, b):
        self.start, self.stop = float(a), float(b)
        try:
            self.draw_thumb(self.start, self.stop)
        except Exception:
            pass

    def draw_thumb(self, start, stop):
        width = self.frame.winfo_width()
        height = self.frame.winfo_height()
        if self.orient == "H":
            width, height = height, width

        self.frame.delete(ALL)
        scale = 10
        img_size = (max(1, (width - self.padding * 2)) * scale, max(1,
                    int(((stop - start) * height - self.padding * 2)) * scale))
        img_width = img_size[0]
        img_height = img_size[1]

        if img_height <= img_width:
            image = Image.new('RGB', (img_width, img_width), self.bg)
            draw = ImageDraw.Draw(image)
            draw.ellipse((0, 0, img_width, img_width),
                         fill=self.fg, outline=None)
        else:
            image = Image.new('RGB', img_size, self.bg)
            draw = ImageDraw.Draw(image)
            draw.ellipse((0, 0, img_width, img_width),
                         fill=self.fg, outline=None)
            draw.rectangle((0, img_width / 2, img_width, img_height -
                           img_width / 2), fill=self.fg, outline=None)
            draw.ellipse((0, img_height - img_width - 1, img_width,
                         img_height - 1), fill=self.fg, outline=None)

        self.thumb = image.resize(
            (max(1, img_width // scale), max(1, max(img_height, img_width) // scale)), Image.LANCZOS)
        if self.orient == "H":
            self.thumb = self.thumb.rotate(90, expand=True)
        thumb_img = ImageTk.PhotoImage(self.thumb, master=self.frame)

        pos = start * (height - self.padding * 2) + self.padding
        pos = min(pos, height - self.padding * 2 - img_width // scale)
        if self.orient == "V":
            self.frame.create_image(
                self.padding, pos, image=thumb_img, anchor="nw")
        else:
            self.frame.create_image(
                pos, self.padding, image=thumb_img, anchor="nw")
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


class LoadingBar(Frame):
    def __init__(self, parent, valueGetter, radius, fg, bg, **kwargs):
        self.root = parent
        self.radius = radius
        self.fg = fg
        self.bg = bg
        self.valueGetter = valueGetter

        super().__init__(self.root, height=self.radius * 2, **kwargs)
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
        left.create_oval(0, 0, self.radius * 2, self.radius *
                         2, fill=self.fg, outline="")
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
        self.root.focus_force()


class DropDownMenu(Button):
    def __init__(self, master, var, *values, **kwargs):
        super().__init__(master)
        self.menu = DropDown(self, var, *values, **kwargs)
        self.configure(**parse_args(self, kwargs))
        super().configure(
            text=var.get(),
            command=self.menu.show
        )

    def config(self, *args, **kwargs):
        return self.configure(*args, **kwargs)

    def configure(self, *args, **kwargs):
        if 'command' in kwargs:
            cmd = kwargs.pop('command')
            self.menu.configure(command=cmd)

        if args:
            self.menu.configure(*args)

        return super().configure(**kwargs)


class DropDown(Toplevel):
    def __init__(self, master, var, *values, command=None, elem_per_row=20, scrollbar=False, **kwargs):
        self.master = master
        self.var = var
        self.values = list(values)
        self.command = command
        self.elem_per_row = elem_per_row
        self.scrollbar = scrollbar

        self.main_frame = None
        self.rows = []
        self.config_ = kwargs

        self.column_width = 100
        self.row_height = 35

        self.sep_bg = "#FFFFFF"
        self.fg = "#FFFFFF"
        self.bg = "#FF00FF"

        super().__init__(self.master)
        self.config(**parse_args(self, kwargs))
        self.overrideredirect(True)
        self.withdraw()
        self.bind("<FocusOut>", self.hide)

    def show(self):
        x, y = self.master.winfo_rootx(), self.master.winfo_rooty() + \
            self.master.winfo_height()
        sb_thickness = self.config_.get('thickness', 30)
        size_x, size_y = self.master.winfo_width() * 2, min(20, len(self.values)) * \
            self.row_height + sb_thickness
        if self.main_frame is not None:
            size_x = min(self.main_frame.winfo_width(), size_x)
        self.geometry("{}x{}+{}+{}".format(size_x, size_y, x, y))
        self.deiconify()
        self.focus_force()

    def hide(self, arg=None):
        self.withdraw()

    def config(self, *args, **kwargs):
        return self.configure(*args, **kwargs)

    def configure(self, *args, **kwargs):
        if not args and not kwargs:
            return super().configure()

        if args:
            for val in args:
                if val not in self.values:
                    self.values.append(val)
            self.update_values()

        catch = ('command', 'elem_per_row', 'scrollbar')
        for key in catch:
            if key in kwargs:
                val = kwargs.pop(key)
                self.__dict__[key] = val

        self.config_ = dict_merge(self.config_, kwargs)

        return super().configure(**parse_args(self, self.config_))

    def root_configure(self, **kwargs):
        if "fg" in kwargs:
            self.fg = kwargs.pop("fg")
        if "bg" in kwargs:
            self.bg = kwargs.pop("bg")
        # kwargs['bg'] = self.fg
        super().configure(**kwargs)

    def entryconfig(self, i, **kwargs):
        self.rows[i].configure(**kwargs)

    def update_values(self):
        if self.main_frame is not None:
            self.main_frame.destroy()

        self.main_frame = ScrollableFrame(
            self, axis="H", scrollbar=self.scrollbar, **self.config_)
        self.main_frame.pack(expand=True, fill="both")

        columns = len(self.values) // self.elem_per_row + 1
        rows = min(self.elem_per_row, len(self.values))

        for i in range(columns):
            self.main_frame.grid_columnconfigure(i * 2, weight=1)
        for i in range(rows):
            self.main_frame.grid_rowconfigure(
                i, weight=1, minsize=self.row_height)

        self.rows = []  # TODO - Empty rows
        if len(self.values) == 0:
            row = Label(
                self.main_frame,
                text='No data!',
                anchor="w"
            )
            row.config(**parse_args(row, self.config_))
            row.grid(
                row=0, 
                column=0, 
                sticky="new"
            )
            self.rows.append(row)

        else:
            for i, val in enumerate(self.values):
                row = Button(
                    self.main_frame, 
                    text=val,
                    command=self.handle_command(val), 
                    anchor="w"
                )
                row.config(
                    **parse_args(row, self.config_)
                    )
                row.grid(
                    row=i % self.elem_per_row, 
                    column=i // self.elem_per_row * 2, 
                    sticky="new"
                )
                self.rows.append(row)

            for i in range(columns - 1):
                sep = Frame(self.main_frame, bg=self.fg, width=2)
                sep.grid(
                    row=0, 
                    column=i * 2 + 1,
                    rowspan=self.elem_per_row, 
                    sticky="ns", 
                    pady=10
                )

        self.main_frame.update_scrollzone()

    def handle_command(self, val):
        def handler():
            self.var.set(val)
            if self.command is not None:
                self.command(val)
        return handler


class EntryWithPlaceholder(Entry):
    def __init__(self, master=None, placeholder="PLACEHOLDER", color='grey', **kwargs):
        super().__init__(master, **kwargs)

        self.placeholder = placeholder
        self.placeholder_color = kwargs.get('color', 'gray')
        self.default_fg_color = self['fg']

        self.bind("<FocusIn>", self.foc_in)
        self.bind("<FocusOut>", self.foc_out)

        self.put_placeholder()

    def put_placeholder(self):
        self.insert(0, self.placeholder)
        self['fg'] = self.placeholder_color

    def foc_in(self, *args):
        if self['fg'] == self.placeholder_color:
            self.delete('0', 'end')
            self['fg'] = self.default_fg_color

    def foc_out(self, *args):
        if self.get() == '':
            self.put_placeholder()


class AnimeListFrame(ScrollableFrame):
    def __init__(self, root, parent, rows_per_page=50, **kwargs):
        self.root = root
        self.parent = parent
        self.database = self.parent.database
        self.animePerRow = self.parent.animePerRow
        self.animePerPage = self.parent.animePerPage
        self.log = self.parent.log

        self.list = []
        self.next_list = None
        self.blank_image = None
        self.list_id = 0

        super().__init__(self.root, **kwargs)

    def find(self, limit=1, **kwargs):
        c = 0
        for anime in self.list:
            if all(anime[k] == v for k, v in kwargs.items()):
                yield anime
                c += 1
                if c >= limit:
                    return

    def remove(self, **kwargs):
        for anime in self.list:
            if all(anime[k] == v for k, v in kwargs.items()):
                self.list.remove(anime)
                break
        self.createList()

    def set(self, data):
        if not isinstance(data, AnimeList):
            raise TypeError(
                "AnimeList instance required, not: {}".format(type(data)))
        else:
            self.list = data
        self.next_list = None
        self.createList()

    def from_filter(self, criteria, listrange=(0, 50)):
        rating_filter = " \nAND (rating NOT IN('R+','Rx') OR rating IS null)"
        if criteria == "DEFAULT":
            table = 'anime'
            filter = "anime.status != 'UPCOMING' AND anime.status != 'UNKNOWN'"
            if self.parent.hideRated:
                filter += rating_filter
            sort = "DESC"
            order = "anime.date_from"
        else:
            # \nAND rating NOT IN('R+','Rx')"
            table = 'anime'
            commonFilter = "\nAND status != 'UPCOMING'"
            order = "date_from"
            sort = "DESC"
            if self.parent.hideRated:
                commonFilter += rating_filter

            if criteria == 'LIKED':
                filter = "like = 1" + commonFilter

            elif criteria == 'NONE':
                filter = "tag IS null OR tag = 'NONE'" + commonFilter

            elif criteria in ['UPCOMING', 'FINISHED', 'AIRING']:
                if criteria == 'UPCOMING':
                    commonFilter = rating_filter if self.parent.hideRated else ""
                    sort = "ASC"
                filter = "status = '{}'".format(criteria) + commonFilter

            elif criteria == 'RATED':
                filter = "rating IN('R+','Rx')\nAND status != 'UPCOMING'"

            elif criteria == "RANDOM":
                order = "RANDOM()"
                filter = "anime.picture is not null"

            else:
                if criteria == 'WATCHING':
                    commonFilter = "\nAND status != 'UPCOMING'"
                    table = 'anime LEFT JOIN broadcasts ON anime.id = broadcasts.id'
                    order = """
                        CASE WHEN anime.status = "AIRING" AND broadcasts.weekday IS NOT NULL
                            THEN (
                                ({}-broadcasts.weekday)%7*24*60
                                +({}-broadcasts.hour)*60
                                +({}-broadcasts.minute)
                                +86400
                            )%86400
                            ELSE "9"
                        END ASC,
                        date_from
                    """
                    tz = timezone(timedelta(hours=9))
                    sort_date = datetime.now(tz)
                    order = order.format(
                        sort_date.weekday(), sort_date.hour, sort_date.minute)
                    # Depend on timezone - TODO
                filter = "tag = '{}'".format(criteria) + commonFilter

        args = {'table': table, 'sort': sort,
                'range': listrange, 'order': order, 'filter': filter}

        def get_next(args):
            listrange = args['range']
            new_list = self.database.filter(**args)
            if not new_list.empty():
                next_range = (listrange[1], listrange[1] +
                              listrange[1] - listrange[0])
                next_args = args.copy()
                next_args['range'] = next_range
                def next_list(args=next_args): return get_next(args)
            else:
                next_list = None
            return new_list, next_list

        self.list, self.next_list = get_next(args)

        self.update_scrollzone()  # Necessary?
        self.createList()

    def createList(self, start=0, waiting=None, list_id=None):
        if list_id is None:
            list_id = self.list_id + 1
            self.list_id = list_id
            # self.log("ANIME_LIST", f'New list id: {list_id}')

        self.generate_list(start, list_id)

    def generate_list(self, start, list_id):
        que = queue.Queue()
        self.parent.getElemImages(que)

        if start == 0:
            try:
                self.canvas.yview_moveto(0)
                while len(self.winfo_children()) > 0:
                    for child in self.winfo_children():
                        child.destroy()

            except Exception as e:
                self.log("MAIN_STATE",
                         "[ERROR] - On AnimeListFrame.create_list():", e)
                return

            if self.list_id != list_id:
                # self.log("ANIME_LIST", f'Interrupted, list id: {list_id}')
                return

        # Ensure the Load More button is on the last column
        anime_count = self.animePerPage // self.animePerRow * self.animePerRow - 1

        ids = set()
        row = []
        self.list_timer = Timer(
            "Anime List Timer", lambda *args: self.log("ANIME_LIST", *args))

        def func(start, stop, list_id):
            def wrapped(i, data):
                if i < start or i >= stop:
                    return False  # == break

                if self.list_id != list_id or self.parent.closing:
                    # self.log("ANIME_LIST", f'Interrupted, list id: {list_id}')
                    return False  # == break

                if data is None:
                    if i == 0:
                        Label(
                            self,
                            text="No results",
                            font=(
                                "Source Code Pro Medium",
                                20),
                            bg=self.parent.colors['Gray2'],
                            fg=self.parent.colors['Gray4'],
                        ).grid(
                            columnspan=self.animePerRow,
                            row=0,
                            pady=50)
                    return False  # == break
                row.append((i, data, que))

                if i % self.animePerRow == 2:
                    while row:
                        args = row.pop(0)
                        tmp = self.create_elem(*args)
                        if tmp:
                            ids.add(tmp)
                        # if args[1]['status'] == 'UPDATE': # TODO - Use a thread?
                        #     self.parent.api.anime(args[1]['id'])
                    if self.list_id != list_id:
                        return False  # == break
            return wrapped

        def cb(list_id):
            def wrapped(i):
                if list_id != self.list_id:
                    return
                try:
                    if ids:
                        with self.database.get_lock():
                            sql = 'UPDATE anime SET status="UPDATE" WHERE id IN (' + ', '.join(
                                str(i) for i in ids) + ')'
                            self.database.sql(sql, get_output=False)

                    if not self.list.empty():
                        self.load_more_button(i - len(row) + 1)
                    else:
                        while row:
                            args = row.pop(0)
                            self.create_elem(*args)

                    self.list_timer.stats()
                    self.parent.stopSearch = True
                finally:
                    que.put("STOP")
            return wrapped

        self.list.map(func(start, anime_count + start, list_id),
                      lambda func: self.after(100, func), cb(list_id))

    def create_elem(self, index, anime, queue):
        self.list_timer.start()
        if self.blank_image is None:
            self.blank_image = self.parent.getImage(None, (225, 310))
        title = anime.title
        if title is None:
            self.list_timer.stop()
            return
        if len(title) > 35:
            title = title[:35] + "..."

        img_can = Canvas(self, width=225, height=310,
                         highlightthickness=0, bg=self.parent.colors['Gray3'])
        img_can.bind("<Button-1>", lambda e,
                     id=anime.id: self.parent.drawOptionsWindow(id))
        img_can.bind("<Button-3>", lambda e, id=anime.id: self.parent.view(id))
        img_can.grid(
            column=index % self.animePerRow,
            row=index // self.animePerRow * 2
        )

        img_can.create_image(0, 0, image=self.blank_image, anchor='nw')
        img_can.image = self.blank_image

        if anime.like == 1:
            title += " ❤"
        lbl = Label(self,
                    text=title,
                    bg=self.parent.colors['Gray2'],
                    fg=self.parent.colors[self.parent.tagcolors[anime.tag]],
                    font=("Source Code Pro Medium", 13),
                    bd=0,
                    wraplength=220)
        lbl.grid(column=index % self.animePerRow,
                 row=(index // self.animePerRow * 2) + 1)
        lbl.name = str(anime.id)

        self.update_scrollzone([img_can, lbl])

        filename = os.path.join(self.parent.cache, str(anime.id) + ".jpg")
        # url = anime.picture
        pics = self.parent.getAnimePictures(anime.id)
        if pics:  # TODO - Choose best pic
            url = pics[0]['url']
            queue.put((filename, url, img_can))
            out = None
        else:
            # with self.database.get_lock():
            #     self.database.sql('UPDATE anime SET status="UPDATE" WHERE id=?', (anime.id,), get_output=False)
            out = anime.id
        self.list_timer.stop()
        return out

    def load_more_button(self, index):
        img_can = Canvas(self, width=225, height=310,
                         highlightthickness=0, bg=self.parent.colors['Gray2'])
        img_can.grid(column=index % self.animePerRow,
                     row=index // self.animePerRow * 2)

        size = 75
        x, y = int(225 / 2 - size / 2), int(310 / 2 - size / 2)
        pos = (x, y + size / 2, x + size, y + size / 2, x + size / 2,
               y + size / 2, x + size / 2, y, x + size / 2, y + size)
        img_can.create_line(*pos, capstyle='round',
                            fill=self.parent.colors['Gray4'], width=15)

        lbl = Label(self, text="Load more...",
                    bg=self.parent.colors['Gray2'], fg=self.parent.colors['Gray4'], font=(
                        "Source Code Pro Medium", 13),
                    bd=0, wraplength=220)
        lbl.grid(column=index % self.animePerRow,
                 row=(index // self.animePerRow * 2) + 1)
        lbl.name = str(-1)

        toDestroy = (img_can, lbl)
        img_can.bind("<Button-1>", lambda e,
                     s=index: self.load_more(index, toDestroy))

    def load_more(self, start, toDestroy):
        [e.destroy() for e in toDestroy]
        self.createList(start=start)


class TableFrame(Frame):
    def __init__(self, parent, keys, cb, scrollbar=True, **kwargs):
        self.keys = keys
        self.sort_key = list(self.keys.keys())[0]
        self.invert_sort = True
        self.cb = cb
        self.use_scrollbar = scrollbar
        self.config_ = kwargs
        self.keys_config = {}
        self.table = []
        self.wid_table = DefaultDict([])
        super().__init__(parent)
        self.configure(**kwargs)

    def draw_keys(self):
        for i, key in enumerate(self.keys):
            self.grid_columnconfigure(i, weight=1)
            self.table_zone.grid_columnconfigure(i, weight=1)
            key_frame = Frame(self)
            key_frame.grid_columnconfigure(0, weight=1)

            b = Button(
                key_frame,
                text=key,
                command=lambda a=key: self.sort_by(a)
            )
            b.configure(
                **parse_args(b, dict_merge(self.config_, self.keys_config)))
            b.grid(row=0, column=0, sticky="nsew")

            if self.sort_key == key:
                if self.invert_sort:
                    sort_txt = "▼"
                else:
                    sort_txt = "▲"
            else:
                sort_txt = "►"

            c = Button(
                key_frame,
                text=sort_txt,
                command=lambda a=key: self.sort_by(a)
            )
            c.configure(
                **parse_args(c, dict_merge(self.config_, self.keys_config)))
            c.grid(row=0, column=1, sticky="nse")

            key_frame.grid(
                row=0,
                column=i,
                sticky="nsew",
                padx=1
            )

    def extend(self, data_list):
        self.table.extend(data_list)

    def add_row(self, data):
        self.table.append(data)

    def pop(self, i):
        return self.table.pop(i)

    def remove(self, data):
        self.table.remove(data)

    def clear(self):
        self.table = []

    def sort_by(self, key):
        if self.sort_key == key:
            self.invert_sort = not self.invert_sort
        else:
            self.sort_key = key
            self.invert_sort = True
        self.draw_table()

    def draw_table(self):
        for w in self.winfo_children():
            w.destroy()

        self.table_zone = ScrollableFrame(
            self, axis="V", scrollbar=False, bg='green')
        self.draw_keys()

        for row, data in enumerate(sorted(self.table, key=lambda e: e.get(self.keys[self.sort_key], -1), reverse=self.invert_sort)):
            for i, key in enumerate(self.keys.values()):
                b = Button(
                    self.table_zone,
                    text=data.get(key, 'Nan'),
                    command=lambda a=data: self.cb(a)
                )
                b.configure(**parse_args(b, self.config_))
                b.grid(
                    row=row + 1,
                    column=i,
                    sticky="nsew"
                )

        self.table_zone.config(**parse_args(self.table_zone, self.config_))
        self.table_zone.grid(
            row=1,
            column=0,
            columnspan=len(self.keys),
            sticky="nsew",
            padx=1
        )
        self.table_zone.update_scrollzone()

        if self.use_scrollbar:
            self.scrollbar = CustomScrollbar(self)

            self.scrollbar.config(
                command=self.table_zone.canvas.yview, orient="vertical")
            self.table_zone.canvas.configure(yscrollcommand=self.scrollbar.set)
            self.scrollbar.grid(
                row=0,
                rowspan=2,
                column=len(self.keys) + 1,
                sticky="ns")

    def configure(self, **kwargs):
        self.config_ = kwargs
        super().configure(**parse_args(self, self.config_))

    def configure_keys(self, **kwargs):
        self.keys_config = kwargs


class Timer():
    def __init__(self, name, logger=None):
        self.startTime = time.time()
        self.name = name

        self.timer = None
        self.timeList = []

        if logger is None:
            self.log = log
        else:
            self.log = logger

    def start(self):
        self.stop()
        self.timer = time.time()

    def stop(self):
        if self.timer is not None:
            self.timeList.append(time.time() - self.timer)
            self.timer = None

    def stats(self):
        nameBracks = "[{}]".format(self.name.center(10))
        total = time.time() - self.startTime
        self.log(nameBracks, "Total:", int(total * 1000), "ms")
        if len(self.timeList) > 0:
            total = sum(self.timeList)
            avg = total / len(self.timeList)
            self.log(nameBracks, "Average:", int(avg * 1000), "ms/loop - Loops:",
                     len(self.timeList), ' (', int(total * 1000), 'ms)')


class LoginDialog(Dialog):

    def __init__(self, fields, title, parent = None, validator=None):

        if len(fields) == 0:
            raise ValueError('You should at least have one field set!')
        
        self.fields = fields

        self.validator = validator

        Dialog.__init__(self, parent, title)

    def body(self, master):
        self.entries = {}

        for i, (field, value) in enumerate(self.fields.items()):
            Label(
                master, 
                text=f"{field.capitalize()}: ", 
                justify='right'
            ).grid(
                row=i, 
                column=0, 
                padx=5, 
                sticky='w'
            )

            entry = Entry(
                master, 
                name="entry_" + field
            )
            if value is not None:
                entry.insert('end', value)
            entry.grid(
                row=i, 
                column=1, 
                padx=5, 
                sticky='we'
            )
            setattr(self, 'entry_'+field, entry)
            self.entries[field] = entry

        return next(iter(self.entries.values()))

    def validate(self):
        try:
            self.results = {}
            for field, entry in self.entries.items():
                self.results[field] = entry.get()
        except Exception as e:
            showwarning(
                "Error",
                "An error occured" + str(e) + "\nPlease try again",
                parent = self
            )
            return 0
        
        check = self.validator(self.results)
        if check != 1:
            showwarning(
                "Error",
                str(check) + "\nPlease try again"
            )
            return 0

        return 1


def parse_args(wid, kwargs):
    return dict((k, v) for k, v in kwargs.items() if k in wid.config().keys())


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
        return None, iter
    else:
        return first, new_iter(first, iter)


def dict_merge(a, b):
    "Used in place of the | operator in 3.10 for compatibility"
    new_dict = {}
    for d in (a, b):
        for k, v in d.items():
            new_dict[k] = v
    return new_dict


def project_modules(root="./"):
    ignore = ("__pycache__", ".git", "venv", "lib", "build", "dist", ".vscode")
    modules = {}
    pattern = re.compile(
        r"(?:from ([\w_\.]*) import \S*)|(?:import ([\w_\.]*))")
    for f in os.listdir(root):
        if f in ignore:
            continue
        path = os.path.realpath(os.path.join(root, f))
        if os.path.isdir(path):
            modules = dict_merge(modules, project_modules(path))
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
    ignore = ("__pycache__", ".git", "venv", "lib", "build", "dist", ".vscode")
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
        log("{} lines in the project, {} files, {} folders, total size: {}".format(
            lines, files, folders, pp_bytes(size)))
    return lines, files, folders, size


if __name__ == "__main__":
    for k, v in project_modules().items():
        log(k, ":")
        for p in v:
            log('   File "{}", line {}'.format(*p))
    project_stats()
