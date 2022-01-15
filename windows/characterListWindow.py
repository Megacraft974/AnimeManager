import threading
import time
import queue
import os
import io

from tkinter import *
from PIL import Image, ImageTk

import utils
from classes import CharacterList, Character


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

                can.create_image(0, 0, image=self.blank_image, anchor='nw')
                can.image = self.blank_image

                title = character.name
                if len(title) >= 20:
                    title = title[:15] + "..."
                if bool(character.like):
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

                filename = os.path.join(self.cache, "c" + str(character['id']) + ".jpg")
                url = character.picture
                queue.put((filename, url, can))

            def getCharacters(id):
                database = self.getDatabase()
                if id == "LIKED":
                    data = database.sql("""
                        SELECT * FROM characters
                        WHERE like = 1
                        GROUP BY id
                        ORDER BY anime_id;""", to_dict=True)
                else:
                    data = database.sql(
                        "SELECT * FROM characters WHERE anime_id=?;", (id,), to_dict=True)
                # keys = list(self.database.keys(table="characters"))
                characters = CharacterList(database.get_all_metadata(Character(c)) for c in data)
                return characters

            def reload(id, c):
                if getCharacters(id) != c:
                    self.characterList.after(1, self.characterListWindow, id, False)

            def update(id):
                self.getCharactersData(id)
                parent.after(1, self.characterListWindow, id)

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
                self.characterListTable.update()
                characters = self.getCharactersData(id)
                while not characters.is_ready() and not characters.empty():
                    if self.root is not None:
                        self.root.update()
                        time.sleep(0.01)
                    else:
                        self.characterList.exit()
                        return
                loadLbl.destroy()
            else:
                characters = getCharacters(id)

        # Characters list
        if True:

            for x in range(self.animePerRow):
                self.characterListTable.grid_columnconfigure(x, weight=1)

            keys = ('id', 'anime_id', 'name', 'role', 'picture', 'desc')

            # que = queue.Queue()
            # thread = threading.Thread(target=getImages, args=(que,), daemon=True)
            # thread.start()
            que = queue.Queue()
            self.getElemImages(que)

            index = None
            for index, character in enumerate(characters):
                if self.closing or self.characterList is None or not self.characterList.winfo_exists():
                    return

                try:
                    characterCell(character, index, que)
                except Exception as e:
                    self.log("MAIN_STATE", "[ERROR] - Can't create cell for character:", character.name, "-", character.id, "-", e)

                if index % self.animePerRow == 0:
                    self.characterListTable.grid_rowconfigure(index, weight=1)
                    self.characterListTable.update()

            que.put("STOP")

            if self.closing or self.characterListTable.winfo_exists():
                if index is None:
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
