"""Replay real selection records and make explicit, controlled corruptions."""
from pathlib import Path
from copy import deepcopy
import json
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT))
from experiments.paths import run_data, resolve_record_paths
from ion_trap_chip.verification.checks import assignments,numerical_response
from ion_trap_chip.verification.comsol import resolve_boxes
from ion_trap_chip.verification.records import Verification,invalidated,signature,write_json
DATA=run_data()

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    r=json.loads((DATA/'reimport_AB/report.json').read_text(encoding='utf-8'))
    if r['status'] not in ['mapped','solved']:raise RuntimeError('Integration must finish before fault replay')
    expected=[]
    for row in r['dc_before']:
        mapped=[r['entity_maps']['2'][str(e)] for e in row['entities']]
        if row['label'] in r['import_selections']:
            native=r['import_selections'][row['label']]
            if not isinstance(native,list) or set(native)!=set(mapped):
                raise RuntimeError('Independent imported-object selection disagrees: '+row['label'])
        expected.append({**row,'entities':mapped})
    report={'oracle':'unique entity correspondence; edited electrode membership independently cross-checked against import feature selections','comparators':{},'faults':[]}
    for name,rows in [('static_ids',r['dc_before']),('native_propagation',r['native_dc_after']),('geometric_and_incidence',r['dc_after'])]:
        report['comparators'][name]=assignments(expected,rows)
    clean=deepcopy(r['dc_after']);lookup={row['label']:i for i,row in enumerate(clean)}
    cases={}
    x=deepcopy(clean);x[lookup['A7']]['entities'].pop();cases['missing_face']=x
    x=deepcopy(clean);a,b=lookup['A7'],lookup['A8'];x[a]['entities'],x[b]['entities']=x[b]['entities'],x[a]['entities'];cases['swapped_A7_A8']=x
    x=deepcopy(clean);x[lookup['B7']]['entities'][0]=x[lookup['A7']]['entities'][0];cases['shared_A7_B7_face']=x
    x=deepcopy(clean);x[lookup['A7']]['voltage']='VA8';cases['wrong_voltage']=x
    for name,rows in cases.items():
        result=assignments(expected,rows)
        report['faults'].append({'case':name,'level':'record replay','detected':not result['passed'],'details':result})
    state={key:key+'_reference' for key in ['geometry','roles','materials','drives','mesh_settings','solver','sampling']}
    report['dependencies']={}
    for key in state:
        edited=state|{key:key+'_edited'}
        report['dependencies'][key]={'invalidated':invalidated(state,edited),'old_field_reusable':signature('field',state)==signature('field',edited)}
    _,fail=resolve_boxes({1:[0,1,0,1,0,1]},{4:[0,1,0,1,0,1],5:[0,1,0,1,0,1]})
    report['ambiguity']={'level':'synthetic resolver unit input','rejected':bool(fail),'details':fail}
    before=json.loads((DATA/'reimport_AB/before_entities.json').read_text(encoding='utf-8'))['3']
    after=json.loads((DATA/'reimport_AB/after_entities.json').read_text(encoding='utf-8'))['3']
    from ion_trap_chip.verification.comsol import transformed_boxes
    manifests={k:json.loads((DATA/'cad'/(k+'_20um.json')).read_text(encoding='utf-8')) for k in ['A7','B7']}
    expected_boxes,_=transformed_boxes({int(k):v for k,v in before.items()},manifests)
    keys=list(after);permuted={10000+i:after[k] for i,k in enumerate(reversed(keys))}
    recovered,fail=resolve_boxes(expected_boxes,permuted)
    report['renumbering_replay']={'level':'saved actual domain descriptors with synthetic unique ID permutation; no additional COMSOL solve','entities':len(before),'matched':len(recovered),'failures':len(fail),'static_ids_valid':False,'passed':len(recovered)==len(before) and not fail}
    report['all_expected_checks_pass']=all(f['detected'] for f in report['faults']) and report['ambiguity']['rejected'] and report['renumbering_replay']['passed'] and report['comparators']['geometric_and_incidence']['passed']
    write_json(DATA/'fault_tests.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report['all_expected_checks_pass']:raise RuntimeError('Fault protocol failed')

if __name__=='__main__':main()
