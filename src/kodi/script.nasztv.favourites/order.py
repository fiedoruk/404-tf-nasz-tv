"""Argument-free entry for a native Kodi Favourites script shortcut."""
import sys
import xbmc
import xbmcgui

_previous_bytecode = sys.dont_write_bytecode
try:
    sys.dont_write_bytecode = True
    from favourites_editor import Editor
finally:
    sys.dont_write_bytecode = _previous_bytecode


if __name__ == '__main__':
    if len(sys.argv) == 1:
        Editor(xbmc, xbmcgui, xbmc.Monitor()).run('order')
