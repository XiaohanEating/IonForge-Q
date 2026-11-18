"""Inspect only the selections and geometry required for CAD replacement."""
from pathlib import Path
import json
import sys
import time
import mph

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.paths import run_data, resolve_record_paths, input_path
OUT = run_data()
SOURCE = input_path('model')

def plain(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return [plain(v) for v in value]
    except TypeError:
        return str(value)

def selection(node):
    result = {}
    try:
        s = node.selection()
        for key, method in [('dimension', s.dimension), ('entities', s.entities), ('named', s.named)]:
            try:
                result[key] = plain(method())
            except Exception:
                pass
    except Exception:
        pass
    return result

def walk(node, path):
    rows = [{'path': path, 'type': str(node.getType()) if hasattr(node, 'getType') else type(node).__name__, 'label': str(node.label()), 'selection': selection(node)}]
    try:
        for tag in node.feature().tags():
            rows.extend(walk(node.feature(tag), path + [str(tag)]))
    except Exception:
        pass
    return rows

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    OUT.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    client = mph.start(cores=2, version='6.3')
    print('CLIENT_READY', flush=True)
    model = client.load(str(SOURCE)); j = model.java; g = j.geom('geom1')
    print('MODEL_LOADED', flush=True)
    record = {'source': str(SOURCE), 'geometry': [], 'nodes': []}
    for tag in g.feature().tags():
        f = g.feature(tag)
        row = {'tag': str(tag), 'type': str(f.getType()), 'active': bool(f.isActive()), 'selections': {}}
        for key in ['input', 'input2']:
            try:
                s = f.selection(key)
                row['selections'][key] = {'objects': plain(s.objects()), 'named': str(s.named())}
            except Exception as exc:
                row['selections'][key] = {'error': str(exc)[:100]}
        record['geometry'].append(row)
    for tag in j.physics().tags():
        record['nodes'].extend(walk(j.physics(tag), ['physics', str(tag)]))
    print('PHYSICS_INSPECTED', flush=True)
    for tag in j.material().tags():
        record['nodes'].extend(walk(j.material(tag), ['material', str(tag)]))
    record['nodes'].extend(walk(j.mesh('mesh1'), ['mesh', 'mesh1']))
    print('MESH_INSPECTED', flush=True)
    for label, name in [('B7', 'imp1.637'), ('A7', 'imp1.117')]:
        g.export().selection().set([name]); g.export(str(OUT / (label + '.step')))
    record['elapsed_seconds'] = time.perf_counter() - start
    (OUT / 'model_inspection.json').write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'geometry': record['geometry'], 'selection_nodes': [r for r in record['nodes'] if r['selection'].get('entities') and len(r['selection']['entities']) < 15], 'seconds': record['elapsed_seconds']}, ensure_ascii=False), flush=True)
    client.remove(model)

if __name__ == '__main__':
    main()
