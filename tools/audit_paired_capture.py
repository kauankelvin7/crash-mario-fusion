"""Audit integrity of local paired CMW1 receiver logs without exposing poses.

This is a self-consistency check, not original-game authentication or physics sync.
Does not launch games, send packets, or access game files.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

MAX_LOG_BYTES = 32 * 1024 * 1024
MAX_SUMMARY_BYTES = 64 * 1024
MAX_ROWS = 14000  # 10,000 bounded arrivals + 3,002 status records
ENGINE_NAMES = {1: 'crash', 2: 'mario'}


class AuditError(ValueError):
    """Captured receiver log and summary do not agree."""


def require(ok, message):
    if not ok:
        raise AuditError(message)


def object_json(line):
    def reject_nonfinite(_):
        raise AuditError('Nonfinite JSON number')
    try:
        value = json.loads(line, parse_constant=reject_nonfinite)
    except (ValueError, UnicodeDecodeError) as exc:
        raise AuditError('Invalid JSON capture entry') from exc
    require(type(value) is dict, 'Capture entry must be an object')
    return value


def audit_rows(rows, summary):
    """Deterministic audit; returns only anonymous aggregates."""
    require(type(summary) is dict, 'Summary must be an object')
    require(summary.get('physical_status') == 'BLOCKED' and summary.get('calibration_ready') is False,
            'Summary overstates physical validation')
    require(summary.get('live_gameplay_verified') is False, 'Summary overstates gameplay validation')
    sources = summary.get('sources')
    rejects = summary.get('rejection_counts')
    require(type(sources) is dict and set(sources) == {'1', '2'}, 'Summary requires both engines')
    require(type(rejects) is dict and all(type(k) is str and type(v) is int and v >= 0
                                          for k, v in rejects.items()), 'Invalid rejection counters')
    received = statuses = paired_statuses = 0
    clock_id = previous_clock = None
    counted_rejections = Counter()
    states = {e: {'accepted': 0, 'last_sequence': 0, 'last_arrival_ns': None,
                  'sequence_holes': 0, 'maximum_arrival_gap_ns': 0} for e in ENGINE_NAMES}
    for row in rows:
        require(type(row) is dict, 'Invalid capture row')
        require(row.get('physical_status') == 'BLOCKED' and row.get('calibration_ready') is False
                and row.get('source_delay') == 'UNKNOWN', 'Capture row overstates validation')
        cid = row.get('receiver_clock_id')
        stamp = row.get('receiver_monotonic_ns')
        require(type(cid) is str and bool(cid) and type(stamp) is int and 0 <= stamp < 2**64,
                'Invalid receiver clock identity/timestamp')
        if clock_id is None:
            clock_id = cid
        require(cid == clock_id, 'Mixed receiver clock domains')
        require(previous_clock is None or stamp >= previous_clock, 'Receiver clock regressed')
        previous_clock = stamp
        kind = row.get('kind')
        if kind == 'status':
            statuses += 1
            require(type(row.get('telemetry_comparable')) is bool, 'Invalid telemetry diagnostic')
            require(type(row.get('sources')) is list and len(row['sources']) == 2 and
                    {s.get('engine') for s in row['sources'] if type(s) is dict} == {1, 2},
                    'Missing engine in status record')
            if row['telemetry_comparable']:
                paired_statuses += 1
        elif kind == 'arrival':
            received += 1
            require(type(row.get('accepted')) is bool, 'Invalid admission boolean')
            reason = row.get('reason')
            require(reason == 'ACCEPTED' or reason in rejects, 'Unknown admission reason')
            if reason != 'ACCEPTED':
                counted_rejections[reason] += 1
            observed = row.get('observed')
            if row['accepted']:
                require(type(observed) is dict and type(row.get('snapshot')) is dict,
                        'Accepted packet missing pose or envelope')
                engine = observed.get('engine')
                require(type(engine) is int and engine in ENGINE_NAMES, 'Unknown accepted engine')
                sequence = observed.get('sequence')
                require(type(sequence) is int and 0 < sequence < 2**32,
                        'Invalid accepted sequence')
                state = states[engine]
                require(sequence > state['last_sequence'], 'Duplicate or regressed accepted sequence')
                holes = sequence - state['last_sequence'] - 1
                gap = None if state['last_arrival_ns'] is None else stamp - state['last_arrival_ns']
                require(row.get('sequence_holes') == holes and row.get('receiver_arrival_gap_ns') == gap,
                        'Incorrect sequence-hole/arrival-gap diagnostic')
                require(row['snapshot'].get('engine') == engine and
                        row['snapshot'].get('sequence') == sequence,
                        'Recorded snapshot mismatches accepted envelope')
                state['accepted'] += 1
                state['sequence_holes'] += holes
                state['last_sequence'] = sequence
                state['last_arrival_ns'] = stamp
                state['maximum_arrival_gap_ns'] = max(state['maximum_arrival_gap_ns'], gap or 0)
            else:
                require('snapshot' not in row and row.get('sequence_holes') is None and
                        row.get('receiver_arrival_gap_ns') is None,
                        'Rejected packet incorrectly treated as valid pose')
        else:
            raise AuditError('Unknown capture row kind')
        require(received <= 10000 and received + statuses <= MAX_ROWS,
                'Capture exceeds bounded receiver contract')
    require(statuses >= 1, 'No receiver status records')
    require(type(summary.get('attempts')) is int and summary['attempts'] == received,
            'Summary attempt count differs from arrival rows')
    for engine, state in states.items():
        require(sources[str(engine)] == state, 'Summary disagrees with accepted packet diagnostics')
    require(all(counted_rejections.get(k, 0) == v for k, v in rejects.items()),
            'Summary rejection counters differ from arrival rows')
    return {
        'result': 'CONSISTENT' if received else 'EMPTY_CAPTURE',
        'evidence_scope': 'RECEIVER_LOG_SELF_CONSISTENCY_ONLY',
        'arrival_records': received,
        'status_records': statuses,
        'paired_telemetry_status_records': paired_statuses,
        'accepted_packets': {name: states[engine]['accepted'] for engine, name in ENGINE_NAMES.items()},
        'rejected_packets': sum(counted_rejections.values()),
        'physical_status': 'BLOCKED',
        'calibration_ready': False,
        'live_gameplay_verified_by_audit': False,
        'source_delay': 'UNKNOWN',
    }


def audit_folder(folder):
    """Read finite local files only; never include raw pose data in output."""
    root = Path(folder)
    log = root / 'observations.jsonl'
    report = root / 'summary.json'
    for path, bound in ((log, MAX_LOG_BYTES), (report, MAX_SUMMARY_BYTES)):
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= bound,
                'Capture file missing, linked, or beyond audit size limit')
    with report.open('r', encoding='utf-8-sig') as stream:
        summary = object_json(stream.read())
    with log.open('r', encoding='utf-8-sig') as stream:
        def parsed():
            for index, line in enumerate(stream, start=1):
                require(index <= MAX_ROWS, 'Capture row limit exceeded')
                require(len(line) <= 20000, 'Oversized capture row')
                yield object_json(line)
        return audit_rows(parsed(), summary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True, type=Path,
                        help='Local private paired-... folder; do not upload it')
    args = parser.parse_args(argv)
    try:
        result = audit_folder(args.capture)
    except (AuditError, OSError, UnicodeError) as exc:
        parser.exit(1, 'Paired capture audit FAILED: local capture integrity check rejected.\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
