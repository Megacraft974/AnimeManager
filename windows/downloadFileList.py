from tkinter import *

import utils


class DownloadFileList:
	def drawFileListWindow(self, publisher, id):
		# Functions
		if True:
			def startDownload(labels, url, id):
				out = self.downloadFile(id, url=url)
				for label in labels:
					try:
						label.configure(fg=self.colors['Gray4'])
					except Exception:
						pass
				table.update_scrollzone()
				download_cb(out, labels)

			def download_cb(out, labels):
				if out.empty():
					self.fileListWindow.after(10, download_cb, out, labels)
					return
				value = out.get()
				color = 'Blue' if value is True else 'Red'
				for label in labels:
					try:
						label.configure(fg=self.colors[color])
					except Exception:
						pass

		# Window init - Fancy corners - Main frame - Events
		if True:
			size = (self.torrentDDLWindowMinWidth,
					self.torrentDDLWindowMinHeight)
			if self.fileListWindow is None or not self.fileListWindow.winfo_exists():
				self.fileListWindow = utils.RoundTopLevel(
					self.ddlWindow,
					title="Torrents:",
					minsize=size,
					bg=self.colors['Gray2'],
					fg=self.colors['Gray3'])
			else:
				self.fileListWindow.clear()

			table = utils.ScrollableFrame(
				self.fileListWindow, bg=self.colors['Gray2'])
			table.pack(expand=True, fill="both", padx=20)

			# keys = {"Title": "name", "Seeds": "seeds", "Leechs": "leech", "Size": "filesize"}
			# table = TableFrame(scroll_frame, keys, )
			table.grid_columnconfigure(0, weight=1)

		# Torrent list
		if True:
			data = self.ddlWindow.publisherData[publisher]

			maxTitleLength = min(70, len(
				sorted(
					(d['name'] for d in data),
					key=len,
					reverse=True)[0]))
			maxSizeLength = len(
				str(sorted((d['size'] for d in data), reverse=True)[0]))

			for row, d in enumerate(data):
				title = d['name']
				fg = self.getTorrentColor(title)
				# title = d['name'].ljust(maxLength) + "-" + d['size']
				bg = (self.colors['Gray3'], self.colors['Gray2'])[row % 2]
				
				title = title[(len(publisher) + 3):]
				if len(title) < 70:
					name_short = title
				else:
					name_short = title[:35] + '...' + title[-25:]

				kwargs = {
					'master': table,
					'font': ("Source Code Pro Medium", 13),
					'bg': bg,
					'fg': fg
				}

				titleLbl = Label(text=(name_short).ljust(maxTitleLength), **kwargs)
				titleLbl.grid(row=row, column=0, sticky="nsew")

				seedsLbl = Label(text=(str(d['seeds']) + "▲").rjust(5) + "   ", **kwargs)
				seedsLbl.grid(row=row, column=1, sticky="nsew")

				leechsLbl = Label(text=(str(d['leech']) + "▼").rjust(5) + "   ", **kwargs)
				leechsLbl.grid(row=row, column=2, sticky="nsew")

				sizeLbl = Label(text=str(d['size']).rjust(maxSizeLength), **kwargs)
				sizeLbl.grid(row=row, column=3, sticky="nsew")

				engineLbl = Label(text=str(d['engine_url'][:30]).rjust(30), **kwargs)
				engineLbl.grid(row=row, column=4, sticky="nsew")

				def command(e, labels=(titleLbl, sizeLbl, seedsLbl, leechsLbl), url=d['link'], id=id):
					return startDownload(labels, url, id)

				titleLbl.bind("<Button-1>", command)
				seedsLbl.bind("<Button-1>", command)
				leechsLbl.bind("<Button-1>", command)
				sizeLbl.bind("<Button-1>", command)
				
			table.update_scrollzone()
