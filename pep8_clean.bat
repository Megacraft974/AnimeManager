autopep8 "D:\Anime Manager" --recursive --in-place -a -a --ignore E501 -j 0 --exclude venv,__pycache__,build,dist,lib,.git
python -m pycodestyle "D:\Anime Manager" --ignore=E501 --exclude venv,__pycache__,build,dist,lib,.git
python -m pycodestyle --statistics --ignore=E501 -qq "D:\Anime Manager" --exclude venv,__pycache__,build,dist,lib,.git
PAUSE