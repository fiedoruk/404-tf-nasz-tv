"""One owned keymap; no Kodi imports, networking, or other profile edits."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

OWNER = "script.orange.tata.setup"
TARGET = "zz-orange-tata.xml"
MARKER = "<!-- Managed by script.orange.tata.setup; schema=1 -->"
KEYMAP = ('''<?xml version="1.0" encoding="UTF-8"?>
%s
<keymap>
  <FullscreenLiveTV>
    <keyboard>
      <up>ChannelUp</up>
      <down>ChannelDown</down>
      <return>ActivateWindow(PVROSDChannels)</return>
      <left>OSD</left>
      <right>Info</right>
    </keyboard>
    <remote>
      <up>ChannelUp</up>
      <down>ChannelDown</down>
      <select>ActivateWindow(PVROSDChannels)</select>
      <left>OSD</left>
      <right>Info</right>
    </remote>
  </FullscreenLiveTV>
</keymap>
''' % MARKER).encode("utf-8")


class SetupError(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def read_file(path):
    if path.is_symlink():
        raise SetupError("Refusing a symbolic link: " + path.name)
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > 65536:
        raise SetupError("Unexpected file type or size: " + path.name)
    return path.read_bytes()


def validate_keymap(data):
    """Require our ownership marker and the exact limited mapping, not just XML."""
    try:
        root = ET.fromstring(data)
        expected = ET.fromstring(KEYMAP)
        def shape(node):
            return (node.tag, node.attrib, (node.text or "").strip(),
                    [shape(child) for child in node])
        if MARKER.encode() not in data or shape(root) != shape(expected):
            raise SetupError("Existing keymap is not this add-on's mapping")
    except ET.ParseError as exc:
        raise SetupError("Invalid keymap XML") from exc


def atomic_write(path, data):
    if path.is_symlink():
        raise SetupError("Refusing a symbolic link: " + path.name)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, value):
    atomic_write(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def load_state(path):
    data = read_file(path)
    if data is None:
        return None
    try:
        state = json.loads(data)
        valid = (state["schema"] == 1 and state["owner"] == OWNER
                 and state["target"] == TARGET
                 and state["installed_sha256"] == digest(KEYMAP)
                 and type(state["before_exists"]) is bool
                 and state["status"] in ("prepared", "installed", "rolled_back")
                 and ((state["before_exists"] and isinstance(state["before_sha256"], str)
                       and len(state["before_sha256"]) == 64)
                      or (not state["before_exists"] and state["before_sha256"] is None)))
        if not valid:
            raise ValueError("invalid fields")
        return state
    except (ValueError, KeyError, TypeError) as exc:
        raise SetupError("Invalid installation state; nothing changed") from exc


def run(action, keymap_directory, profile_directory):
    if action not in ("install", "rollback"):
        raise SetupError("Expected install or rollback")
    keymaps, profile = Path(keymap_directory), Path(profile_directory)
    if keymaps.is_symlink() or profile.is_symlink():
        raise SetupError("Refusing a symbolic-link directory")
    keymaps.mkdir(parents=True, exist_ok=True)
    profile.mkdir(parents=True, exist_ok=True)
    lock = profile / "operation.lock"
    try:
        lock_fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise SetupError("Another operation or interrupted lock exists; inspect before retry") from exc
    try:
        os.close(lock_fd)
        target, state_path = keymaps / TARGET, profile / "state.json"
        backup = profile / "keymap-before.xml"
        before = read_file(target)
        state = load_state(state_path)
        if action == "install":
            validate_keymap(KEYMAP)
            if state and state["status"] in ("prepared", "installed"):
                if digest(before) not in (state["installed_sha256"], state["before_sha256"]):
                    raise SetupError("Managed file changed after setup; refusing overwrite")
                # Preserve the first baseline even when install is invoked repeatedly.
                if state["before_exists"] and digest(read_file(backup)) != state["before_sha256"]:
                    raise SetupError("Backup checksum mismatch; refusing overwrite")
            else:
                if before is not None:
                    validate_keymap(before)
                    atomic_write(backup, before)
                state = {"schema": 1, "owner": OWNER, "target": TARGET,
                         "before_exists": before is not None, "before_sha256": digest(before),
                         "installed_sha256": digest(KEYMAP), "status": "prepared"}
                write_json(state_path, state)
            if read_file(target) != before:
                raise SetupError("Target changed during setup; refusing overwrite")
            atomic_write(target, KEYMAP)
            if read_file(target) != KEYMAP:
                raise SetupError("Installed keymap readback mismatch")
            state["status"] = "installed"
        else:
            if state is None:
                raise SetupError("No installation record; target left untouched")
            prior = read_file(backup) if state["before_exists"] else None
            if digest(prior) != state["before_sha256"]:
                raise SetupError("Backup checksum mismatch; target left untouched")
            if before == prior:
                pass  # Also handles interruption after restore but before state update.
            elif digest(before) == state["installed_sha256"]:
                if read_file(target) != before:
                    raise SetupError("Target changed during rollback; refusing overwrite")
                if prior is None:
                    target.unlink()
                else:
                    atomic_write(target, prior)
            else:
                raise SetupError("Managed file changed after setup; rollback refused")
            if read_file(target) != prior:
                raise SetupError("Rollback readback mismatch")
            state["status"] = "rolled_back"
        write_json(state_path, state)
        report = {"schema": 1, "owner": OWNER, "action": action,
                  "target": TARGET, "status": state["status"],
                  "before_sha256": digest(before), "after_sha256": digest(read_file(target)),
                  "backup_exists": state["before_exists"], "reload_requested": False}
        write_json(profile / "last-report.json", report)
        return report
    finally:
        lock.unlink()
