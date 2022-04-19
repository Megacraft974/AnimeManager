from tkinter import *

import utils


class logWindow():
    def logWindow(self):
        # Functions
        if True:
            def addLog(text):
                print("------------------" + text, flush=True)
                panel = self.logPanel.panel
                row = self.logPanel.row
                bg = 'Gray2' if row % 2 == 1 else "Gray3"

                cell = Frame(panel, bg=self.colors["Gray2"])
                Label(
                    cell,
                    text=text,
                    bg=self.colors[bg],
                    fg=self.colors["White"],
                    font=("Source Code Pro Medium", 13)
                ).pack(fill="both", expand=True)
                cell.grid(column=0, row=row, sticky="ew")

                panel.grid_rowconfigure(row, weight=1)
                self.logPanel.row += 1

            def removeLog(func):
                if self.loggingCb == func:
                    self.loggingCb = None

        # Window init
        if True:
            if self.logPanel is None or not self.logPanel.winfo_exists():
                size = (1000, 500)
                self.logPanel = utils.RoundTopLevel(
                    self.fen,
                    title="Logs",
                    minsize=size,
                    bg=self.colors["Gray2"],
                    fg=self.colors["Gray3"]
                )
            else:
                self.logPanel.clear()
            self.logPanel.grid_rowconfigure(0, weight=1)
            self.logPanel.grid_columnconfigure(0, weight=1)

        # Main Panel
        if True:
            panel = utils.ScrollableFrame(self.logPanel, scrollbar=True, bg=self.colors["Gray2"])
            panel.grid(row=0, column=0, sticky="nsew")
            panel.grid_columnconfigure(0, weight=1)

            self.logPanel.panel = panel
            self.logPanel.row = 0
            self.loggingCb = addLog
            self.logPanel.bind("<Destroy>", lambda e: removeLog(addLog))
