#!/usr/bin/env python3
"""Run trusted checks; compare boundary snapshots, without continuous mutation monitoring."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import sys


class Invalid(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise Invalid(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value):
    return isinstance(value, list) and bool(value) and all(text(x) for x in value)


def load_packet(path):
    raw = path.read_bytes()
    packet = json.loads(raw)
    require(isinstance(packet, dict), 'packet must be an object')
    require(set(packet) == {'version', 'objective', 'inputs', 'write_scope',
                            'invariants', 'environment', 'checks'}, 'unknown or missing packet fields')
    require(type(packet['version']) is int and packet['version'] == 1, 'unsupported version')
    require(text(packet['objective']) and text(packet['environment']), 'objective/environment required')
    for field in ('inputs', 'write_scope', 'invariants'):
        require(strings(packet[field]), field + ' must be a nonempty string list')
    checks = packet['checks']
    require(isinstance(checks, list) and bool(checks), 'checks must be nonempty')
    ids = set()
    for check in checks:
        require(isinstance(check, dict) and set(check) == {
            'id', 'invariant', 'argv', 'expected_exit', 'stdout_contains', 'timeout_seconds'
        }, 'unknown or missing check fields')
        require(text(check['id']) and check['id'] not in ids, 'duplicate or empty check id')
        ids.add(check['id'])
        require(check['invariant'] in packet['invariants'], 'check must name a declared invariant')
        require(check['argv'] is None or strings(check['argv']), 'argv must be a list or null')
        require(type(check['expected_exit']) is int and 0 <= check['expected_exit'] <= 255,
                'expected_exit must be an integer exit code')
        require(strings(check['stdout_contains']), 'observable expected output required')
        require(type(check['timeout_seconds']) is int and 1 <= check['timeout_seconds'] <= 3600,
                'timeout_seconds must be between 1 and 3600')
    require(set(packet['invariants']) == {c['invariant'] for c in checks},
            'every invariant needs a check')
    return packet, hashlib.sha256(raw).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def snapshot(root):
    revision = git(root, 'rev-parse', 'HEAD').decode().strip()
    paths = set(git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0'))
    digest = hashlib.sha256()
    for raw in sorted(paths - {b''}):
        path = root / raw.decode('utf-8')
        require(root in path.resolve().parents and not path.is_symlink(),
                'source symlinks/escaping paths require a project-specific verifier')
        require(not path.exists() or path.is_file(), 'submodules/non-file inputs require a project-specific verifier')
        content = path.read_bytes() if path.exists() else b''
        mode = str(stat.S_IMODE(path.stat().st_mode)) if path.exists() else 'missing'
        for part in (raw, mode.encode(), content):
            digest.update(len(part).to_bytes(8, 'big') + part)
    return {'revision': revision, 'source_sha256': digest.hexdigest()}


def result(check, observation):
    if check['argv'] is None or observation.get('not_run'):
        return 'NOT RUN'
    if (type(observation.get('exit_code')) is not int
            or not isinstance(observation.get('stdout'), str)
            or not isinstance(observation.get('stderr'), str)):
        return 'NOT RUN'
    return 'PASS' if (observation['exit_code'] == check['expected_exit']
                      and all(s in observation['stdout'] for s in check['stdout_contains'])) else 'FAIL'


def gate(packet, packet_hash, report, current, environment):
    require(isinstance(report, dict), 'report must be an object')
    require(report.get('packet_sha256') == packet_hash, 'packet changed; rerun verification')
    require(report.get('before') == current and report.get('after') == current,
            'source/revision changed; rerun verification')
    require(report.get('environment') == environment == packet['environment'],
            'environment identity changed; rerun verification')
    rows = report.get('observations')
    require(isinstance(rows, list), 'missing observations')
    require(len(rows) == len(packet['checks']), 'missing/extra observations')
    require(all(isinstance(row, dict) for row in rows), 'invalid observations')
    by_id = {row.get('id'): row for row in rows}
    require(len(by_id) == len(rows) and set(by_id) == {c['id'] for c in packet['checks']},
            'duplicate/missing/extra check ids')
    return all(result(check, by_id[check['id']]) == 'PASS' for check in packet['checks'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run', 'check'])
    parser.add_argument('packet', type=Path)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--environment', required=True, help='current runtime/config/fixture identity')
    args = parser.parse_args()
    try:
        root = Path(git(args.repo, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
        report_path = args.report.resolve()
        require(root != report_path and root not in report_path.parents,
                'report must be outside the source checkout')
        packet, packet_hash = load_packet(args.packet)
        require(args.environment == packet['environment'], 'environment does not match packet')
        before = snapshot(root)
        if args.action == 'run':
            require(not report_path.exists(), 'report already exists; preserve it and use a fresh path')
            rows = []
            for check in packet['checks']:
                row = {'id': check['id']}
                if check['argv'] is None:
                    row['not_run'] = 'manual observation requires a project-specific driver'
                else:
                    try:
                        completed = subprocess.run(check['argv'], cwd=root, capture_output=True,
                                                   text=True, timeout=check['timeout_seconds'], check=False)
                        row.update(exit_code=completed.returncode, stdout=completed.stdout, stderr=completed.stderr)
                    except (OSError, subprocess.TimeoutExpired, UnicodeError) as error:
                        row['not_run'] = type(error).__name__
                row['status'] = result(check, row)
                rows.append(row)
            report = {'packet_sha256': packet_hash, 'environment': args.environment,
                      'before': before, 'after': snapshot(root), 'observations': rows}
            with report_path.open('x') as stream:
                json.dump(report, stream, indent=2)
                stream.write('\n')
        else:
            report = json.loads(report_path.read_text())
        current_packet, current_hash = load_packet(args.packet)
        accepted = gate(current_packet, current_hash, report, snapshot(root), args.environment)
        for check in packet['checks']:
            row = next(r for r in report['observations'] if r['id'] == check['id'])
            print(check['id'] + ': ' + result(check, row))
        print('PASS: recorded checks match this snapshot' if accepted else 'BLOCKED: failed or NOT RUN checks')
        return 0 if accepted else 1
    except (Invalid, OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        print('BLOCKED: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
