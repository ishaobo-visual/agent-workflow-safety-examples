import json
import tempfile
import unittest
from pathlib import Path
from safety_examples import ActionLedger, Blocked, check_receipt, digest, quarantine, revise_one, route


class SafetyCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='synthetic-safety-')
        self.addCleanup(self.tmp.cleanup)
        # macOS exposes its temporary directory through a system path alias.
        # Canonicalize only the fixture root; linked child paths remain blocked.
        self.root = Path(self.tmp.name).resolve()
        self.state = {'status': 'ACTIVE', 'revision': 1}
        self.calls = []
        self.ledger = ActionLedger(self.root / 'actions.sqlite')
        self.addCleanup(self.ledger.close)

    def transport(self):
        self.calls.append('synthetic write')
        return 'returned, not verified'

    def run_action(self, **kw):
        return self.ledger.execute('action-example', lambda: dict(self.state), 1, kw.pop('transport', self.transport), **kw)

    def files(self):
        names = ['accepted/a.bin', 'accepted/b.bin', 'accepted/c.bin', 'history/record.txt', 'original/source.bin', 'config/api-example.json', 'cache/generated.bin', 'cache/retained.bin']
        for name in names:
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(('SYNTHETIC PUBLIC EXAMPLE: ' + name).encode())
        return {name: digest(self.root / name) for name in names}

    def test_B01_paused_no_action(self):
        self.state['status'] = 'PAUSED'
        with self.assertRaises(Blocked): self.run_action()
        self.assertEqual(self.calls, [])
        self.assertEqual(self.state['status'], 'PAUSED')

    def test_B01_active_positive_control(self):
        self.run_action()
        self.assertEqual(len(self.calls), 1)

    def test_B02_explicit_route_beats_name(self):
        catalog = {'report': {'name': 'Visual statistics', 'line': 'data', 'enabled': True}}
        self.assertEqual(route('report', catalog), 'data')
        with self.assertRaises(Blocked): route('invented', catalog)

    def test_B03_unknown_survives_restart(self):
        def timeout():
            self.calls.append('unknown outcome')
            raise TimeoutError('synthetic')
        with self.assertRaises(TimeoutError): self.run_action(transport=timeout)
        self.ledger.close()
        self.ledger = ActionLedger(self.root / 'actions.sqlite')
        self.addCleanup(self.ledger.close)
        with self.assertRaises(Blocked): self.run_action()
        self.assertEqual(len(self.calls), 1)

    def test_B03_returned_not_replayed(self):
        self.run_action()
        with self.assertRaises(Blocked): self.run_action()
        self.assertEqual(len(self.calls), 1)

    def test_B04_only_selected_file_changes(self):
        before = self.files()
        frozen = {k: v for k, v in before.items() if k != 'accepted/b.bin'}
        revise_one(self.root, 'accepted/b.bin', 'accepted/b.bin', b'synthetic revision', frozen)
        self.assertNotEqual(digest(self.root / 'accepted/b.bin'), before['accepted/b.bin'])
        for k, v in frozen.items(): self.assertEqual(digest(self.root / k), v)

    def test_B04_expanded_revision_rejected(self):
        before = self.files()
        with self.assertRaises(Blocked):
            revise_one(self.root, 'accepted/a.bin', 'accepted/b.bin', b'bad', before)
        for k, v in before.items(): self.assertEqual(digest(self.root / k), v)

    def test_B04_frozen_drift_detected_before_write(self):
        before = self.files()
        (self.root / 'accepted/a.bin').write_bytes(b'external drift')
        with self.assertRaises(Blocked):
            revise_one(self.root, 'accepted/b.bin', 'accepted/b.bin', b'bad', {'accepted/a.bin': before['accepted/a.bin']})
        self.assertEqual(digest(self.root / 'accepted/b.bin'), before['accepted/b.bin'])

    def test_B05_protected_mixed_plan_has_no_partial_move(self):
        before = self.files()
        for name in ['history/record.txt', 'original/source.bin', 'accepted/a.bin', 'config/api-example.json', 'cache/retained.bin']:
            with self.subTest(name=name), self.assertRaises(Blocked):
                quarantine(self.root, ['cache/generated.bin', name], {'cache/retained.bin'})
            self.assertFalse((self.root / 'quarantine').exists())
            for k, v in before.items(): self.assertEqual(digest(self.root / k), v)

    def test_B05_allowed_cache_move_preserves_protected_files(self):
        before = self.files()
        moved = quarantine(self.root, ['cache/generated.bin'], {'cache/retained.bin'})
        self.assertFalse((self.root / 'cache/generated.bin').exists())
        self.assertEqual(digest(moved[0]), before['cache/generated.bin'])
        for k, v in before.items():
            if k != 'cache/generated.bin': self.assertEqual(digest(self.root / k), v)

    def test_B05_traversal_rejected(self):
        before = self.files()
        with self.assertRaises(Blocked): quarantine(self.root, ['cache/../history/record.txt'], set())
        self.assertEqual(digest(self.root / 'history/record.txt'), before['history/record.txt'])

    def test_B06_receipt_bound_to_context(self):
        receipt = {'task': 'task-example', 'executor': 'executor-example', 'revision': 1}
        check_receipt(receipt, 'task-example', 'executor-example', 1)
        for args in [('other', 'executor-example', 1), ('task-example', 'other', 1), ('task-example', 'executor-example', 2)]:
            with self.subTest(args=args), self.assertRaises(Blocked): check_receipt(receipt, *args)

    def test_B07_disabled_route_blocked(self):
        with self.assertRaises(Blocked): route('legacy', {'legacy': {'line': 'creative', 'enabled': False}})

    def test_B08_pause_between_checks(self):
        def pause(): self.state['status'] = 'PAUSED'
        with self.assertRaises(Blocked): self.run_action(before_send=pause)
        self.assertEqual(self.calls, [])

    def test_B08_revision_change_between_checks(self):
        def change(): self.state['revision'] = 2
        with self.assertRaises(Blocked): self.run_action(before_send=change)
        self.assertEqual(self.calls, [])

    def test_case_catalog_maps_all_tests(self):
        cases = json.loads(Path(__file__).with_name('cases.json').read_text('utf-8'))['cases']
        self.assertEqual({x['id'] for x in cases}, {f'B{i:02}' for i in range(1, 9)})
        for case in cases:
            self.assertTrue(case['tests'])
            for name in case['tests']: self.assertTrue(callable(getattr(self, name, None)), name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
