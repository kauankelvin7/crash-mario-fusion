"""Asset-free local capture integrity tests; never execute original games."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.audit_paired_capture import AuditError, audit_rows, audit_folder


def fixture():
    def common(kind, stamp):
        return dict(kind=kind, receiver_clock_id='receiver-test', receiver_monotonic_ns=stamp,
                    physical_status='BLOCKED', calibration_ready=False, source_delay='UNKNOWN')
    start = common('status', 0)
    start.update(telemetry_comparable=False, sources=[{'engine': 1}, {'engine': 2}])
    arrivals = []
    for engine, sequence, stamp, holes in ((1, 1, 1, 0), (2, 1, 2, 0), (1, 3, 3, 1)):
        row = common('arrival', stamp)
        row.update(accepted=True, reason='ACCEPTED', observed=dict(engine=engine, sequence=sequence),
                   snapshot=dict(engine=engine, sequence=sequence), sequence_holes=holes,
                   receiver_arrival_gap_ns=2 if stamp == 3 else None)
        arrivals.append(row)
    finish = common('status', 4)
    finish.update(telemetry_comparable=True, sources=[{'engine': 1}, {'engine': 2}])
    rows = [start, *arrivals, finish]
    summary = dict(attempts=3, physical_status='BLOCKED', calibration_ready=False,
                   live_gameplay_verified=False,
                   rejection_counts={'MALFORMED': 0, 'PAUSED_REBIND_REQUIRED': 0},
                   sources={
                       '1': dict(accepted=2, sequence_holes=1, last_sequence=3,
                                 last_arrival_ns=3, maximum_arrival_gap_ns=2),
                       '2': dict(accepted=1, sequence_holes=0, last_sequence=1,
                                 last_arrival_ns=2, maximum_arrival_gap_ns=0)})
    return rows, summary


class CaptureAuditTests(unittest.TestCase):
    def test_fixture_local_files_and_privacy(self):
        rows, summary = fixture()
        answer = audit_rows(rows, summary)
        self.assertEqual(answer['arrival_records'], 3)
        self.assertEqual(answer['paired_telemetry_status_records'], 1)
        self.assertEqual(answer['accepted_packets'], {'crash': 2, 'mario': 1})
        self.assertFalse(answer['live_gameplay_verified_by_audit'])
        self.assertNotIn('receiver-test', json.dumps(answer))
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            (folder / 'observations.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
            (folder / 'summary.json').write_text(json.dumps(summary))
            self.assertEqual(audit_folder(folder), answer)

    def test_reject_tampered_clocks_and_attempts(self):
        for case in ('time', 'domain', 'attempts'):
            rows, summary = fixture()
            if case == 'time':
                rows[3]['receiver_monotonic_ns'] = 1
            if case == 'domain':
                rows[2]['receiver_clock_id'] = 'foreign'
            if case == 'attempts':
                summary['attempts'] = 42
            with self.subTest(case=case), self.assertRaises(AuditError):
                audit_rows(rows, summary)

    def test_reject_missing_pose_holes_and_overclaims(self):
        for case in ('pose', 'holes', 'physical', 'calibration'):
            rows, summary = fixture()
            if case == 'pose':
                rows[1].pop('snapshot')
            if case == 'holes':
                rows[3]['sequence_holes'] = 0
            if case == 'physical':
                summary['physical_status'] = 'VERIFIED_REAL'
            if case == 'calibration':
                rows[1]['calibration_ready'] = True
            with self.subTest(case=case), self.assertRaises(AuditError):
                audit_rows(rows, summary)

    def test_rejected_packet_and_paused_admission_semantics(self):
        rows, summary = fixture()
        row = dict(rows[2], accepted=False, reason='MALFORMED', observed=None)
        for field in ('snapshot', 'sequence_holes', 'receiver_arrival_gap_ns'):
            row.pop(field, None)
        rows[2] = row
        summary['rejection_counts']['MALFORMED'] = 1
        summary['sources']['2'] = dict(accepted=0, sequence_holes=0, last_sequence=0,
                                      last_arrival_ns=None, maximum_arrival_gap_ns=0)
        self.assertEqual(audit_rows(rows, summary)['rejected_packets'], 1)
        rows[1]['reason'] = 'PAUSED_REBIND_REQUIRED'
        summary['rejection_counts']['PAUSED_REBIND_REQUIRED'] = 1
        self.assertEqual(audit_rows(rows, summary)['rejected_packets'], 2)

    def test_missing_and_symlinked_private_files_fail(self):
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(AuditError):
                audit_folder(name)
            rows, summary = fixture()
            folder = Path(name)
            (folder / 'observations.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            original = folder / 'original.json'
            original.write_text(json.dumps(summary))
            link = folder / 'summary.json'
            try:
                link.symlink_to(original)
            except OSError as exc:
                # Windows without Developer Mode or elevated rights refuses symlink creation.
                # In that environment the missing summary must still fail closed.
                if getattr(exc, 'winerror', None) != 1314:
                    raise
                self.assertFalse(link.exists())
            with self.assertRaises(AuditError):
                audit_folder(folder)


if __name__ == '__main__':
    unittest.main()
