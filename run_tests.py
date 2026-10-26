"""Offline runner; deliberately fails if a test attempts networking or a child process."""
import json
import sys
import unittest
from pathlib import Path


def offline_guard(event, args):
    if event.startswith('socket.') or event in {'subprocess.Popen', 'os.system'}:
        raise RuntimeError('Network and child-process actions are disabled in this test run')


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    sys.addaudithook(offline_guard)
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern='test_cases.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'passed': result.wasSuccessful(), 'model_evaluation': 'NOT_RUN'}))
    raise SystemExit(not result.wasSuccessful())
