from .mySql import MySQL
from .dbManager import thread_safe_db

databases = {
    'MySQL': MySQL,
	'SQLite': thread_safe_db
}