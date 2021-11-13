import os

from tkinter import *
from tkinter.ttk import Progressbar


class loadingWindow:
    def loadingWindow(self):
        if self.root is None:
            self.loadfen = Tk()
        else:
            self.loadfen = Toplevel(self.root)

        self.loadfen.geometry("920x500+{}+{}".format(100, 100))
        self.loadfen.configure(bg=self.colors['Gray3'])
        self.loadfen.title("Nyaa.si - Custom Browser - Loading...")
        self.loadfen.wm_iconphoto(False, self.getImage(
            os.path.join(self.iconPath, 'favicon.png')))

        main = Frame(self.loadfen, width=920, bg=self.colors['Gray2'])
        for i in range(2):
            main.grid_rowconfigure(i, weight=1)
        main.grid_columnconfigure(0, weight=1)

        Label(main, text="Loading...", bg=self.colors['Gray2'], fg=self.colors['Gray4'], font=(
            "Source Code Pro Medium", 20)).grid(row=0, column=0, sticky="s")
        self.loadLabel = Label(
            main, text="-/-, -:-", bg=self.colors['Gray2'], fg=self.colors['Gray4'], font=("Source Code Pro Medium", 20))
        self.loadLabel.grid(row=1, column=0, sticky="n")
        main.pack(fill="both", expand=True)

        self.loadProgress = Progressbar(
            self.loadfen, orient=HORIZONTAL, length=500, mode='determinate')
        self.loadProgress.pack(side="bottom", padx=10, pady=10)

        self.loadfen.update()
