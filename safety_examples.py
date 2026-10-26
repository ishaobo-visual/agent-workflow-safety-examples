"""Small educational reference mechanisms; no network or platform integrations."""
import hashlib
import sqlite3
from pathlib import Path


class Blocked(Exception):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def route(business_id, catalog):
    row = catalog.get(business_id)
    if row is None or not row['enabled']:
        raise Blocked('unknown or disabled route')
    return row['line']


def check_receipt(receipt, task, executor, revision):
    if receipt != {'task': task, 'executor': executor, 'revision': revision}:
        raise Blocked('receipt does not match current context')


class ActionLedger:
    """Persistent single-process demo; not a distributed workflow service."""
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS actions (id TEXT PRIMARY KEY, state TEXT NOT NULL)')
        self.db.commit()

    def close(self):
        self.db.close()

    def execute(self, action_id, read_state, expected_revision, transport, before_send=None):
        def check():
            state = read_state()
            if state['status'] != 'ACTIVE' or state['revision'] != expected_revision:
                raise Blocked('inactive or changed state')
        check()
        try:
            with self.db:
                self.db.execute('INSERT INTO actions VALUES (?, ?)', (action_id, 'INTENT'))
        except sqlite3.IntegrityError as exc:
            raise Blocked('existing action requires reconciliation; never replay') from exc
        try:
            if before_send:
                before_send()
            check()
            result = transport()
        except Exception:
            with self.db:
                self.db.execute('UPDATE actions SET state=? WHERE id=?', ('UNKNOWN', action_id))
            raise
        with self.db:
            self.db.execute('UPDATE actions SET state=? WHERE id=?', ('RETURNED_UNVERIFIED', action_id))
        return result


def plain_file(root, path):
    root, path = Path(root).absolute(), Path(path).absolute()
    if not path.is_relative_to(root) or '..' in path.parts:
        raise Blocked('outside fixture root')
    for node in (path, *path.parents):
        if node.is_symlink() or getattr(node, 'is_junction', lambda: False)():
            raise Blocked('linked path')
    if not path.is_file() or path.stat().st_nlink != 1:
        raise Blocked('not an ordinary single-link file')
    return path


def revise_one(root, selected, authorized, payload, frozen):
    """Only a synthetic whole-file edit. Does not claim pixel-level repair."""
    root = Path(root)
    if selected != authorized or selected in frozen:
        raise Blocked('outside authorized revision')
    target = plain_file(root, root / selected)
    for name, expected in frozen.items():
        if digest(plain_file(root, root / name)) != expected:
            raise Blocked('frozen file changed')
    target.write_bytes(payload)
    for name, expected in frozen.items():
        if digest(root / name) != expected:
            raise Blocked('frozen file changed after edit')


def quarantine(root, relative_paths, protected):
    """Move only cache files; preflight whole plan; never permanently delete."""
    root = Path(root)
    if not relative_paths or len(set(relative_paths)) != len(relative_paths):
        raise Blocked('empty or duplicate plan')
    prepared = []
    for name in relative_paths:
        rel = Path(name)
        if name in protected or rel.is_absolute() or '..' in rel.parts or rel.parts[0] != 'cache':
            raise Blocked('protected or outside cache')
        p = plain_file(root, root / rel)
        prepared.append((rel, p, digest(p)))
    output = root / 'quarantine'
    if output.exists():
        raise Blocked('existing output; reconcile instead of replay')
    output.mkdir()
    moved = []
    for rel, source, expected in prepared:
        target = output / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        if digest(target) != expected:
            raise Blocked('readback failed')
        moved.append(target)
    return moved
