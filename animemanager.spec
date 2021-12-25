# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

added_files = [
    ('animeAPI', 'animeAPI'),
    ('icons', 'icons'),
    ('lib', 'lib'),
    ('media_players', 'media_players'),
    ('search_engines', 'search_engines'),
    ('windows', 'windows'),
]

added_libs = ('certifi', 'jsonschema', 'mpv')
for name in added_libs:
    added_files += collect_data_files(name)

print("-- datas:\n", '\n--'.join(sorted(map(str, added_files))))

binaries = []
binaries += collect_dynamic_libs('ffpyplayer')

print("\n-- bins:\n", '\n--'.join(map(str, binaries)))

modules = ['lxml._elementpath', 'mobile_server', 'tkinter.ttk', 'tkinter.filedialog', 'pytube', 'jikanpy', 'jsonapi_client', 'vlc', 'mpv', 'ffpyplayer', 'ffpyplayer.player']
"""
    ('cert.pem','cert.pem'),
    ('key.pem','key.pem')
]"""

# excluded = ['_gtkagg', '_tkagg', 'bsddb', 'curses', 'pywin.debugger', 'pywin.debugger.dbgcon', 'pywin.dialogs', 'tcl', 'Tkconstants', 'Tkinter']

a = Analysis(['animemanager.py'],
             pathex=['D:\\Anime Manager'],
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
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)
