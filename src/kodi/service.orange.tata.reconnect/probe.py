"""Local IPv4 route selection only: no send, receive, DNS or HTTP."""

import errno
import ipaddress
import json
import socket


def route_snapshot():
    result = {"route_available": None, "local_addr_is_unspecified": None}
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.settimeout(0.5)
            probe.connect(("192.0.2.1", 9))
            address = ipaddress.ip_address(probe.getsockname()[0])
            result["local_addr_is_unspecified"] = address.is_unspecified
            result["route_available"] = not (address.is_unspecified or address.is_loopback)
    except OSError as exc:
        if exc.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ENETDOWN):
            result["route_available"] = False
    except ValueError:
        pass
    return result


def kodi_snapshot(xbmc):
    result = route_snapshot()
    try:
        address = ipaddress.ip_address(xbmc.getIPAddress())
        result["kodi_has_address"] = not (address.is_unspecified or address.is_loopback)
    except (ValueError, RuntimeError):
        result["kodi_has_address"] = None
    try:
        item = xbmc.Player().getPlayingItem()
        result["orangego.channel_id"] = item.getProperty("orangego.channel_id")
        result["orangego.is_live"] = item.getProperty("orangego.is_live")
        result["video_info_title"] = item.getVideoInfoTag().getTitle()
        result["label"] = item.getLabel()
        result["gui_video_title"] = xbmc.getInfoLabel("VideoPlayer.Title")
    except (RuntimeError, AttributeError):
        result["player_probe_unavailable"] = True
    result["meaning"] = "LOCAL_ROUTE_ONLY_NOT_INTERNET"
    return result


if __name__ == "__main__":
    import xbmc
    xbmc.log("[orange.tata.reconnect.probe] " + json.dumps(kodi_snapshot(xbmc)), xbmc.LOGINFO)
