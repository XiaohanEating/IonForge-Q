"""Check result-table integrity and internal consistency without raw fields."""
from pathlib import Path
import csv
import hashlib
import json
from ion_trap_chip.verification.records import invalidated, signature

ROOT = Path(__file__).resolve().parents[1]

def rows(name):
    with (ROOT/'results'/name).open(encoding='utf-8',newline='') as handle:
        return list(csv.DictReader(handle))

def main():
    manifest = json.loads((ROOT/'results/manifest.json').read_text(encoding='utf-8'))
    checks = {}
    actual = {p.relative_to(ROOT).as_posix() for p in (ROOT/'results').glob('*.csv')}
    checks['table_inventory'] = {r['path'] for r in manifest['files']} == actual and len(actual) == 8
    checks['file_hashes'] = all((ROOT/r['path']).is_file() and hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest() == r['sha256'] for r in manifest['files'])
    records = rows('assignments.csv')
    checks['assignment_inventory'] = len(records) == 6 and {(r['import_order'],r['method']) for r in records} == {(o,m) for o in ['AB','BA'] for m in ['static_ids','native_propagation','checked_mapping']}
    checks['assignment_counts'] = all(int(r['total_electrodes']) == 40 and int(r['correct_electrodes']) == (38 if r['method'] == 'native_propagation' else 40) for r in records)
    faults = rows('fault_detection.csv')
    checks['fault_records'] = len(faults) == 8 and all(r['detected'].lower() == 'true' for r in faults) and {r['test_type'] for r in faults} == {'live_model','record_replay'}
    state = {k:k+'_reference' for k in ['geometry','roles','materials','drives','mesh_settings','solver','sampling']}
    deps = rows('dependencies.csv')
    checks['dependency_inventory'] = len(deps) == len(state) and {r['changed_input'] for r in deps} == set(state)
    checks['dependency_rules'] = all(r['invalidated_stages'].split(';') == invalidated(state,state | {r['changed_input']:'edited'}) and (r['old_field_reusable'] == 'true') == (signature('field',state) == signature('field',state | {r['changed_input']:'edited'})) for r in deps)
    acceptance = rows('response_acceptance.csv')
    checks['response_decisions'] = len(acceptance) == 2 and all((float(r['max_difference_V']) <= float(r['threshold_V'])) == (r['passed'] == 'true') for r in acceptance)
    meshes = rows('mesh_response.csv')
    checks['mesh_levels'] = [int(r['level']) for r in meshes] == [0,1,2] and all(float(r['maximum_absolute_response_mV']) > 0 and int(r['modified_elements']) > 0 for r in meshes)
    controls = rows('analytic_control.csv') + rows('linearity.csv')
    checks['control_decisions'] = len(controls) == 3 and all((float(r.get('max_error_V',r.get('max_absolute_error_V'))) <= float(r['threshold_V'])) == (r['passed'].lower() == 'true') for r in controls)
    renum = rows('renumbering.csv')
    checks['renumbering_summary'] = len(renum) == 1 and int(renum[0]['matched']) == int(renum[0]['entities']) and int(renum[0]['failures']) == 0
    result = {'status':'passed' if all(checks.values()) else 'failed','scope':'Table integrity, summary consistency and dependency rules; no field recomputation or new COMSOL solve.','checks':checks,'recorded_device_status':'UNRESOLVED' if any(r['passed'] == 'false' for r in acceptance) else 'ACCEPT'}
    out = ROOT/'outputs/result_verification.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+chr(10),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if not all(checks.values()): raise SystemExit(1)

if __name__ == '__main__': main()
