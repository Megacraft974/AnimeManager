call .\venv\Scripts\activate
python -m PyInstaller animemanager.spec --upx-dir lib\upx-3.96-win64
deactivate
pause