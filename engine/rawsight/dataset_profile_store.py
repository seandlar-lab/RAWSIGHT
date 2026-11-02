"""Persistent, provenance-aware Light Analysis profiles (v0.1).

No source data is copied. This module does not modify the existing profiler.
Call get_or_create_profile from a future import bridge, passing profile_dataset.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

SCHEMA_VERSION = 1
ANALYSIS_VERSION = 'light-analysis-v0.1'  # bump on changes that affect profile output
FINGERPRINT_SAMPLE_BYTES = 65536


def _fingerprint(path: Path) -> dict:
    """Fast file identity: stat and bounded head/tail digest (not a full hash)."""
    resolved = path.expanduser().resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f'Not a regular file: {resolved}')
    before = resolved.stat()
    digest = hashlib.sha256()
    with resolved.open('rb') as source:
        digest.update(source.read(FINGERPRINT_SAMPLE_BYTES))
        if before.st_size > FINGERPRINT_SAMPLE_BYTES:
            source.seek(max(0, before.st_size - FINGERPRINT_SAMPLE_BYTES))
            digest.update(source.read(FINGERPRINT_SAMPLE_BYTES))
    after = resolved.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError(f'Source changed while fingerprinting: {resolved}')
    return {
        'path': str(resolved), 'size_bytes': after.st_size,
        'modified_ns': after.st_mtime_ns, 'edge_sha256': digest.hexdigest(),
        'fingerprint_method': 'stat_and_first_last_64k_sha256',
    }


def _read_external_metadata(metadata_path: str | None) -> tuple[dict | None, dict | None]:
    if metadata_path is None:
        return None, None
    path = Path(metadata_path)
    fingerprint = _fingerprint(path)
    if path.suffix.lower() != '.json':
        raise ValueError('v0.1 supports JSON metadata files only')
    with path.open('r', encoding='utf-8') as source:
        content = json.load(source)
    if not isinstance(content, dict):
        raise ValueError('Metadata JSON root must be an object')
    return fingerprint, content


def _cache_key(source: dict, external: dict | None, analysis_version: str) -> str:
    material = json.dumps({
        'schema_version': SCHEMA_VERSION,
        'analysis_version': analysis_version,
        'source': source, 'external_metadata_source': external,
    }, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(material.encode('utf-8')).hexdigest()


def _write_atomic(destination: Path, value: dict) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2)
    descriptor, temp_name = tempfile.mkstemp(prefix='.profile-', suffix='.tmp', dir=destination.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def get_or_create_profile(
    file_path: str,
    store_dir: str,
    profiler: Callable[[str], dict],
    metadata_path: str | None = None,
    analysis_version: str = ANALYSIS_VERSION,
    force: bool = False,
) -> dict:
    """Return {'cache_status', 'profile_path', 'dataset_profile'}.

    Cache hits never call profiler. Metadata source and inferred profile remain separate.
    The profile store is an explicit directory owned by the caller/project.
    """
    if not analysis_version.strip():
        raise ValueError('analysis_version must be non-empty')
    source = _fingerprint(Path(file_path))
    metadata_source, external_metadata = _read_external_metadata(metadata_path)
    key = _cache_key(source, metadata_source, analysis_version)
    destination = Path(store_dir).expanduser().resolve() / f'{key}.json'
    if not force and destination.is_file():
        try:
            with destination.open('r', encoding='utf-8') as saved:
                document = json.load(saved)
            if (document.get('schema_version') == SCHEMA_VERSION
                and document.get('cache_key') == key
                and document.get('source') == source
                and document.get('external_metadata_source') == metadata_source
                and document.get('analysis_version') == analysis_version
                and isinstance(document.get('light_analysis'), dict)):
                return {'cache_status': 'reused', 'profile_path': str(destination),
                        'dataset_profile': document}
        except (ValueError, OSError, TypeError, AttributeError):
            pass  # corrupted/incompatible cache: rebuild
    light_analysis = profiler(source['path'])
    if not isinstance(light_analysis, dict):
        raise TypeError('Profiler must return a dict')
    # Reject stale writes when the source/metadata changes during profiling.
    if _fingerprint(Path(file_path)) != source:
        raise RuntimeError('Dataset changed during profiling; profile not saved')
    if metadata_source is not None and _fingerprint(Path(metadata_path)) != metadata_source:
        raise RuntimeError('Metadata changed during profiling; profile not saved')
    document = {
        'schema_version': SCHEMA_VERSION, 'cache_key': key,
        'analysis_version': analysis_version,
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'source': source,
        'external_metadata_source': metadata_source,
        'external_metadata': external_metadata,
        'light_analysis': light_analysis,
        'user_confirmed_metadata': {},
        'provenance': {
            'light_analysis': 'derived_by_rawsight',
            'external_metadata': 'supplied_file' if metadata_source else 'not_supplied',
            'user_confirmed_metadata': 'not_collected_in_v0.1',
        },
        'limitations': [
            'Fast fingerprint does not detect changes confined to the middle of a file '
            'if file size and modification timestamp remain unchanged.',
            'External metadata is stored separately; it is not treated as verified fact.',
            'No source observations are copied to the profile store.',
        ],
    }
    _write_atomic(destination, document)
    return {'cache_status': 'created' if not force else 'refreshed',
            'profile_path': str(destination), 'dataset_profile': document}
