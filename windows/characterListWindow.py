import threading
import time
import queue
from tkinter import *

import utils


class characterListWindow:
    def characterListWindow(self, id, update=True):
        # Functions
        if True:
            def characterCell(character, index, queue):
                database = self.getDatabase()

                size = (225, 310)
                cell = Frame(self.characterListTable, bg=self.colors['Gray3'])
                cell.grid_rowconfigure(0, weight=1)
                cell.grid_columnconfigure(0, weight=1)

                can = Canvas(
                    cell,
                    width=size[0],
                    height=size[1],
                    highlightthickness=0,
                    bg=self.colors['Gray3'])
                can.grid(row=0, column=0, sticky="ns")
                can.bind("<Button-1>", lambda e,
                         a=character: self.characterWindow(a))

                filename = os.path.join(
                    self.cache, "c" + str(character['id']) + ".jpg")

                if "c" + str(character['id']) + \
                        ".jpg" in os.listdir(self.cache):
                    im = Image.open(filename)
                    image = self.getImage(filename)
                    loadImg = False
                else:
                    im = Image.new('RGB', (225, 310), self.colors['Gray'])
                    loadImg = True
                    self.log(
                        'DISK_ERROR',
                        "[ERROR] - Can't open image for character",
                        character['name'],
                        "id",
                        character['id'])
                    image = ImageTk.PhotoImage(im)

                can.create_image(size[0] / 2, size[1] / 2,
                                 image=image, anchor='center')
                can.image = image

                title = character['name']
                if len(title) >= 20:
                    title = title[:15] + "..."
                if database.exist(id=character['id'], table='characters') and bool(database(id=character['id'], table='characters')['like']):
                    title += " ❤"
                color = 'Blue' if character['role'] == 'main' else 'White'
                b = Button(
                    cell,
                    text=title,
                    bd=0,
                    height=1,
                    relief='solid',
                    font=(
                        "Source Code Pro Medium",
                        13),
                    activebackground=self.colors['Gray2'],
                    activeforeground=self.colors[color],
                    bg=self.colors['Gray3'],
                    fg=self.colors[color],
                    command=lambda a=character: self.characterWindow(a))
                b.name = character['id']
                b.grid(row=1, column=0, sticky="nsew")

                x, y = index // self.animePerRow, index % self.animePerRow
                cell.grid(row=x, column=y, sticky="nsew", pady=2, padx=2)

                if loadImg:
                    queue.put((filename, character, can))
                    # threading.Thread(target=downloadPic,args=(filename,character,can)).start()

            def getImages(queue):
                def downloadPic(filename, character, can):
                    if character['picture'] is None:
                        return
                    self.log("NETWORK", "Requesting picture for character id",
                             character['id'], "name", character["name"])
                    raw_data = requests.get(character['picture']).content
                    im = Image.open(io.BytesIO(raw_data))
                    im = im.resize((225, 310))
                    if im.mode != 'RGB':
                        im = im.convert('RGB')
                    im.save(filename)

                    image = ImageTk.PhotoImage(im, master=self.characterList)
                    try:
                        can.create_image(0, 0, image=image, anchor='nw')
                        can.image = image
                    except BaseException:
                        pass

                while True:
                    if queue.empty():
                        time.sleep(0.01)
                    else:
                        args = queue.get()
                        if args == "STOP":
                            break
                        downloadPic(*args)

            def getCharacters(id):
                database = self.getDatabase()
                if id == "LIKED":
                    characters = database.sql("""
                        SELECT * FROM characters
                        WHERE like = 1
                        GROUP BY id
                        ORDER BY anime_id;""")
                else:
                    characters = database.sql(
                        "SELECT * FROM characters WHERE anime_id=?;", (id,))
                return characters

            def reload(id, c):
                if getCharacters(id) != c:
                    self.characterList.after(
                        1, lambda id=id: self.characterListWindow(id, False))

            def update(id):
                self.getCharactersData(id)
                parent.after(1, lambda id=id: characterListWindow(id))

        # Main window - Fancy corners - Events
        if True:
            size = (self.characterListWindowMinWidth,
                    self.characterListWindowMinHeight)
            if self.choice is not None and self.choice.winfo_exists():
                parent = self.choice
            else:
                parent = self.fen

            if self.characterList is None or not self.characterList.winfo_exists():
                self.characterList = utils.RoundTopLevel(
                    parent,
                    title="Characters",
                    minsize=size,
                    bg=self.colors['Gray3'],
                    fg=self.colors['Gray2'])
            else:
                self.characterList.clear()
            # self.characterList.titleLbl.configure(text="Characters", bg= self.colors['Gray3'], fg= self.colors['Gray2'], font=("Source Code Pro Medium",18))

            self.characterListTable = utils.ScrollableFrame(
                self.characterList, bg=self.colors['Gray3'])
            self.characterListTable.pack(expand=True, fill="both")

            self.characterListTable.grid_columnconfigure(0, weight=1)

            self.characterList.update()

        # Data check
        if True:
            sql = "SELECT EXISTS(SELECT 1 FROM characters WHERE anime_id = ?);"
            empty = not bool(self.database.sql(sql, (id,))[0][0])
            if id != "LIKED" and empty:
                loadLbl = Label(
                    self.characterListTable,
                    text="Loading data...",
                    bg=self.colors['Gray3'],
                    fg=self.colors['Gray2'],
                    font=(
                        "Source Code Pro Medium",
                        18))
                loadLbl.pack(fill="both", expand=True, pady=10, side=BOTTOM)
                thread = threading.Thread(
                    target=self.getCharactersData, args=(id,))
                thread.start()
                while thread.is_alive():
                    if self.root is not None:
                        self.root.update()
                        time.sleep(0.01)
                    else:
                        self.characterList.exit()
                        return
                loadLbl.destroy()

        # Characters list
        if True:
            characters = getCharacters(id)

            # if update:
            #     thread = threading.Thread(target=self.getCharactersData, args=(id,lambda id=id,c=characters:reload(id,c)))
            #     thread.start()

            maxX = len(characters) // self.animePerRow
            [self.characterListTable.grid_rowconfigure(
                x, weight=1) for x in range(maxX)]
            # [self.characterListTable.grid_columnconfigure(y,weight=1) for y in range(max(len(characters),self.animePerRow))]

            for x in range(min(len(characters), self.animePerRow)):
                self.characterListTable.grid_columnconfigure(x, weight=1)
                # Frame(self.characterListTable,bg=self.colors['Gray3']).grid(row=0,column=x,sticky="nsew")

            que = queue.Queue()
            keys = ('id', 'anime_id', 'name', 'role', 'picture', 'desc')

            thread = threading.Thread(target=getImages, args=(que,))
            thread.start()

            for index, data in enumerate(characters):
                if self.characterList is None:
                    break

                character = dict(zip(keys, data))
                try:
                    characterCell(character, index, que)
                    self.characterListTable.update()
                except BaseException:
                    pass

            que.put("STOP")
            while not que.empty() and self.characterList is not None and self.characterList.winfo_exists():
                self.characterList.update()
                time.sleep(0.01)

            if self.characterListTable.winfo_exists():
                self.characterListTable.grid_columnconfigure(0, weight=1)
                if len(characters) == 0:
                    Label(
                        self.characterListTable,
                        text="No characters",
                        font=(
                            "Source Code Pro Medium",
                            13),
                        bg=self.colors['Gray3'],
                        fg=self.colors['Red'],
                    ).grid(
                        row=0,
                        column=0,
                        sticky="nsew",
                        pady=2,
                        padx=2)
                self.characterListTable.update()
