"""Local-only policy decisions. Storage boundaries only; no process control or file relocation."""
from contextlib import contextmanager
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import uuid


class Denied(ValueError):
    """Messages are stable codes, never private input values."""


def allow(condition, code):
    if not condition:
        raise Denied(code)


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def alias(value):
    return isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', value) is not None


def digest(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def external(repo, path):
    repo = Path(repo).resolve()

    def check(candidate):
        allow(repo != candidate and repo not in candidate.parents, 'private_location_inside_checkout')
        allow(not any(parent.name == '.git' or (parent / '.git').exists()
                      for parent in [candidate, *candidate.parents]), 'private_location_inside_git')

    original = Path(path).absolute()
    current = Path(original.anchor)
    pending = list(original.parts[1:])
    links = 0
    check(current)
    while pending:
        part = pending.pop(0)
        if part == '..':
            current = current.parent
            check(current)
            continue
        candidate = current / part
        check(candidate)
        if candidate.is_symlink():
            links += 1
            allow(links <= 40, 'private_path_symlink_loop')
            target = Path(os.readlink(candidate))
            if target.is_absolute():
                current = Path(target.anchor)
                check(current)
                pending = list(target.parts[1:]) + pending
            else:
                pending = list(target.parts) + pending
        else:
            current = candidate
    return current


def private_config(repo, path):
    try:
        location = external(repo, path)
        allow(location.stat().st_mode & 0o077 == 0, 'private_config_permissions')
        value = json.loads(location.read_text())
        allow(isinstance(value, dict), 'invalid_private_config')
        return value
    except (OSError, ValueError):
        raise Denied('invalid_private_config') from None


class LocalLedger:
    """One local serialized ledger; crash locks require reconciliation, never auto-expiry."""
    def __init__(self, repo, directory):
        self.repo = Path(repo).resolve()
        self.directory = external(self.repo, directory)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        allow(not self.directory.is_symlink() and self.directory.stat().st_mode & 0o077 == 0,
              'invalid_private_location')

    @contextmanager
    def transaction(self):
        lock = self.directory / 'lock'
        try:
            lock.mkdir(mode=0o700)
        except FileExistsError:
            raise Denied('ledger_busy') from None
        try:
            path = self.directory / 'state.json'
            allow(not path.is_symlink(), 'invalid_private_state')
            try:
                state = json.loads(path.read_text()) if path.exists() else {
                    'tasks': {}, 'writers': {}, 'reservations': {}}
            except (OSError, ValueError):
                raise Denied('invalid_private_state') from None
            allow(isinstance(state, dict) and set(state) == {'tasks', 'writers', 'reservations'}
                  and all(isinstance(v, dict) for v in state.values()), 'invalid_private_state')
            yield state
            descriptor, temp = tempfile.mkstemp(dir=self.directory)
            try:
                with os.fdopen(descriptor, 'w') as stream:
                    json.dump(state, stream)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temp, path)
                directory_fd = os.open(self.directory, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            finally:
                if Path(temp).exists():
                    Path(temp).unlink()
        finally:
            lock.rmdir()


def within(root, relative):
    allow(isinstance(relative, str) and relative and '\\' not in relative, 'path_escape')
    parts = relative.split('/')
    allow(not PurePosixPath(relative).is_absolute() and all(p not in {'', '.', '..'} for p in parts),
          'path_escape')
    root = Path(root).resolve()
    path = root
    for part in parts:
        path /= part
        allow(not path.is_symlink(), 'path_escape')
    allow(root in path.resolve().parents, 'path_escape')
    return path


@dataclass(frozen=True)
class VolumeObservation:
    mount_root: Path
    identity: str
    mounted: bool
    actual_mount: bool
    features: frozenset
    free_bytes: int
    measured_at: float


@dataclass(frozen=True)
class StoragePolicy:
    identity: str
    required_features: frozenset
    max_observation_age: float
    safety_bytes: int


def reserve(ledger, reservation, policy, observation, peak_bytes, now, artifact_relative='artifacts'):
    allow(alias(reservation), 'invalid_reservation')
    allow(isinstance(observation, VolumeObservation) and observation.mounted is True
          and observation.actual_mount is True, 'volume_not_verified_mounted')
    allow(isinstance(policy.identity, str) and bool(policy.identity.strip())
          and observation.identity == policy.identity, 'volume_identity_mismatch')
    allow(Path(observation.mount_root).is_dir(), 'mount_path_missing')
    artifact_root = within(observation.mount_root, artifact_relative)
    disjoint_roots(ledger.repo, artifact_root, ledger.directory)
    allow(isinstance(policy.required_features, frozenset) and bool(policy.required_features)
          and isinstance(observation.features, frozenset)
          and policy.required_features <= observation.features, 'unsupported_metadata_or_features')
    allow(number(now) and number(observation.measured_at) and number(policy.max_observation_age)
          and 0 <= now - observation.measured_at <= policy.max_observation_age, 'stale_volume_observation')
    allow(type(peak_bytes) is int and peak_bytes > 0 and type(observation.free_bytes) is int
          and observation.free_bytes >= 0 and type(policy.safety_bytes) is int
          and policy.safety_bytes >= 0, 'invalid_storage_budget')
    with ledger.transaction() as state:
        reservations = state['reservations']
        allow(reservation not in reservations, 'duplicate_reservation')
        pending = sum(r['bytes'] for r in reservations.values() if r['volume'] == policy.identity and r['active'])
        allow(peak_bytes + pending + policy.safety_bytes <= observation.free_bytes, 'storage_budget_conflict')
        token = uuid.uuid4().hex
        reservations[reservation] = {'volume': policy.identity, 'bytes': peak_bytes,
                                     'active': True, 'token': token}
    return token


def release_reservation(ledger, reservation, token, operation_stopped):
    allow(operation_stopped is True, 'storage_operation_stop_unconfirmed')
    with ledger.transaction() as state:
        entry = state['reservations'].get(reservation)
        allow(entry and entry['token'] == token, 'reservation_identity_mismatch')
        entry['active'] = False


def disjoint_roots(source, artifacts, state):
    roots = [Path(p).resolve() for p in (source, artifacts, state)]
    allow(all(a != b and a not in b.parents and b not in a.parents
              for i, a in enumerate(roots) for b in roots[i + 1:]), 'source_artifact_state_overlap')


@dataclass(frozen=True)
class Inventory:
    content_sha256: str
    metadata_sha256: str
    count: int
    bytes: int


def relocation_decision(before, stable_source, copied, restored, metadata_supported,
                        reference_published=False, actual_reclaimed_bytes=None):
    for item in (before, stable_source, copied, restored):
        allow(isinstance(item, Inventory) and digest(item.content_sha256)
              and digest(item.metadata_sha256) and type(item.count) is int and item.count >= 0
              and type(item.bytes) is int and item.bytes >= 0, 'invalid_inventory')
    allow(metadata_supported is True, 'unsupported_metadata')
    allow(before == stable_source == copied == restored, 'copy_or_recovery_mismatch')
    allow(actual_reclaimed_bytes is None or (type(actual_reclaimed_bytes) is int
          and actual_reclaimed_bytes >= 0), 'invalid_reclaimed_measurement')
    return {'may_publish_reference': True, 'reference_published': reference_published is True,
            'keep_original': True, 'may_delete': False, 'is_backup': False,
            'logical_bytes': before.bytes, 'actual_reclaimed_bytes': actual_reclaimed_bytes}
