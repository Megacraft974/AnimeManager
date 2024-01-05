import os
import threading
import subprocess
import time

from operator import itemgetter
from datetime import date, datetime, timedelta, time as datetime_time, timezone
from tkinter import *
from tkinter.ttk import Progressbar

import qbittorrentapi.exceptions

from .. import utils


class optionsWindow:
	def drawOptionsWindow(self, id):
		# Functions
		if True:
			def findTorrent(id):
				if self.animeHashes.get(id):
					return

				if self.getQB() == "OK":
					database = self.getDatabase()

					torrents = database.get_metadata(id, "torrents")
					if torrents == []:
						self.animeHashes[id] = None
						return

					torrent_hashes = []
					for t in torrents:
						path = os.path.join(self.torrentPath, t)
						if os.path.exists(path):
							torrent_hash = self.getTorrentHash(path)
							torrent_hashes.append(torrent_hash)
					try:
						qbtorrents = self.qb.torrents_info(
							status_filter="downloading", torrent_hashes="|".join(torrent_hashes))
					except qbittorrentapi.exceptions.APIConnectionError:
						self.log('MAIN_STATE',
								 '[ERROR] - Error while connecting to torrent client')
					else:
						if len(qbtorrents) > 0:
							self.animeHashes[id] = qbtorrents[0].hash
							self.optionsWindow.after(10, self.reload, id, False)

			def updateLoadingBar(id, bar, text):
				if not self.animeHashes.get(id):
					return
				hash = self.animeHashes.get(id)
				try:
					torrent = self.qb.torrents_properties(hash)
				except qbittorrentapi.exceptions.NotFound404Error:
					value = 100
				except qbittorrentapi.exceptions.APIConnectionError:
					self.log(
						"NETWORK", "[ERROR] - Couldn't find the torrent client!")
					value = 100
				else:
					value = torrent.pieces_have / torrent.pieces_num * 100
				if value == 100:
					self.animeHashes[id] = None
					self.reload(id, update=False)
				else:
					try:
						bar['value'] = value
						# TODO - Fill with zeros
						text.configure(text=str(round(value, 2)) + "%")
					except Exception:
						pass
					self.optionsWindow.after(500, updateLoadingBar, id, bar, text)

			def updateEpisodes(epsList, title, folder):
				eps = self.getEpisodes(folder)
				if len(eps) >= 1 and list(eps)[0] is not None:
					titles = [e['title'] for e in eps]
					state = "normal"
				else:
					titles = []
					state = "disabled"

				if not 'var' in epsList.__dict__:
					# Was probably removed
					return
				var = epsList.var

				epsList.configure(
					*titles,
					command=lambda e, title=title, var=var:
						watch(title, e, eps, var),
					state=state
				)

				colorFileEntries(id, eps, epsList)
				epsList.bind(
					"<Button-3>",
					lambda
						title=title,
						var=var: 
					openEps(title, eps, var))
				epsList.bind(
					"<Button-1>",
					lambda
						e,
						a=id,
						b=eps,
						c=epsList: 
					colorFileEntries(a, b, c)
				)

			def colorFileEntries(id, eps, epsList):
				last_seen = self.database(id=id, table="anime")['last_seen']
				if len(eps) >= 1 and list(eps)[0] is not None:
					pathList = [os.path.normpath(i['path']) for i in eps]
				else:
					pathList = []
				if last_seen is not None and os.path.normpath(last_seen) in pathList:
					for i in range(pathList.index(os.path.normpath(last_seen)) + 1):
						epsList.menu.entryconfig(
							i, foreground=self.colors['Green'])

			def like(id, b):
				liked = bool(self.database(id=id, table='anime').like)
				self.database.set({'id': id, 'like': not liked},
								  table='anime', get_output=False)

				if not liked:
					im_path = os.path.join(self.iconPath, "heart.png")
				else:
					im_path = os.path.join(self.iconPath, "heart(1).png")

				folder = self.getFolder(id)
				showFolderButtons = folder is not None and os.path.isdir(
					os.path.join(self.animePath, folder))

				iconSize = (50, 50) if showFolderButtons else (30, 30)
				image = self.getImage(im_path, iconSize)
				b.configure(image=image)
				b.image = image

				for lbl in self.animeList.winfo_children():
					if lbl.winfo_class() == 'Label' and lbl.name == str(id):
						text = lbl.cget("text").replace(" ❤", "")
						if not liked:
							text += " ❤"
						lbl['text'] = text
						break

			def watch(title, file, eps, var):
				var.set("Watch")
				video = [i['title'] for i in eps].index(file)
				playlist = [i['path'] for i in eps]
				self.log('MAIN_STATE', "Watching", file)
				self.RPC_watching(title, eps=[video + 1, len(eps)])
				self.player(playlist, video, id, self.dbPath,
							callback=self.RPC_stop_watching)

			def openEps(e, eps, var):
				var.set("Watch")
				playlist = [os.path.normpath(i['path']) for i in eps.values()]
				folder = os.path.dirname(playlist[0])
				self.log('MAIN_STATE', "Opening", len(playlist), "files")
				subprocess.call(
					[os.path.normpath("C:/Program Files/VideoLAN/VLC/vlc.exe"), folder])

			def ddlFromUrl(id):
				def callback(var, id):
					url = var.get()
					self.downloadFile(id, url=url)
				self.textPopupWindow(
					self.optionsWindow,
					"Enter torrent url",
					lambda var,
					id=id: callback(
						var,
						id),
					fentype="TEXT")

			def tag(id, tag):
				with self.database.get_lock():
					self.database.set({'id': id, 'tag': tag},
									  table='anime', get_output=False)

				for lbl in self.animeList.winfo_children():
					if lbl.winfo_class() == 'Label' and lbl.name == str(id):
						lbl.configure(fg=self.colors[self.tagcolors[tag]])
						break
				self.reload(id, False)

			def trailer(id):
				trailer = anime.trailer
				if trailer is not None:
					self.log('MAIN_STATE', "Watching trailer for anime",
							 anime.title, "url", trailer)
					self.player((trailer,), 0, url=True)

			def switch(id, titles=None):
				if titles is not None:
					id = titles[id]
				self.optionsWindow.clear()
				self.drawOptionsWindow(id)

			def dataUpdate(id):
				data = self.api.anime(id)

				if 'status' in data.keys() and data.status != 'UPDATE':
					self.optionsWindow.after(10, self.reload, id)

		# Window init - Fancy corners - Main frame
		if True:
			anime = self.database(id=id, table="anime")

			if anime.status == 'UPDATE' or len(anime.keys()) == 0:
				threading.Thread(target=dataUpdate, args=(
					id,)).start()

			if len(anime.keys()) == 0:
				anime.title = "Loading..."

			if self.optionsWindow is None or not self.optionsWindow.winfo_exists():
				size = (self.infoWindowMinWidth, self.infoWindowMinHeight)
				self.optionsWindow = utils.RoundTopLevel(
					self.fen,
					title=anime.title,
					minsize=size,
					bg=self.colors['Gray2'],
					fg=self.colors['Gray3'])
				self.optionsWindow.titleLbl.configure(
					# fg=self.colors[self.tagcolors[self.database(
					#     id=id, table='anime').tag]]
					fg=self.colors[self.tagcolors[anime.tag]]
				)
			else:
				self.optionsWindow.clear()
				self.optionsWindow.titleLbl.configure(
					text=anime.title,
					bg=self.colors['Gray2'],
					fg=self.colors[self.tagcolors[anime.tag]],
					font=("Source Code Pro Medium", 18)
				)

		# Title - File buttons
		if True:
			titleFrame = Frame(self.optionsWindow, bg=self.colors['Gray2'])

			if self.animeHashes.get(id):
				offRow = 1
				bar = Progressbar(
					titleFrame, orient=HORIZONTAL, mode='determinate')
				bar.grid(row=0, column=0, columnspan=2,
						 sticky="nsew", padx=2, pady=2)
				text = Label(
					titleFrame,
					text="0%",
					bg=self.colors['Gray2'],
					fg=self.colors['Gray4'],
					font=(
						"Source Code Pro Medium",
						15))
				text.grid(row=0, column=2, padx=10)

				updateLoadingBar(id, bar, text)
			else:
				offRow = 0
			b = Button(
				titleFrame,
				text="Download torrents",
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
				command=lambda id=id: self.drawDdlWindow(id))
			b.bind("<Button-3>", lambda e, id=id: ddlFromUrl(id))
			b.grid(row=1 + offRow, column=0, sticky="nsew", padx=2, pady=2)

			Button(
				titleFrame,
				text="Manage torrents",
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
				command=lambda id=id: self.torrentFilesWindow(id)
			).grid(
				row=1 + offRow,
				column=1,
				sticky="nsew",
				padx=2,
				pady=2)

			offCol = 0
			folder = self.getFolder(id)
			showFolderButtons = folder is not None and os.path.isdir(
				os.path.join(self.animePath, folder))
			if showFolderButtons:
				command = (
					'explorer '
					'"{}"'.format(
						os.path.normpath(
							os.path.join(
								self.animePath,
								folder
					)))
				)
				Button(
					titleFrame,
					text="Open folder",
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
					command=lambda c=command: subprocess.run(c)
				).grid(
					row=2 + offRow,
					column=0,
					sticky="nsew",
					padx=2,
					pady=2)

				titles = []
				state = "normal"

				var = StringVar()
				var.set("Watch")
				epsList = utils.DropDownMenu(
					titleFrame,
					var,
					*titles,
					scrollbar=True,
					state=state,
					highlightthickness=0,
					borderwidth=0,
					font=(
						"Source Code Pro Medium",
						13),
					activebackground=self.colors['Gray3'],
					activeforeground=self.colors['White'],
					bg=self.colors['Gray3'],
					fg=self.colors['White']
				)
				epsList.menu.configure(
					bd=0,
					borderwidth=0,
					font=(
						"Source Code Pro Medium",
						13),
					activebackground=self.colors['Gray3'],
					activeforeground=self.colors['White'],
					bg=self.colors['Gray2'],
					fg=self.colors['White'],
					thickness=20,
					padx=20,
					sb_fg=self.colors['Gray3']
				)
				epsList.menu.root_configure(
					borderwidth=2,
					fg=self.colors['Gray3'],
					bg=self.colors['Gray2']
				)
				epsList.grid(row=2 + offRow, column=1,
							 sticky="nsew", padx=2, pady=2)
				epsList.var = var

				self.optionsWindow.after(10, lambda a=epsList, b=anime.title, c=folder: updateEpisodes(a, b, c))

			[titleFrame.grid_columnconfigure(i, weight=1) for i in range(2)]

			iconSize = (50, 50) if showFolderButtons else (30, 30)
			if bool(anime.like):
				image = self.getImage(
					os.path.join(
						self.iconPath,
						"heart.png"),
					iconSize)
			else:
				image = self.getImage(
					os.path.join(
						self.iconPath,
						"heart(1).png"),
					iconSize)
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
			likeButton.configure(command=lambda id=id,
								 b=likeButton: like(id, b))
			likeButton.image = image
			likeButton.grid(row=1 + offRow, column=2,
							rowspan=2, sticky="nsew", padx=5)
			titleFrame.grid(row=0, column=0, sticky="nsew")

		# Tags
		if True:
			tags = Frame(self.optionsWindow, bg=self.colors['Gray2'])
			Label(
				tags,
				text="Tag as:",
				bg=self.colors['Gray2'],
				fg=self.colors['Gray4'],
				font=(
					"Source Code Pro Medium",
					15)).grid(
				row=0,
				column=0,
				pady=10)
			for i, data in enumerate(self.tag_options.items()):
				tag_txt, color, tag_filter = data[0], data[1]['color'], data[1]['filter']
				Button(
					tags,
					text=tag_txt,
					bd=0,
					height=1,
					relief='solid',
					font=(
						"Source Code Pro Medium",
						13),
					activebackground=self.colors['Gray2'],
					activeforeground=self.colors['Green'],
					bg=self.colors['Gray2'],
					fg=self.colors[color],
					command=lambda id=id, tag_filter=tag_filter: tag(
						id, tag_filter)
				).grid(
					row=0,
					column=1 + i,
					sticky="nsew",
					padx=5)

			if anime.trailer is not None:
				Label(
					tags,
					text="-",
					bg=self.colors['Gray2'],
					fg=self.colors['Gray4'],
					font=(
						"Source Code Pro Medium",
						13)).grid(
					row=0,
					column=i + 2,
					pady=5)
				Button(
					tags,
					text="Watch trailer",
					bd=0,
					height=1,
					relief='solid',
					font=(
						"Source Code Pro Medium",
						13),
					activebackground=self.colors['Gray2'],
					activeforeground=self.colors['White'],
					bg=self.colors['Gray2'],
					fg=self.colors['White'],
					command=lambda id=id: trailer(id)).grid(
					row=0,
					column=i + 3,
					sticky="nsew",
					padx=5)
			tags.grid(row=3, column=0)

		# Synopsis
		if True:
			if anime.synopsis not in ('', None):
				synopsis = Label(
					self.optionsWindow,
					text=anime.synopsis,
					wraplength=900,
					font=(
						"Source Code Pro Medium",
						10),
					bg=self.colors['Gray2'],
					fg=self.colors['White'])
			else:
				synopsis = Label(
					self.optionsWindow,
					text="No synopsis",
					wraplength=900,
					font=(
						"Source Code Pro Medium",
						10),
					bg=self.colors['Gray2'],
					fg=self.colors['White'])
			synopsis.grid(row=4, column=0)

		# Secondary infos
		if True:
			secondInfos = Frame(self.optionsWindow, bg=self.colors['Gray2'])
			if anime.episodes is not None:
				text = str(anime.episodes) + \
					" episode{}".format("s" if anime.episodes > 1 else "")
				episodes = Label(
					secondInfos,
					text=text,
					font=(
						"Source Code Pro Medium",
						10),
					bg=self.colors['Gray2'],
					fg=self.colors['White'])
			else:
				episodes = Label(
					secondInfos,
					text="No episodes",
					font=(
						"Source Code Pro Medium",
						10),
					bg=self.colors['Gray2'],
					fg=self.colors['White'])
			if anime.rating is not None and anime.rating != 'None':
				rating = Label(
					secondInfos,
					text="Rating: " + anime.rating,
					font=(
						"Source Code Pro Medium",
						10),
					bg=self.colors['Gray2'],
					fg=self.colors['White'])
			else:
				rating = Label(
					secondInfos,
					text="No rating",
					font=(
						"Source Code Pro Medium",
						10),
					bg=self.colors['Gray2'],
					fg=self.colors['White'])
			if anime.duration not in (None, 'None', 'Unknown'):
				text = "(" + str(anime.duration) + " min{})".format(
					" each" if anime.episodes is not None and anime.episodes > 1 else "")
				duration = Label(
					secondInfos,
					text=text,
					font=(
						"Source Code Pro Medium",
						10),
					bg=self.colors['Gray2'],
					fg=self.colors['White'])
			else:
				duration = Label(
					secondInfos,
					text="(Unknown duration)",
					font=(
						"Source Code Pro Medium",
						10),
					bg=self.colors['Gray2'],
					fg=self.colors['White'])

			rating.grid(row=0, column=0)
			Label(
				secondInfos,
				text="-",
				font=(
					"Source Code Pro Medium",
					10),
				bg=self.colors['Gray2'],
				fg=self.colors['White']).grid(
				row=0,
				column=1)
			episodes.grid(row=0, column=2)
			duration.grid(row=0, column=3)
			secondInfos.grid(row=5, column=0)

		# Genres
		if True:
			genresFrame = Frame(self.optionsWindow, bg=self.colors['Gray2'])
			genres = anime.genres

			all_genres = dict(self.database.sql(
				"SELECT id, name FROM genresIndex"))

			for genre_id in genres:
				txt = all_genres.get(genre_id)
				if txt is None or txt == "NONE":
					txt = "Unknown"
				Label(
					genresFrame,
					text=txt,
					bd=0,
					height=1,
					font=(
						"Source Code Pro Medium",
						13),
					bg=self.colors['Gray2'],
					fg=self.colors['Gray'],
				).pack(
					side="left")
				lbl = Label(
					genresFrame,
					text=" - ",
					bd=0,
					height=1,
					font=(
						"Source Code Pro Medium",
						13),
					bg=self.colors['Gray2'],
					fg=self.colors['Gray'],
				)
				lbl.pack(side="left")
			if len(genres) >= 1:
				lbl.pack_forget()
			genresFrame.grid(row=6, column=0, pady=10)

		# Relations
		if True:
			relationsFrame = Frame(self.optionsWindow, bg=self.colors['Gray2'])
			relations = self.get_relations(id, type='anime')
			column = 0
			relations = sorted(relations, key=itemgetter('name'))
			for relation in relations:
				rel_ids = relation['rel_id']
				sql = "SELECT title,id FROM anime WHERE id IN (" + ",".join(
					"?" * len(rel_ids)) + ");"
				# TODO - Only do a single call to db
				titles = dict(self.database.sql(sql, rel_ids))
				text = relation['name'].capitalize().replace("_", " ")
				if len(titles) == 1:
					Button(relationsFrame,
						   text=text,
						   bd=0,
						   height=1,
						   relief='solid',
						   font=("Source Code Pro Medium",
								 13),
						   activebackground=self.colors['Gray2'],
						   activeforeground=self.colors['Red'],
						   bg=self.colors['Gray2'],
						   fg=self.colors[self.tagcolors[self.database(
							   id=rel_ids[0], table='anime').tag]],
						   command=lambda ids=rel_ids: switch(ids[0])).grid(row=0,
																			column=column)
				elif len(titles) > 1:
					var = StringVar()
					var.set(text)
					# if len(titles) == 1:
					relList = OptionMenu(
						relationsFrame,
						var,
						*titles.keys(),
						command=lambda e,
						titles=titles: switch(
							e,
							titles))
					relList.configure(
						indicatoron=False,
						highlightthickness=0,
						borderwidth=0,
						font=(
							"Source Code Pro Medium",
							13),
						activebackground=self.colors['Gray2'],
						activeforeground=self.colors['White'],
						bg=self.colors['Gray2'],
						fg=self.colors['White'])
					relList["menu"].configure(
						bd=0,
						borderwidth=0,
						activeborderwidth=0,
						font=(
							"Source Code Pro Medium",
							13),
						activebackground=self.colors['Gray3'],
						activeforeground=self.colors['White'],
						bg=self.colors['Gray2'],
						fg=self.colors['White'],
					)
					relList.grid(row=0, column=column)

					for i, rel_id in enumerate(rel_ids):
						relList['menu'].entryconfig(
							i, foreground=self.colors[self.tagcolors[self.database(id=rel_id, table="anime").tag]])
				else:
					self.log("ERROR", "id:{}, rel_ids:{}, titles:{}".format(
						str(id), str(rel_ids), str(titles)))
					# raise Exception("ERROR - id:{}, rel_ids:{}, titles:{}".format(str(id),str(rel_ids),str(titles)))

				if len(titles) > 0:
					column += 1
					lbl = Label(
						relationsFrame,
						text="-",
						bd=0,
						height=1,
						font=(
							"Source Code Pro Medium",
							13),
						bg=self.colors['Gray2'],
						fg=self.colors['Gray'],
					)
					lbl.grid(row=0, column=column)
					column += 1

			if column > 0:
				lbl.grid_forget()

			relationsFrame.grid(row=7, column=0)

		# State
		if True:
			state = Frame(self.optionsWindow, bg=self.colors['Gray2'])
			datefrom, dateto = anime.date_from, anime.date_to
			if datefrom is not None:
				datefrom = datetime.utcfromtimestamp(datefrom)
			if dateto is not None:
				dateto = datetime.utcfromtimestamp(dateto)

			status = self.getStatus(anime)
			Label(
				state,
				text="Status:",
				bg=self.colors['Gray2'],
				fg=self.colors['Gray4'],
				font=(
					"Source Code Pro Medium",
					15)).grid(
				row=0,
				column=0,
				sticky="e")
			statusLbl = Label(state,
							  text=self.dateStates[status]['text'],
							  bg=self.colors['Gray2'],
							  fg=self.colors[self.dateStates[status]['color']],
							  font=("Source Code Pro Medium",
									13))
			statusLbl.grid(row=0, column=1, sticky="w")
			dateLbl = Label(state,
							text="",
							bg=self.colors['Gray2'],
							fg=self.colors[self.dateStates[status]['color']],
							font=("Source Code Pro Medium",
								  13))
			if status != 'UNKNOWN' and datefrom is not None:
				dateLbl['text'] = self.getDateText(
					datefrom, dateto, anime.broadcast, status)
				dateLbl.grid(row=1, column=0, columnspan=2)
			state.grid(row=8, column=0)

		# Actions
		if True:
			actions = Frame(self.optionsWindow, bg=self.colors['Gray2'])
			for i, data in enumerate(self.actionButtons):
				Button(actions,
					   text=data['text'],
					   bd=0,
					   height=1,
					   relief='solid',
					   font=("Source Code Pro Medium",
							 13),
					   activebackground=self.colors['Gray2'],
					   activeforeground=self.colors[data['color']],
					   bg=self.colors['Gray2'],
					   fg=self.colors[data['color']],
					   command=lambda c=data['command'],
					   id=id: c(id)).grid(row=0,
										  column=i * 2)
				if i < len(self.actionButtons) - 1:
					Label(
						actions,
						text="-",
						bd=0,
						height=1,
						font=(
							"Source Code Pro Medium",
							13),
						bg=self.colors['Gray2'],
						fg=self.colors['Gray'],
					).grid(
						row=0,
						column=i * 2 + 1)

			actions.grid(row=9, column=0)

		if id not in self.animeHashes:
			t = threading.Thread(target=findTorrent, args=(id,))
			t.start()

		self.optionsWindow.update_events()

	def copy_title(self, id):
		database = self.getDatabase()
		self.root.clipboard_clear()
		title = database(id=id, table="anime")['title']
		self.root.clipboard_append(title)

	def reload(self, id, update=True):
		def wait_for_thread(t, cb=None):
			if t.is_alive():
				self.optionsWindow.after(500, wait_for_thread, t, cb)
			elif cb:
				cb()
	
		def finish_reload():
			if self.closing or self.optionsWindow is None or not self.optionsWindow.winfo_exists():
				return

			self.optionsWindow.clear()
			self.drawOptionsWindow(id)

			self.log('TIME', "Reloading:".ljust(25),
							round(time.time() - self.reload_start, 2), "sec")

		if 'TIME' in self.logs:
			self.reload_start = time.time()

		thread_files = threading.Thread(
			target=self.regroupFiles, args=(True,))
		thread_files.start()

		waiter = lambda thread_files=thread_files: wait_for_thread(thread_files, finish_reload)

		if update:
			thread_data = threading.Thread(
				target=self.api.anime, args=(id,))
			thread_data.start()

			old_waiter = waiter
			waiter = lambda thread_data=thread_data: wait_for_thread(thread_data, old_waiter)

		waiter()

	def deleteFiles(self, id):
		def clearFolder(path):
			self.log("DB_UPDATE", "Cleaning up folder:", path)
			try:
				# rd /S /Q "\\?\D:\Animes\folder."
				os.system('del /F /S /Q "{}"'.format(path))
			except Exception as e:
				self.log('DISK_ERROR', "Error while removing folder", path, e)
				raise
			c = 0
			while len(os.listdir(path)) != 0 and c < 10:
				time.sleep(1)
				c += 1
			if len(os.listdir(path)) == 0:
				os.rmdir(path)
				self.log("DB_UPDATE", "Deleted all files and removed folder")
			else:
				self.log("DISK_ERROR",
						 "Some files haven't been removed from folder", path)

		folder = self.getFolder(id)
		path = os.path.join(
			self.animePath,
			folder) if folder is not None else ""

		if os.path.exists(path):
			anime = self.database(id=id, table="anime")
			torrents = anime.torrents

			if self.getQB() == "OK":
				hashes = [self.getTorrentHash(os.path.join(
					self.torrentPath, torrent)) for torrent in torrents]

				self.log('DB_UPDATE', "Deleting", path, "-",
						 len(hashes), "torrents to remove")

				self.qb.torrents_delete(
					delete_files=True,
					torrent_hashes=hashes)

			threading.Timer(1, clearFolder, (path,)).start()
		else:
			self.log("DISK_ERROR", "Folder path doesn't exist:", path)

		with self.database.get_lock():
			self.database.set({'id': id, 'tag': "SEEN"},
							  table='anime', get_output=False)

		for lbl in self.animeList.winfo_children():
			if lbl.winfo_class() == 'Label' and lbl.name == str(id):
				lbl.configure(fg=self.colors[self.tagcolors["SEEN"]])
				break
		self.reload(id, False)

	def delete(self, id):
		self.log('DB_UPDATE', f"Deleted {self.database(id=id, table='anime').get('title')}")
		self.animeList.remove(id=id)
		self.database.remove(None, id=id, table="anime")
		self.optionsWindow.exit()

	def deleteSeenEpisodes(self, id):
		folder = self.getFolder(id)
		path = os.path.join(
			self.animePath,
			folder) if folder is not None else ""

		if os.path.exists(path):
			toDelete = []
			anime = self.database(id=id, table="anime")
			last_seen = os.path.normpath(anime.last_seen)

			eps = self.getEpisodes(folder)
			if len(eps) >= 1 and list(eps)[0] is not None:
				pathList = {os.path.normpath(e['path']): e for e in eps}
			else:
				pathList = []
			if last_seen is not None and last_seen in pathList.keys():
				for p, e in pathList.items():
					if p == os.path.normpath(last_seen):
						break
					toDelete.append(p)

			torrents = anime.torrents

			if self.getQB() == "OK":
				hashes = [self.getTorrentHash(os.path.join(
					self.torrentPath, torrent)) for torrent in torrents]
				hashesToDelete = []

				for t_hash in hashes:
					try:
						root = self.qb.torrents_properties(t_hash).save_path
					except qbittorrentapi.exceptions.NotFound404Error:
						continue

					for f in self.qb.torrents_files(t_hash):
						sub_p = os.path.normpath(os.path.join(path, f.name))
						if sub_p in toDelete:
							hashesToDelete.append(t_hash)
							break

				if len(toDelete) > 0:
					self.log('DB_UPDATE', "Deleting", len(toDelete), "files from", path, "-",
							 len(hashesToDelete), "torrents to remove")

					self.qb.torrents_delete(
						torrent_hashes=hashes)

					cmd = 'del /F /Q "{}"'.format('" "'.join(toDelete))
					try:
						os.system(cmd)
					except Exception:
						self.log('DISK_ERROR',
								 "Error while removing folder", path)
						raise
				else:
					self.log('DB_UPDATE', "No file to delete!")
			else:
				self.log("MAIN_STATE", "qBittorrent API not found!")
				return
		else:
			self.log("DISK_ERROR", "Folder path doesn't exist:", path)
		self.log("DB_UPDATE", "Deleted all files")
		self.reload(id, False)

	def getDateText(self, datefrom, dateto, broadcast, status):
		tz = timezone.utc
		today = datetime.now(tz)
		delta = today - datefrom.astimezone(tz)  # - timedelta(days=1)
		if status == 'FINISHED':
			if dateto is None:
				datetext = "Published on {}".format(
					datefrom.strftime("%d %b %Y"))
			else:
				datetext = "From {} to {} ({} days)".format(
					datefrom.strftime("%d %b %Y"), dateto.strftime("%d %b %Y"), delta.days)
		elif status == 'AIRING':
			datetext = "Since {} ({} days)".format(
				datefrom.strftime("%d %b %Y"), delta.days)
			if broadcast is not None:
				weekday, hour, minute = map(int, broadcast.split("-"))

				daysLeft = (weekday - today.weekday()) % 7
				dateObj = datetime.today() + timedelta(days=daysLeft)

				# Depends on timezone - TODO
				hourDateObj = timedelta(hours=hour - 5, minutes=minute)
				dateObj = datetime.combine(
					dateObj.date(), datetime_time.min) + hourDateObj
				text = dateObj.strftime(
					"Next episode on %a %d at %H:%M")
				datetext += "\n{}".format(text)

				daysSince = (today.weekday() - weekday) % 7
				text = "Last episode: {}"
				if daysSince == 0:
					text = text.format("Today")
				elif daysSince == 1:
					text = text.format("Yesterday")
				elif daysSince > 1:
					text = text.format(str(daysSince) + " days ago")
				else:
					text = text.format("uhh?")
				datetext += "\n{}".format(text)
			else:
				daysSince = ((delta.days - 1) % 7)
				dateObj = date.today() - timedelta(days=daysSince)
				text = dateObj.strftime("Last episode on %a %d ({})")
				if daysSince == 0:
					text = text.format("Today")
				elif daysSince == 1:
					text = text.format("Yesterday")
				elif daysSince > 1:
					text = text.format(str(daysSince) + " days ago")
				else:
					text = text.format("uhh?")
				datetext += "\n" + text

		elif status == 'UPCOMING':
			datetext = "On {} ({} days left)".format(
				datefrom.strftime("%d %b %Y"), -delta.days)
		else:
			datetext = ''

		return datetext
