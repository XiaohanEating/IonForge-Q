"""Content-addressed dependencies and independent acceptance predicates."""
from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

DEPENDENCIES = {
    'cad': ('geometry',),
    'mapping': ('geometry', 'roles'),
    'mesh': ('geometry', 'mesh_settings'),
    'field': ('geometry', 'roles', 'materials', 'drives', 'mesh_settings', 'solver'),
    'samples': ('geometry', 'roles', 'materials', 'drives', 'mesh_settings', 'solver', 'sampling'),
}

def digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()

def file_hash(path: Path) -> str:
    h = sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def signature(stage: str, state: dict) -> str:
    """Missing dependencies are an error, never a reusable partial signature."""
    return digest({key: state[key] for key in DEPENDENCIES[stage]})

def invalidated(previous: dict, current: dict) -> list[str]:
    return [stage for stage in DEPENDENCIES if signature(stage, previous) != signature(stage, current)]

@dataclass
class Verification:
    geometry: bool | None = None
    assignment: bool | None = None
    provenance: bool | None = None
    numerics: bool | None = None
    reasons: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if False in (self.geometry, self.assignment, self.provenance):
            return 'REJECT'
        if all(x is True for x in (self.geometry, self.assignment, self.provenance, self.numerics)):
            return 'ACCEPT'
        return 'UNRESOLVED'

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temporary.replace(path)
