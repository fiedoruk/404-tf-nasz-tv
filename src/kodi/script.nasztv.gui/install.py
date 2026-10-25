"""Three owned targets; exact baselines, atomic writes and resumable rollback."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET

OWNER = "script.nasztv.gui"
OLD_MAP_SHA = "26303e86b773e14d20238464af4e054277fb1af8201473cc808b7a22871809ca"
SEEK_SHA = "ae88943851c92b74bd1368091c15e636477e15eb75a2ab21116980b9859889b2"
OLD_MARKER = b"<!-- Managed by script.orange.tata.setup; schema=1 -->"
MARKER = b"<!-- Managed by script.nasztv.gui; schema=1 -->"
CUSTOM_ID = "1598"
NAMES = ("keymap", "custom", "seekbar", "details_helper")
KEYMAP = b'''<?xml version="1.0" encoding="UTF-8"?>
<!-- Managed by script.nasztv.gui; schema=1 -->
<keymap>
  <FullscreenLiveTV>
    <keyboard>
      <up>ChannelUp</up>
      <down>ChannelDown</down>
      <return>ActivateWindow(PVROSDChannels)</return>
      <left>RunPlugin(plugin://plugin.video.orange_go/?mode=nasztv&amp;action=help)</left>
      <right>RunPlugin(plugin://plugin.video.orange_go/?mode=nasztv&amp;action=cycle)</right>
      <backspace>RunPlugin(plugin://plugin.video.orange_go/?mode=nasztv&amp;action=back)</backspace>
      <browser_back>RunPlugin(plugin://plugin.video.orange_go/?mode=nasztv&amp;action=back)</browser_back>
      <escape>RunPlugin(plugin://plugin.video.orange_go/?mode=nasztv&amp;action=back)</escape>
    </keyboard>
    <remote>
      <up>ChannelUp</up>
      <down>ChannelDown</down>
      <select>ActivateWindow(PVROSDChannels)</select>
      <left>RunPlugin(plugin://plugin.video.orange_go/?mode=nasztv&amp;action=help)</left>
      <right>RunPlugin(plugin://plugin.video.orange_go/?mode=nasztv&amp;action=cycle)</right>
      <back>RunPlugin(plugin://plugin.video.orange_go/?mode=nasztv&amp;action=back)</back>
    </remote>
  </FullscreenLiveTV>
</keymap>
'''


class InstallError(RuntimeError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def read(path):
    if path.is_symlink() or path.parent.is_symlink():
        raise InstallError("Symlink target refused: " + path.name)
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > 2_000_000:
        raise InstallError("Unexpected target: " + path.name)
    return path.read_bytes()


def atomic(path, data):
    if path.is_symlink():
        raise InstallError("Symlink target refused")
    fd, name = tempfile.mkstemp(prefix=".nasztv-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_json(path, value):
    atomic(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def parse_xml(data):
    try:
        return ET.fromstring(data)
    except (ET.ParseError, TypeError) as exc:
        raise InstallError("Invalid XML; installation refused") from exc


def patch_seekbar(data):
    if sha(data) != SEEK_SHA:
        raise InstallError("Unknown AZR DialogSeekBar baseline")
    # Preserve all original bytes except marker and two visibility guards.
    patched, count = re.subn(rb"<visible>(.*?)</visible>",
                            rb"<visible>[\1] + !PVR.IsPlayingTV</visible>", data,
                            flags=re.S)
    if count != 2:
        raise InstallError("Unexpected DialogSeekBar visibility structure")
    patched = patched.replace(b'<window id="115">', b'<window id="115">\n    ' + MARKER, 1)
    parse_xml(patched)
    return patched


def validate_skin(skin):
    manifest = read(skin / "addon.xml")
    if manifest is None:
        raise InstallError("Skin manifest missing")
    root = parse_xml(manifest)
    if (root.get("id"), root.get("version")) != ("skin.arctic.zephyr.mod", "3.0.3"):
        raise InstallError("Only Arctic Zephyr Reloaded 3.0.3 is supported")


def run(command, keymaps, skin, profile, addon):
    if command not in ("install", "rollback"):
        raise InstallError("Unknown installer command")
    keymaps, skin, profile, addon = map(Path, (keymaps, skin, profile, addon))
    for directory in (keymaps, skin, skin / "1080i", profile):
        if directory.is_symlink():
            raise InstallError("Symlink directory refused")
    profile.mkdir(parents=True, exist_ok=True)
    lock = profile / "operation.lock"
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise InstallError("An operation or interrupted lock exists") from exc
    os.close(fd)
    try:
        validate_skin(skin)
        targets = {"keymap": keymaps / "zz-orange-tata.xml",
                   "custom": skin / "1080i" / "Custom_NaszTV.xml",
                   "seekbar": skin / "1080i" / "DialogSeekBar.xml",
                   "details_helper": skin / "1080i" / "Custom_NaszTVDetails.xml"}
        state_path = profile / "state.json"
        raw = read(state_path)
        state = json.loads(raw) if raw is not None else None
        current = {name: read(path) for name, path in targets.items()}
        if (state is not None and state.get("owner") == OWNER and state.get("schema") == 1
                and state.get("status") == "rolled_back"
                and set(state.get("files", {})) == {"keymap", "custom", "seekbar"}):
            if current["details_helper"] is not None:
                raise InstallError("Details helper already existed before migration")
            state["files"]["details_helper"] = {"before": None, "after": None}
        if state is not None:
            if (state.get("owner") != OWNER or state.get("schema") != 1
                    or state.get("status") not in ("prepared", "installed", "rolled_back")
                    or state.get("skin_path") != str(skin)
                    or set(state.get("files", {})) != set(NAMES)):
                raise InstallError("Invalid state record")
            baseline = {}
            for name in NAMES:
                record = state["files"][name]
                if set(record) != {"before", "after"}:
                    raise InstallError("Invalid file record")
                baseline[name] = read(profile / (name + ".before")) if record["before"] is not None else None
                if sha(baseline[name]) != record["before"]:
                    raise InstallError("Backup checksum mismatch: " + name)
                if sha(current[name]) not in (record["before"], record["after"]):
                    raise InstallError("Target changed outside this installer: " + name)
        else:
            if command == "rollback":
                raise InstallError("No installation record")
            baseline = current.copy()
        if command == "install":
            if sha(baseline["keymap"]) != OLD_MAP_SHA or OLD_MARKER not in (baseline["keymap"] or b""):
                raise InstallError("Expected exact script.orange.tata.setup 0.1.0 keymap")
            if baseline["custom"] is not None:
                raise InstallError("Custom_NaszTV.xml already existed before installation")
            if baseline["details_helper"] is not None:
                raise InstallError("Custom_NaszTVDetails.xml already existed before installation")
            for path in (skin / "1080i").glob("*.xml"):
                if path.name.lower().startswith("custom") and path.name not in ("Custom_NaszTV.xml", "Custom_NaszTVDetails.xml"):
                    candidate = parse_xml(read(path))
                    if candidate.get("id") in (CUSTOM_ID, "1599"):
                        raise InstallError("Custom window ID collision")
            custom = read(addon / "resources" / "Custom_NaszTV.xml")
            if custom is None or MARKER not in custom:
                raise InstallError("Own custom XML missing")
            root = parse_xml(custom)
            if root.get("id") != CUSTOM_ID or root.get("type") != "dialog" or root.find("visible") is None:
                raise InstallError("Invalid own window contract")
            helper = read(addon / "resources" / "Custom_NaszTVDetails.xml")
            if helper is None or MARKER not in helper:
                raise InstallError("Details helper missing")
            helper_root = ET.fromstring(helper)
            if helper_root.get("id") != "1599" or helper_root.get("type") != "dialog":
                raise InstallError("Invalid details helper")
            desired = {"keymap": KEYMAP, "custom": custom, "seekbar": patch_seekbar(baseline["seekbar"]),
                       "details_helper": helper}
            if state is not None and any(state["files"][n]["after"] != sha(desired[n]) for n in NAMES):
                if state["status"] != "rolled_back" or any(current[n] != baseline[n] for n in NAMES):
                    raise InstallError("Package differs from installed version; rollback first")
                # Qualified upgrade only after exact rollback. Keep the original backups.
                for name in NAMES:
                    state["files"][name]["after"] = sha(desired[name])
                state["status"] = "prepared"
                write_json(state_path, state)
            if state is None:
                for name in NAMES:
                    if baseline[name] is not None:
                        atomic(profile / (name + ".before"), baseline[name])
                state = {"schema": 1, "owner": OWNER, "skin_path": str(skin), "status": "prepared",
                         "files": {n: {"before": sha(baseline[n]), "after": sha(desired[n])} for n in NAMES}}
                write_json(state_path, state)
        else:
            desired = baseline
        # All guards and all backup checks complete before mutating a target.
        for name in NAMES:
            target = targets[name]
            if read(target) != current[name]:
                raise InstallError("Concurrent target change: " + name)
            if desired[name] is None:
                if target.exists():
                    target.unlink()
            elif current[name] != desired[name]:
                atomic(target, desired[name])
            if read(target) != desired[name]:
                raise InstallError("Readback failed: " + name)
        state["status"] = "installed" if command == "install" else "rolled_back"
        write_json(state_path, state)
        return {"owner": OWNER, "status": state["status"], "files": state["files"]}
    finally:
        lock.unlink()
