import multiprocessing
import sys, os
sys.path.append(os.path.abspath('../'))

test = True
if __name__ == "__main__":
	if test is False:
		import AnimeManager
		AnimeManager.Manager()
	else:
		from AnimeManager import test