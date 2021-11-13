from tkinter import *

import utils


class seasonSelector:
    def seasonSelector(self):
        # Window init
        if True:
            size = (self.seasonChooserMinWidth, self.seasonChooserMinHeight)
            self.seasonChooser = utils.RoundTopLevel(
                self.fen, title="Season selector", minsize=size, bg=self.colors['Gray3'], fg=self.colors['Gray2'])
            self.seasonChooser.titleLbl.configure(
                text="Season selector", bg=self.colors['Gray3'], fg=self.colors['Gray2'], font=("Source Code Pro Medium", 18))
            self.season_ids = []

            table = utils.ScrollableFrame(
                self.seasonChooser, bg=self.colors['Gray2'])
            table.pack(expand=True, fill="both", padx=20)

            [table.grid_columnconfigure(i, weight=1) for i in range(5)]
            # table.grid_columnconfigure(0,weight=1)

            self.seasonChooser.update()

        # Table init
        if True:
            today = date.today()
            currentYear, currentMonth = today.year, today.month
            startYear = currentYear + 5
            stopYear = 1920
            for i, year in enumerate(range(startYear, stopYear, -1)):
                fg = self.colors['White' if year <= currentYear else 'Blue']
                bg = self.colors['Gray2' if i % 2 == 0 else 'Gray3']
                Label(table, text=str(year), bg=bg, fg=fg, font=("Source Code Pro Medium", 18)
                      ).grid(row=i, column=0, sticky="nsew")
                for j, season in enumerate(self.seasons.keys()):
                    if year == currentYear:
                        if self.seasons[season]['start'] > currentMonth:
                            fg = self.colors['Blue']
                        else:
                            fg = self.colors['White']

                    cell = Button(table, text=season.capitalize(), bd=0, height=1, relief='solid', font=("Source Code Pro Medium", 15),
                                  activebackground=self.colors['Gray2'], activeforeground=self.colors['White'], bg=bg, fg=fg,
                                  command=lambda y=year, s=season: self.getSeason(y, s))
                    cell.grid(row=i, column=j + 1, sticky="nsew")

        table.update()
        self.seasonChooser.update()
