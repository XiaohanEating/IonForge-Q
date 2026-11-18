"""Keep archived evidence read-only and reruns in explicitly prepared folders."""
from pathlib import Path
import os
import json

ROOT = Path(__file__).resolve().parents[1]

def run_data():
    value = os.environ.get('IONFORGE_RUN_DIR')
    if not value:
        raise RuntimeError('Prepare a run with python -m tools.prepare_run --output runs/demo, then set IONFORGE_RUN_DIR.')
    path = Path(value).resolve()
    if path == (ROOT / 'results').resolve() or ROOT / 'results' in path.parents:
        raise ValueError('Published result tables are read-only for reruns.')
    if not (path / '.ionforge-run').is_file():
        raise ValueError('Run directory is not prepared; use tools.prepare_run.')
    return path


def input_path(key, directory=False):
    config = json.loads((run_data() / 'inputs.json').read_text(encoding='utf-8'))
    if key not in config:
        raise ValueError(f'Missing user-supplied {key}; see tools.prepare_run --help.')
    path = Path(config[key]).resolve()
    if not (path.is_dir() if directory else path.is_file()):
        raise FileNotFoundError(f'Configured {key} does not exist: {path}')
    return path

def resolve_record_paths(records):
    for record in records.values():
        for key in ['source', 'step']:
            path = Path(record[key])
            if not path.is_absolute():
                record[key] = str(ROOT / path)
    return records
