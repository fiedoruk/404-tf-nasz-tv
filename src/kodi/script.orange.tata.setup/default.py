"""Run once inside Kodi: default install, or RunScript(addon.id,rollback)."""

import sys
from pathlib import Path

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from setup_keymap import SetupError, run, write_json


def main():
    addon = xbmcaddon.Addon()
    profile = Path(xbmcvfs.translatePath(addon.getAddonInfo("profile")))
    args = sys.argv[1:]
    if not args:
        choice = xbmcgui.Dialog().select('Nasz TV — konfiguracja', [
            'Zainstaluj mapę pilota', 'Utwórz M3U i EPG z własnego konta Orange',
            'Cofnij GUI (najpierw)', 'Cofnij mapę pilota (potem)'])
        if choice < 0: return
        if choice == 1:
            xbmc.executebuiltin('RunPlugin(plugin://plugin.video.orange_go/?mode=exportTataPvr)')
            return
        if choice == 2:
            xbmc.executebuiltin('RunScript(script.nasztv.gui,rollback)')
            return
        args = ['install' if choice == 0 else 'rollback']
    action = args[0] if len(args) == 1 else "install" if not args else None
    try:
        report = run(action, xbmcvfs.translatePath("special://profile/keymaps/"), profile)
        xbmc.executebuiltin("Action(reloadkeymaps)")
        report["reload_requested"] = True
        write_json(profile / "last-report.json", report)
    except (SetupError, OSError) as exc:
        xbmc.log("[script.orange.tata.setup] " + str(exc), xbmc.LOGERROR)
        xbmcgui.Dialog().notification("Pilot TV", "Nie ukończono operacji. Sprawdź dziennik Kodi.", xbmcgui.NOTIFICATION_ERROR)
        return
    message = "Mapa pilota zapisana." if action == "install" else "Przywrócono poprzednią mapę."
    xbmc.log("[script.orange.tata.setup] " + action + ": " + report["status"], xbmc.LOGINFO)
    xbmcgui.Dialog().notification("Pilot TV", message, xbmcgui.NOTIFICATION_INFO)


if __name__ == "__main__":
    main()
