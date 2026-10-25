"""Exclusive membership-only backup for a separately approved repair call."""
import json
import os
from pathlib import Path
import stat
from prune_memberships import MEMBER_COLUMNS, Refused


def exclusive_backup(path, group_id):
    """Return a callback. Parent must already exist; no overwrite, chmod or mkdir."""
    path = Path(path)
    if type(group_id) is not int or not 0 < group_id <= 2147483647:
        raise Refused('backup_group_unknown')
    if not path.is_absolute() or path.name in ('', '.', '..'):
        raise Refused('backup_path')

    def save(columns, rows):
        if (tuple(columns) != MEMBER_COLUMNS or not rows or len(rows) > 1000
                or any(len(row) != 7 or any(type(value) is not int for value in row)
                       or row[1] != group_id or row[0] <= 0 for row in rows)):
            raise Refused('backup_payload')
        payload = json.dumps({'schema': 1, 'columns': list(columns),
                              'deleted_rows': [list(row) for row in rows]},
                             separators=(',', ':')).encode('utf-8') + b'\n'
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            parent = os.fstat(directory)
            if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid()
                    or stat.S_IMODE(parent.st_mode) != 0o700):
                raise Refused('backup_parent_unknown')
            fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=directory)
            with os.fdopen(fd, 'wb') as handle:
                info = os.fstat(handle.fileno())
                if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
                    raise Refused('backup_mode')
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
                current = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                    raise Refused('backup_replaced')
            os.fsync(directory)
            return True
        finally:
            os.close(directory)
        # On failure preserve the file as evidence. Never unlink/reuse an uncertain backup.

    return save
