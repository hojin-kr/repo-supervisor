"""Local-only policy decisions. No provider dispatch, process control, or file relocation."""
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import uuid

from verify import snapshot


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
    path = Path(path).absolute()
    repo = Path(repo).resolve()
    allow(repo != path and repo not in path.parents, 'private_location_inside_checkout')
    resolved = path.resolve()
    allow(repo != resolved and repo not in resolved.parents, 'private_location_inside_checkout')
    allow(not any(parent.name == '.git' or (parent / '.git').exists()
                  for parent in [resolved, *resolved.parents]), 'private_location_inside_git')
    return resolved


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


@dataclass(frozen=True)
class Quote:
    model: str
    capabilities: frozenset
    input_rate: Decimal
    output_rate: Decimal
    currency: str
    unit_tokens: int
    observed_at: float
    expires_at: float


@dataclass(frozen=True)
class ProviderPolicy:
    models: frozenset
    capabilities: frozenset
    currency: str
    unit_tokens: int
    max_rate: Decimal
    max_quote_age: float
    auxiliary_roles: frozenset
    max_attempts: int
    cooldown: float
    max_cooldown: float = 3600

    def validate(self, primary, auxiliaries, now):
        allow(number(now) and type(self.max_attempts) is int and 1 <= self.max_attempts <= 100
              and number(self.cooldown) and number(self.max_cooldown)
              and self.cooldown <= self.max_cooldown
              and number(self.max_quote_age) and self.max_quote_age > 0,
              'invalid_provider_policy')
        allow(isinstance(self.models, frozenset) and bool(self.models)
              and all(isinstance(model, str) and model.strip() == model and model
                      and '*' not in model and '?' not in model for model in self.models)
              and isinstance(self.capabilities, frozenset) and bool(self.capabilities)
              and isinstance(self.auxiliary_roles, frozenset), 'invalid_exact_model_policy')
        allow(isinstance(self.currency, str) and bool(self.currency.strip()), 'invalid_cost_policy')
        allow(isinstance(self.max_rate, Decimal) and self.max_rate.is_finite() and self.max_rate >= 0
              and type(self.unit_tokens) is int and self.unit_tokens > 0, 'invalid_cost_policy')
        allow(isinstance(auxiliaries, dict) and set(auxiliaries) == set(self.auxiliary_roles),
              'uncontrolled_auxiliary_roles')
        for quote in [primary, *auxiliaries.values()]:
            allow(isinstance(quote, Quote) and isinstance(quote.model, str) and quote.model in self.models, 'model_not_allowlisted')
            allow(isinstance(quote.capabilities, frozenset) and self.capabilities <= quote.capabilities,
                  'capability_unknown_or_missing')
            allow(quote.currency == self.currency and type(quote.unit_tokens) is int
                  and quote.unit_tokens == self.unit_tokens,
                  'cost_unit_mismatch')
            allow(number(quote.observed_at) and number(quote.expires_at)
                  and quote.observed_at <= now < quote.expires_at
                  and now - quote.observed_at <= self.max_quote_age, 'cost_unknown_or_expired')
            allow(all(isinstance(rate, Decimal) and rate.is_finite() and 0 <= rate <= self.max_rate
                      for rate in (quote.input_rate, quote.output_rate)), 'cost_unknown_or_excessive')

    def fingerprint(self):
        data = [sorted(self.models), sorted(self.capabilities), self.currency, self.unit_tokens,
                str(self.max_rate), self.max_quote_age, sorted(self.auxiliary_roles),
                self.max_attempts, self.cooldown, self.max_cooldown]
        return hashlib.sha256(json.dumps(data).encode()).hexdigest()


def classify(status=None, code=None):
    """Codes are normalized adapter assertions, never guesses from free-form provider prose."""
    if code == 'POLICY_DENIED':
        return 'policy_denied'
    if status == 401:
        return 'auth'
    if status == 403:
        return 'forbidden'
    if status == 429 and code in {'QUOTA_EXHAUSTED', 'RATE_LIMIT'}:
        return 'quota'
    if status is None and code in {'CONNECTION_RESET', 'NETWORK_TIMEOUT', 'NETWORK_UNREACHABLE'}:
        return 'network'
    if code == 'TEST_FAILED':
        return 'test_failed'
    return 'unknown'


def remaining_fraction(value, *, unit, meaning):
    allow(unit in {'fraction', 'percent'} and meaning in {'used', 'remaining'},
          'ambiguous_quota_units')
    limit = Decimal('1') if unit == 'fraction' else Decimal('100')
    allow(isinstance(value, Decimal) and value.is_finite() and 0 <= value <= limit,
          'invalid_quota_value')
    fraction = value / limit
    return Decimal('1') - fraction if meaning == 'used' else fraction


class ProviderClaims:
    """Record plans and trusted controller receipts. Live dispatch is unsupported."""
    def __init__(self, ledger, policy):
        self.ledger, self.policy = ledger, policy

    def begin(self, task, contract_sha256, owner, primary, auxiliaries, now, resume=False, live=False):
        allow(not live, 'live_adapter_unverified')
        allow(alias(task) and alias(owner) and digest(contract_sha256), 'invalid_task_contract')
        self.policy.validate(primary, auxiliaries, now)
        source = snapshot(self.ledger.repo)
        workspace = str(self.ledger.repo)
        with self.ledger.transaction() as state:
            prior = state['tasks'].get(task)
            allow(not any((item.get('receipt') or {}).get('outcome') == 'policy_denied'
                          for item in state['tasks'].values()), 'policy_denied_terminal')
            allow(workspace not in state['writers'], 'writer_already_claimed')
            allow(not any(key != task and item['contract'] == contract_sha256
                          for key, item in state['tasks'].items()), 'duplicate_contract')
            if prior:
                allow(resume and prior['status'] in {'network_wait', 'quota_wait', 'stopped'},
                      'task_not_resumable')
                allow(prior['contract'] == contract_sha256 and prior['checkpoint'] == source
                      and prior['policy_sha256'] == self.policy.fingerprint(),
                      'checkpoint_or_contract_drift')
                allow(prior['stop_confirmed'] is True and now >= prior['not_before'],
                      'stop_unconfirmed_or_cooldown')
                allow(len(prior['attempts']) < self.policy.max_attempts, 'attempt_budget_exhausted')
                if prior['status'] != 'quota_wait':
                    allow(primary.model == prior['model'], 'retry_must_keep_exact_model')
                attempts = prior['attempts']
            else:
                allow(not resume, 'missing_checkpoint')
                attempts = []
            run_id = uuid.uuid4().hex
            state['tasks'][task] = {'status': 'claimed', 'contract': contract_sha256, 'owner': owner,
                'model': primary.model, 'auxiliaries': {k: q.model for k, q in auxiliaries.items()},
                'attempts': attempts + [{'run_id': run_id, 'model': primary.model, 'receipt': None}],
                'policy_sha256': self.policy.fingerprint(),
                'quote': {'observed_at': primary.observed_at, 'expires_at': primary.expires_at,
                          'input_rate': str(primary.input_rate), 'output_rate': str(primary.output_rate),
                          'currency': primary.currency, 'unit_tokens': primary.unit_tokens},
                'run_id': run_id, 'checkpoint': source,
                'stop_confirmed': False, 'not_before': now, 'receipt': None}
            state['writers'][workspace] = task
        return run_id

    def finish(self, task, run_id, model, outcome, stop_confirmed, now, retry_after=0,
               stop_receipt_sha256=None):
        allow(number(now) and number(retry_after) and retry_after <= self.policy.max_cooldown,
              'invalid_receipt_time_or_cooldown')
        allow(stop_confirmed is not True or digest(stop_receipt_sha256), 'stop_receipt_required')
        allow(outcome in {'policy_denied', 'auth', 'forbidden', 'quota', 'network', 'test_failed',
                          'partial', 'unknown', 'stopped', 'worker_done'}, 'unknown_outcome')
        with self.ledger.transaction() as state:
            current = state['tasks'].get(task)
            allow(current and current['status'] == 'claimed' and current['run_id'] == run_id
                  and current['model'] == model, 'receipt_identity_mismatch')
            allow(current['policy_sha256'] == self.policy.fingerprint(), 'policy_drift')
            allow(now >= current['not_before'], 'receipt_time_before_claim')
            current['receipt'] = {'run_id': run_id, 'model': model, 'outcome': outcome,
                                  'stop_confirmed': stop_confirmed is True, 'at': now,
                                  'stop_receipt_sha256': stop_receipt_sha256}
            current['attempts'][-1]['receipt'] = current['receipt']
            current['stop_confirmed'] = stop_confirmed is True
            if stop_confirmed is not True:
                current['status'] = 'stop_unknown'
                return
            current['checkpoint'] = snapshot(self.ledger.repo)
            current['status'] = {'network': 'network_wait', 'quota': 'quota_wait'}.get(outcome, outcome)
            current['not_before'] = now + max(self.policy.cooldown, retry_after)
            del state['writers'][str(self.ledger.repo)]


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
