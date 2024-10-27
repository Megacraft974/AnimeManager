DELIMITER //

DROP PROCEDURE IF EXISTS get_torrent_data//
CREATE PROCEDURE get_torrent_data(IN t_hash INT)
BEGIN
	SELECT name, trackers FROM torrents WHERE hash = t_hash LIMIT 1;
END //

DROP PROCEDURE IF EXISTS get_anime_data//
CREATE PROCEDURE get_anime_data(IN a_id INT)
BEGIN
	SELECT * FROM animes WHERE id = a_id LIMIT 1;
END //

DROP PROCEDURE IF EXISTS get_pictures//
CREATE PROCEDURE get_pictures(IN id_list VARCHAR(255))
BEGIN
	SET @query = CONCAT('SELECT id, url, size FROM pictures WHERE id IN (', id_list, ')');
	PREPARE stmt FROM @query;
	EXECUTE stmt;
	DEALLOCATE PREPARE stmt;
END //

DROP PROCEDURE IF EXISTS anime_exists//
CREATE PROCEDURE anime_exists(IN a_id INT, OUT result INT)
BEGIN
	-- Return the count of records with the given name
	SELECT COUNT(*) INTO result FROM animes WHERE id = a_id;
END //


DROP PROCEDURE IF EXISTS save_anime//
CREATE PROCEDURE save_anime(IN a_id INT, IN a_data JSON)
BEGIN
	IF (SELECT COUNT(*) FROM animes WHERE id = a_id) > 0 THEN
		-- If an entry exists, update the existing record
		SET @update_values = (SELECT GROUP_CONCAT(
			CONCAT_WS(
				'=', 
				JSON_UNQUOTE(JSON_EXTRACT(a_data, CONCAT('$.', column_name))), 
				column_name
			)
			SEPARATOR ', ')
			FROM information_schema.columns 
			WHERE table_name = 'anime' AND column_name != 'id');

		SET @update_query = CONCAT('UPDATE anime SET ', @update_values, ' WHERE id = ', a_id);

		PREPARE stmt FROM @update_query;
		EXECUTE stmt;
		DEALLOCATE PREPARE stmt;
	ELSE
		-- If no entry exists, insert a new record
		SET @insert_columns = (SELECT GROUP_CONCAT(column_name) 
			FROM information_schema.columns 
			WHERE table_name = 'animes' AND column_name != 'id');
		
		SET @insert_values = (SELECT GROUP_CONCAT(JSON_UNQUOTE(JSON_EXTRACT(a_data, CONCAT('$.', column_name))) SEPARATOR ', ')
			FROM information_schema.columns 
			WHERE table_name = 'animes' AND column_name != 'id');
		
		SET @insert_query = CONCAT('INSERT INTO animes (id, ', @insert_columns, ') VALUES (', a_id, ', ', @insert_values, ')');
		
		PREPARE stmt FROM @insert_query;
		EXECUTE stmt;
		DEALLOCATE PREPARE stmt;
	END IF;
END //

DROP PROCEDURE IF EXISTS get_anime_id_from_api_id//
CREATE PROCEDURE get_anime_id_from_api_id(IN a_api_key VARCHAR(255), IN a_api_id INT)
BEGIN
	SET @query = CONCAT('SELECT id FROM indexList WHERE ', a_api_key, ' = ', a_api_id, ' LIMIT 1');
	PREPARE stmt FROM @query;
	EXECUTE stmt;
	DEALLOCATE PREPARE stmt;
END //

DROP PROCEDURE IF EXISTS get_broadcast//
CREATE PROCEDURE get_broadcast(IN a_id INT)
BEGIN
	SELECT weekday, hour, minute FROM broadcasts WHERE id=a_id LIMIT 1;
END //

DROP PROCEDURE IF EXISTS save_broadcast//
CREATE PROCEDURE save_broadcast(IN a_id INT, IN b_weekday INT, IN b_hour INT, IN b_minute INT)
BEGIN
	DECLARE existing_count INT;
	
	-- Check if the entry exists
	SELECT COUNT(*) INTO existing_count FROM broadcasts WHERE id = a_id;
	
	IF existing_count = 0 THEN
		-- Entry does not exist, insert new record
		INSERT INTO broadcasts(id, weekday, hour, minute) VALUES (a_id, b_weekday, b_hour, b_minute);
	ELSE
		-- Entry exists, update the record if values are different
		UPDATE broadcasts 
		SET weekday = b_weekday, hour = b_hour, minute = b_minute 
		WHERE id = a_id AND (weekday != b_weekday OR hour != b_hour OR minute != b_minute);
	END IF;
END //

DELIMITER ;