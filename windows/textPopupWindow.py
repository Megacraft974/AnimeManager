from tkinter import *

import utils


class textPopupWindow:
    def textPopupWindow(self, parent, title, callback, fentype="TEXT"):
        # Main window
        if True:
            if self.popupWindow is not None and self.popupWindow.winfo_exists():
                self.popupWindow.exit()
                self.popupWindow.destroy()
            self.popupWindow = utils.RoundTopLevel(parent, title=title, minsize=(
                750, 150), bg=self.colors['Gray2'], fg=self.colors['Gray3'])

        if fentype == "TEXT":
            var = StringVar()
            e = Entry(
                self.popupWindow,
                textvariable=var,
                highlightthickness=0,
                borderwidth=0,
                font=(
                    "Source Code Pro Medium",
                    13),
                bg=self.colors['Gray3'],
                fg=self.colors['White'])
            e.bind("<Return>", lambda e, var=var: callback(var))
            e.grid(row=0, column=0, sticky="nsew", padx=5, pady=(0, 20))
            self.popupWindow.handles.append(e)
            Button(
                self.popupWindow,
                text="Ok",
                bd=0,
                height=1,
                relief='solid',
                font=(
                    "Source Code Pro Medium",
                    13),
                activebackground=self.colors['Gray2'],
                activeforeground=self.colors['Gray3'],
                bg=self.colors['Gray3'],
                fg=self.colors['Gray2'],
                command=lambda var=var: callback(var)).grid(
                row=0,
                column=1,
                sticky="nsew",
                pady=(
                    0,
                    20))

            self.popupWindow.update()
        else:
            self.log("ERROR", "Unknown window type", fentype)
            raise
