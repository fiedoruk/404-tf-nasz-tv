"""Finite UI helper with validated profile/persistence; no service, HTTP or player control."""
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
    if len(sys.argv) in (1, 2):
        command = sys.argv[1] if len(sys.argv) == 2 else 'edit'
        if len(sys.argv) == 1:
            choice = xbmcgui.Dialog().select('Ulubione — eksperymentalne', [
                'Edytuj listę (zapis do bazy Kodi)', 'Przygotuj integrację AZR', 'Cofnij integrację AZR'])
            command = ('edit', 'prepare', 'unprepare')[choice] if choice >= 0 else 'cancel'
        if command in ('prepare', 'unprepare'):
            from integration import main
            try: main(rollback=command == 'unprepare')
            except Exception as exc: xbmcgui.Dialog().ok('Ulubione — zatrzymano', str(exc))
        elif command != 'cancel':
            Editor(xbmc, xbmcgui, xbmc.Monitor()).run(command)
