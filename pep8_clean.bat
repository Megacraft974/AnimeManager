autopep8 "E:\Anime Manager" --recursive --in-place -a -a --ignore E501 -j 0 --exclude venv,__pycache__,build,dist,lib,.git
python -m pycodestyle "E:\Anime Manager" --ignore=E501 --exclude venv,__pycache__,build,dist,lib,.git
python -m pycodestyle --statistics --ignore=E501 -qq "E:\Anime Manager" --exclude venv,__pycache__,build,dist,lib,.git
PAUSE