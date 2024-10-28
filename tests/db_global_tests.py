class DbGlobalTests:
	def test_tables(self):
		tables = ["anime", "animeRelations", "broadcasts", "characters", "charactersIndex", "characterRelations", "genres", "genresIndex", "indexList", "pictures", "title_synonyms", "torrents", "torrentsIndex"]
		with self.db:
			for table in tables:
				try:
					data = self.db.sql(f"SELECT * FROM {table} LIMIT 1")
				except Exception as e:
					self.fail(f"Error while trying to access table {table}: {e}")
				else:
					self.assertIsNotNone(data, f"Table {table} seems to be empty")