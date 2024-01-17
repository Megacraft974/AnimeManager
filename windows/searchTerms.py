import os
from tkinter import *

from .. import utils


class SearchTerms:
    def drawSearchTermsWindow(self, id, parent=None):
        # Functions
        if True:
            def getsearchTermsWindow(id):
                with self.database.get_lock():
                    data = self.database.sql(
                        "SELECT value FROM title_synonyms WHERE id=?", (id,))
                return [row[0] for row in data]

            def draw_table(table, id):
                timer = utils.Timer('Draw search terms table', logger=lambda *args,
                                    **kwargs: self.log('FILE_SEARCH', *args, **kwargs))
                i = None

                terms = getsearchTermsWindow(id)

                deleteIcon = self.getImage(os.path.join(
                    self.iconPath, "delete.png"), (20, 20))

                for i, term in enumerate(terms):
                    timer.start()

                    if term is None:
                        continue

                    # Alternating bg color
                    bg = (self.colors['Gray3'], self.colors['Gray2'])[i % 2]

                    # Avoid raising an error when the window is closing
                    if self.closing or not self.searchTermsWindow.winfo_exists():
                        return

                    row = Frame(table,
                                bg=bg
                                )

                    Label(
                        row,
                        text=term,
                        bd=0,
                        height=1,
                        font=(
                            "Source Code Pro Medium",
                            13),
                        bg=bg,
                        fg=self.colors['White'],
                    ).grid(
                        row=0,
                        column=0,
                        sticky="nsew"
                    )

                    b = Button(
                        row,
                        image=deleteIcon,
                        bd=0,
                        height=1,
                        relief='solid',
                        font=(
                            "Source Code Pro Medium",
                            13),
                        activebackground=self.colors['Gray3'],
                        activeforeground=self.colors['White'],
                        bg=bg,
                        fg=self.colors['White'],
                        command=lambda term=term, id=id, table=table:
                            self.removeSearchTerm(id, term, lambda: draw_table(table, id))
                    )

                    b.image = deleteIcon
                    b.grid(
                        row=0,
                        column=1,
                        sticky="nsew"
                    )

                    row.grid_columnconfigure(0, weight=1)
                    row.grid(
                        row=i,
                        column=0,
                        sticky='nsew'
                    )

                try:
                    if i is None:
                        self.searchTermsWindow.titleLbl['text'] = "No search terms!"
                    else:
                        self.searchTermsWindow.titleLbl['text'] = "Search terms"
                except TclError:
                    pass
                table.update_scrollzone()

                timer.stats()

        # Window init - Fancy corners - Main frame - Events
        if True:
            size = (self.searchTermsWindowMinWidth,
                    self.searchTermsWindowMinHeight)
            if self.searchTermsWindow is None or not self.searchTermsWindow.winfo_exists():
                if parent is None:
                    parent = self.ddlWindow

                self.searchTermsWindow = utils.RoundTopLevel(
                    parent,
                    title="Search terms",
                    minsize=size,
                    bg=self.colors['Gray2'],
                    fg=self.colors['Gray3'])
            else:
                self.searchTermsWindow.clear()

        # Terms list
        if True:
            table = utils.ScrollableFrame(
                self.searchTermsWindow, bg=self.colors['Gray2'])
            table.grid_columnconfigure(0, weight=1)
            table.grid(sticky="nsew")

            draw_table(table, id)  # Draw table content

        if self.closing or not self.searchTermsWindow.winfo_exists():
            return

    def addSearchTerms(self, id, term, cb=None):
        with self.database.get_lock():
            exists = self.database.sql(
                "SELECT EXISTS( SELECT 1 FROM title_synonyms WHERE id=? AND value=? )", (
                    id, term)
            )
            if not bool(exists[0][0]):
                self.database.sql(
                    "INSERT INTO title_synonyms(id, value) VALUES (?, ?)", (id, term), get_output=False)

        if cb:
            cb()

    def removeSearchTerm(self, id, term, cb=None):
        with self.database.get_lock():
            self.database.sql(
                "DELETE FROM title_synonyms WHERE id=? AND value=?", (id, term), get_output=False)
        if cb:
            cb()
