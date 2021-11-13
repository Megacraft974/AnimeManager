autopep8 "D:\Anime Manager" --recursive --in-place --pep8-passes 2000 -a
python -m pycodestyle "D:\Anime Manager" --ignore=E501
python -m pycodestyle --statistics -qq "D:\Anime Manager"
PAUSE