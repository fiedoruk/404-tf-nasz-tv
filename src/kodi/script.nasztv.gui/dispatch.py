"""One-shot input handling. No network, loop, sleep or Kodi import on host."""
import os

MODE = "nasztv.hud.mode"
HELP = "nasztv.hud.help"
SUPPRESS = "nasztv.hud.suppress.channel"
PROPERTIES = (MODE, HELP, SUPPRESS)
WINDOW = "Custom_NaszTV.xml"


def serial_handle(command, home, api, profile):
    # Kodi RunScript instances are asynchronous. OS lock covers read-modify-write
    # and is released automatically even if the Python invocation terminates.
    import fcntl
    os.makedirs(profile, mode=0o700, exist_ok=True)
    with open(os.path.join(profile, "dispatch.lock"), "a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            handle(command, home, api)
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def reset(home):
    for name in PROPERTIES:
        home.clearProperty(name)


def handle(command, home, api):
    if command not in ("cycle", "help", "back", "up", "down", "reset", "list"):
        raise ValueError("Unknown dispatcher command")
    if command == "reset":
        reset(home)
        return
    if not api.getCondVisibility("PVR.IsPlayingTV"):
        reset(home)
        if command == "back":
            api.executebuiltin("Action(Back)")
        return
    raw = home.getProperty(MODE)
    mode = int(raw) if raw in ("1", "2") else 0
    help_open = home.getProperty(HELP) == "1"
    if command == "list":
        home.clearProperty(HELP)
        api.executebuiltin("ActivateWindow(PVROSDChannels)")
    elif command == "help":
        home.setProperty(HELP, "" if help_open else "1")
        if help_open:
            home.clearProperty(SUPPRESS)
    elif command == "cycle":
        home.clearProperty(HELP)
        mode = (mode + 1) % 3
        if (mode == 2 and home.getProperty("nasztv.details.status") in ("error", "empty")
                and home.getProperty("nasztv.details.busy") != "1"):
            markers = ("nasztv.details.request_channel_name", "nasztv.details.request_now_start",
                       "nasztv.details.request_next_start")
            if any(home.getProperty(key) for key in markers):
                # Invalidate the entire old request before making mode2 visible.
                # The details worker still owns cache/backoff and its independent flock.
                for key in markers:
                    home.clearProperty(key)
        home.setProperty(MODE, str(mode))
        if mode == 0:
            home.setProperty(SUPPRESS, api.getInfoLabel("VideoPlayer.ChannelNumberLabel") or "__unknown__")
        else:
            home.clearProperty(SUPPRESS)
    elif command in ("up", "down"):
        home.clearProperty(HELP)
        home.clearProperty(SUPPRESS)
        api.executebuiltin("Action(%s)" % ("ChannelUp" if command == "up" else "ChannelDown"))
    elif help_open:
        home.clearProperty(HELP)
        home.clearProperty(SUPPRESS)
    elif mode or api.getCondVisibility("Window.IsVisible(%s)" % WINDOW):
        home.setProperty(MODE, "0")
        home.setProperty(SUPPRESS, api.getInfoLabel("VideoPlayer.ChannelNumberLabel") or "__unknown__")
    else:
        # Direct GUI action, not a synthetic key press: does not re-enter keymap.
        api.executebuiltin("Action(Back)")
