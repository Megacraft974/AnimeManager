import multiprocessing
from . import animeManager

if __name__ == '__main__':
	multiprocessing.freeze_support()
	p = multiprocessing.current_process()
	if p.name == 'MainProcess':
		m = animeManager.Manager()
