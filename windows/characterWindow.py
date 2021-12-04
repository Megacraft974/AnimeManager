import threading
import re
from tkinter import *

import utils


class characterWindow:
    def characterWindow(self, character, update=True):
        # Functions
        if True:
            def like(id, b):
                d = self.database(id=id, table='characters')
                liked = self.database.exist(id=id, table='characters') and bool(d['like'])
                self.database.set({'id': id, 'like': not liked})

                if not liked:
                    im_path = os.path.join(self.iconPath, "heart.png")
                else:
                    im_path = os.path.join(self.iconPath, "heart(1).png")

                iconSize = (30, 30)
                self.getImage(im_path, iconSize)
                b.configure(image=image)
                b.image = image
                b.update()

                for but in self.characterListTable.winfo_children():
                    if but.winfo_class() == 'Button' and but.name == id:
                        text = but.cget("text").replace(" ❤", "")
                        if not liked:
                            text += " ❤"
                        but['text'] = text
                        but.update()
                        break

            def switchAnime(id):
                try:
                    self.characterInfo.exit()
                except BaseException:
                    pass
                try:
                    self.characterList.exit()
                except BaseException:
                    pass
                try:
                    self.reload(id, False)
                except BaseException:
                    self.optionsWindow(id)

            def update(c):
                c = self.getCharacterData(c['id'])
                try:
                    self.characterInfo.after(
                        1, lambda c=c: self.characterWindow(c, update=False))
                except BaseException:
                    pass

        # Main window - Fancy corners - Events
        if True:
            size = (self.characterInfoWindowMinWidth,
                    self.characterInfoWindowMinHeight)
            if self.characterInfo is None or not self.characterInfo.winfo_exists():
                self.characterInfo = utils.RoundTopLevel(
                    self.characterList,
                    title="Loading data...",
                    minsize=size,
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray3'])
            else:
                self.characterInfo.clear()
            self.characterInfo.grid_rowconfigure(1, weight=1)
            self.characterInfo.grid_columnconfigure(1, minsize=250, weight=1)

        # Data check
        if True:
            if 'desc' not in character.keys() or character['desc'] is None:
                # self.characterInfo.titleLbl.configure(text="Loading data...", bg= self.colors['Gray2'], fg= self.colors['Gray3'], font=("Source Code Pro Medium",18))

                # thread = threading.Thread(target=self.getCharacterData, args=(character['id'],))
                # thread.start()
                # while thread.is_alive():
                #     self.characterInfo.update()
                #     time.sleep(0.01)

                if update:
                    thread = threading.Thread(target=update, args=(character,))
                    thread.start()

                data = self.database.sql(
                    "SELECT * FROM characters WHERE anime_id=? AND id=?;",
                    (character['anime_id'],
                     character['id']))[0]
                keys = ('id', 'anime_id', 'name', 'role', 'picture', 'desc')
                # character = {key:(json.loads(data[i]) if type(data[i]) == str else data[i]) for i,key in enumerate(keys)}
                character['desc'] = data[5]

        # Picture
        if True:
            filename = os.path.join(
                self.cache, "c" + str(character['id']) + ".jpg")

            if "c" + str(character['id']) + ".jpg" in os.listdir(self.cache):
                im = self.getImage(filename)
            else:
                raw_data = requests.get(character['picture']).content
                im = Image.open(io.BytesIO(raw_data))
                im = im.resize((225, 310))
                if im.mode != 'RGB':
                    im = im.convert('RGB')
                im.save(filename)

                image = ImageTk.PhotoImage(im)

            try:
                can = Canvas(self.characterInfo, width=225, height=310,
                             highlightthickness=0, bg=self.colors['Gray3'])
                can.grid(row=0, column=0, rowspan=2)
                can.create_image(0, 0, image=image, anchor='nw')
                can.image = image
            except BaseException:
                try:
                    self.characterInfo.exit()
                except BaseException:
                    pass

        # Title panel
        if True:
            self.characterInfo.titleFrame.destroy()
            titleFrame = Frame(self.characterInfo, bg=self.colors['Gray2'])
            titleFrame.grid_columnconfigure(0, weight=1)

            titleLbl = Label(titleFrame, text=character['name'], wraplength=500, bg=self.colors['Gray2'], font=(
                "Source Code Pro Medium", 18), fg=self.colors['Blue' if character['role'] == "Main" else 'White'])
            titleLbl.grid(row=0, column=0, sticky="nsew", columnspan=2)
            self.characterInfo.titleLbl = titleLbl
            self.characterInfo.handles = [titleLbl]
            self.characterInfo.update()

            if self.database.exist(id=character['id'], table='characters') and bool(self.database(id=character['id'], table='characters')['like']):
                im_path = os.path.join(self.iconPath, "heart.png")
            else:
                im_path = os.path.join(self.iconPath, "heart(1).png")
            iconSize = (30, 30)
            image = self.getImage(im_path, iconSize)

            Button(
                titleFrame,
                text="Go to anime",
                bd=0,
                height=1,
                relief='solid',
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['White'],
                bg=self.colors['Gray3'],
                fg=self.colors['White'],
                command=lambda id=character['anime_id']: switchAnime(id)).grid(
                row=1,
                column=0,
                sticky="nsew",
                padx=(
                    20,
                    0))

            likeButton = Button(
                titleFrame,
                image=image,
                bd=0,
                relief='solid',
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['White'],
                bg=self.colors['Gray2'],
                fg=self.colors['White'],
            )
            likeButton.configure(
                command=lambda id=character['id'], b=likeButton: like(id, b))
            likeButton.image = image
            likeButton.grid(row=1, column=1, sticky="nsew", padx=5)

            titleFrame.grid(row=0, column=1, sticky="nsew")

        # Info panel
        if True:
            infoFrame = Frame(self.characterInfo, bg=self.colors['Gray2'])

            if 'desc' in character.keys() and character['desc'] is not None:
                desc = "\n".join(re.findall(
                    r'([^\n]{1,40}\S+)|[\n]+', character['desc'], re.M))
                lines = len(desc.split("\n"))
                if lines > 50:
                    Label(
                        infoFrame,
                        text="\n".join(
                            desc.split("\n")[
                                :lines // 2]),
                        wraplength=800,
                        font=(
                            "Source Code Pro Medium",
                            10),
                        bg=self.colors['Gray2'],
                        fg=self.colors['White']).grid(
                        row=0,
                        column=0,
                        sticky="n")
                    Frame(infoFrame, width=2, bg=self.colors['Gray4']).grid(
                        row=0, column=1, sticky="ns", padx=10)
                    Label(
                        infoFrame,
                        text="\n".join(
                            desc.split("\n")[
                                lines // 2:]),
                        wraplength=800,
                        font=(
                            "Source Code Pro Medium",
                            10),
                        bg=self.colors['Gray2'],
                        fg=self.colors['White']).grid(
                        row=0,
                        column=2,
                        sticky="n")
                else:
                    Label(
                        infoFrame,
                        text=desc,
                        wraplength=500,
                        font=(
                            "Source Code Pro Medium",
                            10),
                        bg=self.colors['Gray2'],
                        fg=self.colors['White']).grid(
                        row=0,
                        column=0)
            else:
                if update:
                    Label(
                        infoFrame,
                        text="Loading...",
                        font=(
                            "Source Code Pro Medium",
                            10),
                        bg=self.colors['Gray2'],
                        fg=self.colors['White']).grid(
                        row=0,
                        column=0)

                else:
                    Label(
                        infoFrame,
                        text="No description",
                        font=(
                            "Source Code Pro Medium",
                            10),
                        bg=self.colors['Gray2'],
                        fg=self.colors['White']).grid(
                        row=0,
                        column=0)
            # desc
            # infoFrame.grid_rowconfigure(0,weight=1)
            infoFrame.grid_columnconfigure(0, weight=1)
            infoFrame.grid(row=1, column=1, sticky="nsew",
                           padx=(20, 0), pady=(10, 0))

            self.characterInfo.update()
