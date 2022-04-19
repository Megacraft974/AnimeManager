# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

added_files = [
    ('animeAPI/*.py', 'animeAPI'),
    ('icons/app_icon/icon.ico', 'icons/app_icon'),
    ('icons/*.*', 'icons'),
    ('lib/mpv-1.dll', 'lib'),
    ('media_players/*.py', 'media_players'),
    ('search_engines/*.py', 'search_engines'),
    ('windows/*.py', 'windows'),
]

for f in os.listdir('icons'):
    path = os.path.join('icons', f)
    if os.path.isfile(path):
        added_files.append((path, path))

for f in os.listdir('icons/app_icon'):
    path = os.path.join('icons/app_icon', f)
    if os.path.isdir(path) and f != "full_size":
        added_files.append((path, path))

added_libs = ('certifi', 'jsonschema', 'mpv', 'ffpyplayer')
for name in added_libs:
    added_files += collect_data_files(name)

print("-- datas:\n", '\n--'.join(sorted(map(str, added_files))))

binaries = []
bin_names = ('mpv', 'vlc')
for name in bin_names:
    binaries += collect_data_files(name)

print("\n-- bins:", '\n--'.join(map(str, binaries)))

modules = ['lxml._elementpath', 'thefuzz', 'bs4', 'mobile_server', 'tkinter.ttk', 'tkinter.filedialog', 'pytube', 'jikanpy', 'jsonapi_client', 'vlc', 'mpv', 'ffpyplayer.player', 'pypresence']

# excluded = ['_gtkagg', '_tkagg', 'bsddb', 'curses', 'pywin.debugger', 'pywin.debugger.dbgcon', 'pywin.dialogs', 'tcl', 'Tkconstants', 'Tkinter']

a = Analysis(['animemanager.py'],
             pathex=['E:\\Anime Manager'],
             binaries=binaries,
             datas=added_files,
             hiddenimports=modules,
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='animeManager',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          icon='icons/app_icon/icon.ico'
          )
