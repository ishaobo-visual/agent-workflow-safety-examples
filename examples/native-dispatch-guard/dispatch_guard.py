"""Serialize cooperative native dispatch without treating timeout as completion.

Unix only. Use a shared local directory controlled by trusted processes.
"""
import fcntl
import hashlib
import json
import os
import re
import uuid
from contextlib import contextmanager
from pathlib import Path


class Busy(RuntimeError):
    """A controller or an unresolved native attempt still owns the resource."""


class AlreadyAttempted(RuntimeError):
    """This request identifier has already been claimed."""


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(path, value):
    path = Path(path)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def completion_payload(attempt):
    """The trusted native wrapper writes this only after its work has exited."""
    return {"attempt_id": attempt["attempt_id"],
            "request_sha256": attempt["request_sha256"], "native_finished": True}


def write_completion(attempt):
    """For trusted wrappers/simulations, never to release a timed-out controller."""
    _write(attempt["completion_path"], completion_payload(attempt))


class Guard:
    def __init__(self, directory):
        self.directory = Path(directory).absolute()
        self.current = self.directory / "current.json"

    @contextmanager
    def _lock(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / "dispatch.lock").open("a+") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise Busy("Another controller holds the dispatch lock") from None
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @staticmethod
    def _completed(state):
        try:
            return _read(state["completion_path"]) == completion_payload(state)
        except (OSError, ValueError, KeyError):
            return False

    def status(self):
        """Read without creating files or releasing a claim."""
        state = _read(self.current) if self.current.exists() else {"state": "idle"}
        if state["state"] in ("running", "outcome_unknown"):
            state["native_finished_observed"] = self._completed(state)
        return state

    def reconcile(self):
        """Observe the matching completion marker; never dispatch work."""
        with self._lock():
            state = self.status()
            if state["state"] in ("running", "outcome_unknown"):
                if not self._completed(state):
                    raise Busy("The native outcome is unresolved")
                state.pop("native_finished_observed", None)
                state["state"] = "native_finished"
                _write(self.current, state)
            return state

    def dispatch(self, request_id, request_bytes, runner):
        """Claim once, then invoke runner(attempt) exactly once in this call.

        request_bytes must describe all immutable inputs. The runner owns its
        timeout policy; a timeout/exception never proves native completion.
        This is not a distributed exactly-once execution guarantee.
        """
        if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", request_id):
            raise ValueError("Use a short alphanumeric request identifier")
        if not isinstance(request_bytes, bytes) or not callable(runner):
            raise TypeError("Expected request bytes and a callable runner")
        with self._lock():
            previous = self.status()
            if previous["state"] in ("running", "outcome_unknown") and not self._completed(previous):
                raise Busy("Resolve the original native attempt before dispatch")
            job = self.directory / "requests" / request_id
            job.parent.mkdir(exist_ok=True)
            try:
                job.mkdir()
            except FileExistsError:
                raise AlreadyAttempted(request_id) from None
            attempt = {"state": "running", "request_id": request_id,
                       "attempt_id": uuid.uuid4().hex,
                       "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
                       "completion_path": str(job / "native-finished.json")}
            _write(job / "claim.json", attempt)
            _write(self.current, attempt)
            try:
                return runner(dict(attempt))
            finally:
                attempt["state"] = "native_finished" if self._completed(attempt) else "outcome_unknown"
                _write(self.current, attempt)
