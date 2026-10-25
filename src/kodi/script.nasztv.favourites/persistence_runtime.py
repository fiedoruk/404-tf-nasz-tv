"""Guarded membership persistence after native save; caller owns target authorization."""
import sys
import uuid


def persist_after_save(desired_ids, read_memory, origin_is_favourites, profile):
    old = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        import sqlite3
        import xbmc
        from durable_backup import exclusive_backup
        from prune_memberships import prune_stale_memberships, MEMBER_COLUMNS, Refused
        from portable_profile import resolve_runtime_profile
    finally:
        sys.dont_write_bytecode = old
    wanted = tuple(sorted(desired_ids))
    if tuple(sorted(read_memory())) != wanted:
        raise Refused('memory_changed_after_save')
    fresh = resolve_runtime_profile(xbmc)
    if fresh != profile:
        raise Refused('profile_changed_after_save')
    parent, database = profile.backup_dir, profile.database
    if database.is_symlink() or not database.is_file():
        raise Refused('database_missing_or_symlink')
    backup = parent / ('membership-%d-' % profile.group_id + uuid.uuid4().hex + '.json')
    connection = sqlite3.connect(database.resolve().as_uri()+'?mode=rw', uri=True, timeout=0.25)
    try:
        # Only the explicit Kodi21/schema46 DELETE-journal contract, without changing it.
        if connection.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
            raise Refused('journal_mode_changed')
        rows = tuple(connection.execute('SELECT '+','.join(MEMBER_COLUMNS)+
                     ' FROM map_channelgroups_channels WHERE idGroup=? ORDER BY idChannel', (profile.group_id,)))
        if tuple(sorted(read_memory())) != wanted:
            raise Refused('memory_changed_before_transaction')
        # Preserve the UI guard's original group scope with a fresh playing ID.
        playing_id = read_memory(playing=True)
        return prune_stale_memberships(connection, wanted, rows, playing_id=playing_id,
            origin_is_favourites=origin_is_favourites, backup_rows=exclusive_backup(backup, profile.group_id),
            group_identity=profile.identity)
    finally:
        connection.close()
