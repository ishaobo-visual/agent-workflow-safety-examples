import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from dispatch_guard import AlreadyAttempted, Busy, Guard, write_completion


def try_dispatch(directory, queue):
    try:
        Guard(directory).dispatch("second", b"other", lambda _: queue.put("called"))
    except Busy:
        queue.put("busy")


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "resource"
        self.guard = Guard(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_status_has_no_write_side_effect(self):
        self.assertEqual(self.guard.status(), {"state": "idle"})
        self.assertFalse(self.root.exists())

    def test_timeout_survives_new_controller_and_late_completion(self):
        captured = []
        def timeout(attempt):
            captured.append(attempt)
            raise TimeoutError("transport stopped waiting")
        with self.assertRaises(TimeoutError):
            self.guard.dispatch("first", b"request", timeout)
        guard = Guard(self.root)
        self.assertEqual(guard.status()["state"], "outcome_unknown")
        with self.assertRaises(Busy):
            guard.dispatch("second", b"other", lambda _: self.fail("must not dispatch"))
        with self.assertRaises(Busy):
            guard.reconcile()
        write_completion(captured[0])
        self.assertEqual(guard.reconcile()["state"], "native_finished")
        with self.assertRaises(AlreadyAttempted):
            guard.dispatch("first", b"request", lambda _: self.fail("must not retry"))
        guard.dispatch("second", b"other", write_completion)

    def test_transport_success_without_marker_stays_unknown(self):
        self.assertEqual(self.guard.dispatch("one", b"r", lambda _: "ok"), "ok")
        self.assertEqual(self.guard.status()["state"], "outcome_unknown")

    def test_wrong_marker_cannot_release_claim(self):
        captured = []
        self.guard.dispatch("one", b"r", lambda a: captured.append(a))
        marker = Path(captured[0]["completion_path"])
        marker.write_text(json.dumps({"attempt_id": "wrong", "request_sha256": captured[0]["request_sha256"], "native_finished": True}))
        with self.assertRaises(Busy):
            self.guard.reconcile()
        marker.write_text("broken JSON")
        with self.assertRaises(Busy):
            self.guard.reconcile()

    def test_native_completion_does_not_claim_business_success(self):
        def failure(attempt):
            write_completion(attempt)
            raise RuntimeError("native job failed and exited")
        with self.assertRaises(RuntimeError):
            self.guard.dispatch("one", b"r", failure)
        self.assertEqual(self.guard.status()["state"], "native_finished")
        self.assertNotIn("success", self.guard.status())

    def test_distinct_process_cannot_dispatch_while_lock_is_held(self):
        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        def runner(attempt):
            child = ctx.Process(target=try_dispatch, args=(str(self.root), queue))
            child.start()
            try:
                self.assertEqual(queue.get(timeout=10), "busy")
                child.join(10)
                self.assertEqual(child.exitcode, 0)
                self.assertFalse((self.root / "requests" / "second").exists())
            finally:
                if child.is_alive():
                    child.terminate(); child.join()
                queue.close(); queue.join_thread()
            write_completion(attempt)
        self.guard.dispatch("one", b"r", runner)

    def test_crashed_controller_claim_blocks_new_work(self):
        self.root.mkdir()
        (self.root / "current.json").write_text(json.dumps({"state": "running", "attempt_id": "old", "request_sha256": "0" * 64, "completion_path": str(self.root / "missing.json")}))
        with self.assertRaises(Busy):
            self.guard.dispatch("new", b"r", lambda _: self.fail("must not dispatch"))

    def test_corrupt_state_fails_closed(self):
        self.root.mkdir()
        (self.root / "current.json").write_text("broken JSON")
        with self.assertRaises(ValueError):
            self.guard.dispatch("new", b"r", lambda _: self.fail("must not dispatch"))

    def test_request_id_cannot_escape_directory(self):
        for name in ("../outside", "/absolute", "", "a/b"):
            with self.assertRaises(ValueError):
                self.guard.dispatch(name, b"r", write_completion)
        self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
