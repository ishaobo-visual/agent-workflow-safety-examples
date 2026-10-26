"""Offline demonstration. No real application, network, or credentials."""
import tempfile
from dispatch_guard import Busy, Guard, write_completion

with tempfile.TemporaryDirectory() as directory:
    guard = Guard(directory)
    attempts = []
    def delayed_native(attempt):
        attempts.append(attempt)
        raise TimeoutError("controller stopped waiting; native work may continue")
    try:
        guard.dispatch("demo", b"synthetic request", delayed_native)
    except TimeoutError:
        print(guard.status()["state"])
    try:
        guard.dispatch("next", b"synthetic request two", write_completion)
    except Busy:
        print("second dispatch blocked")
    write_completion(attempts[0])  # Simulates an actual late native exit.
    print(guard.reconcile()["state"])
