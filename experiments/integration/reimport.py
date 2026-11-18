"""Actual A7/B7 STEP round trip, all selection remapping, and DC solve."""
from pathlib import Path
import argparse
import json
import sys
import time
import traceback
from copy import deepcopy
import numpy as np
import mph

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.paths import run_data, resolve_record_paths, input_path
sys.path.insert(0, str(ROOT))
from ion_trap_chip.verification.comsol import ids, entity_boxes, resolve_boxes, replace_cad, transformed_boxes, interpolate, adjacent_domains, complete_by_adjacency
from ion_trap_chip.verification.records import write_json, file_hash, signature, invalidated, Verification
from ion_trap_chip.verification.checks import assignments

DATA = run_data()
SOURCE = input_path('model')

def collect_selections(j):
    records = []; references = []
    def save(s, name, named_allowed=False):
        try:
            dim = list(s.dimension())
            if len(dim) != 1 or int(dim[0]) not in [0,1,2,3]: return
            values = ids(s)
            if not values: return
            named = str(s.named()) if hasattr(s, 'named') else ''
            if named and not named_allowed: return
            row = {'name': name, 'dim': int(dim[0]), 'entities': values, 'named': named}
            if hasattr(s,'inputDimension'):
                row['input_dim']=int(s.inputDimension())
                inp=s.inputEntities()
                row['input_entities']=[int(x) for x in inp] if inp is not None else []
            records.append(row);references.append(s)
        except Exception:
            return
    for tag in j.selection().tags():
        s = j.selection(tag)
        if str(s.getType()) == 'Explicit': save(s, 'selection/'+str(tag), True)
    def walk(node, name):
        try: save(node.selection(), name)
        except Exception: pass
        try:
            for tag in node.feature().tags(): walk(node.feature(tag), name+'/'+str(tag))
        except Exception: pass
    for tag in j.physics().tags(): walk(j.physics(tag), 'physics/'+str(tag))
    for tag in j.material().tags(): walk(j.material(tag), 'material/'+str(tag))
    walk(j.mesh('mesh1'), 'mesh/mesh1')
    return records, references

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--order', choices=['AB','BA'], default='AB');parser.add_argument('--solve', action='store_true');args=parser.parse_args()
    out=DATA/('reimport_'+args.order);out.mkdir(exist_ok=True)
    report={'case':'external_STEP_width_edit','order':args.order,'cores':2,'status':'started','source_sha256':file_hash(SOURCE),'protocol_sha256':file_hash(ROOT/'docs/protocol.md'),'code_sha256':{str(p.relative_to(ROOT)):file_hash(p) for folder in [ROOT/'ion_trap_chip/verification',ROOT/'experiments/integration'] for p in folder.glob('*.py')}}
    client=mph.start(cores=2,version='6.3'); print('CLIENT_READY',flush=True)
    model=client.load(str(SOURCE));j=model.java;g=j.geom('geom1');print('MODEL_LOADED',flush=True)
    try:
        records={k:json.loads((DATA/'cad'/(k+'_20um.json')).read_text(encoding='utf-8')) for k in ['A7','B7']}
        records=resolve_record_paths(records)
        selections, references=collect_selections(j)
        report['selection_snapshot']=selections
        used={dim:sorted({e for r in selections if r['dim']==dim for e in r['entities']}) for dim in range(4)}
        old={d:entity_boxes(g,d,e) for d,e in used.items() if e}
        before_adjacency=adjacent_domains(g,old[2])
        dc_before=[{'tag':str(t),'label':str(j.physics('es').feature(t).label()),'voltage':str(j.physics('es').feature(t).getString('V0')),'entities':ids(j.physics('es').feature(t).selection())} for t in j.physics('es').feature().tags() if str(j.physics('es').feature(t).getType())=='ElectricPotential']
        report['dc_before']=dc_before
        write_json(out/'before_entities.json',old)
        print('SNAPSHOT',{d:len(e) for d,e in old.items()},len(selections),flush=True)
        start=time.perf_counter()
        replace_cad(g,records,{'A7':'imp1.117','B7':'imp1.637'},['A7','B7'] if args.order=='AB' else ['B7','A7'])
        report['import_build_seconds']=time.perf_counter()-start
        report['native_dc_after']=[{**r,'entities':ids(j.physics('es').feature(r['tag']).selection())} for r in dc_before]
        print('REIMPORTED',report['import_build_seconds'],flush=True)
        mapping_start=time.perf_counter()
        counts={0:int(g.getNVertices()),1:int(g.getNEdges()),2:int(g.getNBoundaries()),3:int(g.getNDomains())}
        new={d:entity_boxes(g,d,range(1,counts[d]+1)) for d in old}
        write_json(out/'after_entities.json',new)
        maps={};failures={}; changed={}
        for d,boxes in old.items():
            expected, changed[d]=transformed_boxes(boxes,records)
            maps[d],failures[d]=resolve_boxes(expected,new[d])
        after_adjacency=adjacent_domains(g,new[2])
        if not failures[3]:
            failures[2], report['topology_resolved_faces']=complete_by_adjacency(maps[2],failures[2],maps[3],before_adjacency,after_adjacency)
        report['entity_maps']=maps;report['mapping_failures']=failures;report['transformed_entities']=changed
        print('MAPPING',{d:len(f) for d,f in failures.items()},flush=True)
        if any(failures.values()): raise ValueError('Entity correspondence requires resolution; see mapping_failures')
        report['selection_updates']=[]
        for row,s in zip(selections,references):
            values=[maps[row['dim']][e] for e in row['entities']]
            if set(ids(s))==set(values):
                report['selection_updates'].append({'name':row['name'],'action':'already_correct'})
                continue
            print('UPDATE_SELECTION',row['name'],row['dim'],len(values),flush=True)
            report['active_selection_update']=row['name']
            if row['name'].startswith('selection/'):
                s.geom('geom1',row['dim'])
            s.set(values)
            if set(ids(s))!=set(values):raise ValueError('Selection output differs after remapping: '+row['name'])
            report['selection_updates'].append({'name':row['name'],'action':'remapped'})
        report['dc_after']=[{**r,'entities':ids(j.physics('es').feature(r['tag']).selection()),'voltage':str(j.physics('es').feature(r['tag']).getString('V0'))} for r in dc_before]
        report['import_selections']={}
        for label in records:
            tag='geom1_ifq_'+label.lower()+'_bnd'
            try: report['import_selections'][label]=ids(j.selection(tag))
            except Exception as exc: report['import_selections'][label]={'error':str(exc)}
        expected=[{**r,'entities':[maps[2][e] for e in r['entities']]} for r in dc_before]
        for row in expected:
            if row['label'] in records:
                imported=report['import_selections'][row['label']]
                if not isinstance(imported,list) or set(row['entities'])!=set(imported):raise ValueError('Import membership disagrees for '+row['label'])
        report['assignment_check']=assignments(expected,report['dc_after'])
        if not report['assignment_check']['passed']:raise ValueError('Electrical assignment check failed')
        report['mapping_and_assignment_seconds']=time.perf_counter()-mapping_start
        report['live_faults']=[]
        by_label={r['label']:r for r in report['dc_after']}
        for case in ['missing_face','swapped_A7_A8','shared_A7_B7_face','wrong_voltage']:
            actual=deepcopy(report['dc_after']);lookup={r['label']:r for r in actual}
            if case=='missing_face':lookup['A7']['entities'].pop()
            elif case=='swapped_A7_A8':lookup['A7']['entities'],lookup['A8']['entities']=lookup['A8']['entities'],lookup['A7']['entities']
            elif case=='shared_A7_B7_face':lookup['B7']['entities'][0]=lookup['A7']['entities'][0]
            else:lookup['A7']['voltage']='VA8'
            changed_rows=[r for r in actual if r!=by_label[r['label']]]
            original_names={}
            for row in changed_rows:
                f=j.physics('es').feature(row['tag']);original_names[row['tag']]=str(f.selection().named())
                f.selection().set(row['entities']);f.set('V0',row['voltage'])
            observed=[{**r,'entities':ids(j.physics('es').feature(r['tag']).selection()),'voltage':str(j.physics('es').feature(r['tag']).getString('V0'))} for r in actual]
            checked=assignments(expected,observed)
            report['live_faults'].append({'case':case,'level':'actual COMSOL feature mutation and read-back; rejected before solve','detected':not checked['passed'],'check':checked})
            for row in changed_rows:
                f=j.physics('es').feature(row['tag']);original=by_label[row['label']]
                if original_names[row['tag']]:f.selection().named(original_names[row['tag']])
                else:f.selection().set(original['entities'])
                f.set('V0',original['voltage'])
        if not all(r['detected'] for r in report['live_faults']):raise ValueError('Live fault check failed')
        restored=[{**r,'entities':ids(j.physics('es').feature(r['tag']).selection()),'voltage':str(j.physics('es').feature(r['tag']).getString('V0'))} for r in expected]
        if not assignments(expected,restored)['passed']:raise ValueError('Fault test restoration failed')
        parameters={str(name):str(j.param().get(name)) for name in j.param().varnames()}
        state={'geometry':{'model':report['source_sha256'],'edit':{}},'roles':[{k:r[k] for k in ['label','tag']} for r in expected],'materials':{'source_model':report['source_sha256'],'changed':False},'drives':[{k:r[k] for k in ['label','voltage']} for r in expected],'mesh_settings':{'source_model':report['source_sha256'],'refinement':0},'solver':{'study':'std1','source_model':report['source_sha256']},'sampling':{'x_mm':1.3,'z_mm':13.2,'y_mm':[-1.65,-.70],'count':381,'quantity':'V'}}
        state['drives']={'expressions':state['drives'],'model_parameters':parameters}
        edited={**state,'geometry':{'model':report['source_sha256'],'edit':{label:r['step_sha256'] for label,r in records.items()}}}
        report['dependency_state']=edited
        report['invalidated_stages']=invalidated(state,edited)
        report['field_signature']=signature('field',edited)
        report['sample_signature']=signature('samples',edited)
        report['stale_reference_field_rejected']=signature('field',state)!=report['field_signature']
        provenance=all(file_hash(Path(r['step']))==r['step_sha256'] for r in records.values())
        report['verification']={'geometry':all(r['after']['valid'] for r in records.values()),'assignment':True,'provenance':provenance,'numerics':None,'status':Verification(True,True,provenance,None).status}
        if not provenance:raise ValueError('STEP changed after manifest generation')
        report['remapped_selections']=len(selections)
        report['changed_selections']=sum(r['action']=='remapped' for r in report['selection_updates'])
        report['changed_entity_ids']={d:sum(a!=b for a,b in mapping.items()) for d,mapping in maps.items()}
        for tag in j.sol().tags(): j.sol(tag).clearSolutionData()
        if args.solve:
            start=time.perf_counter();print('SOLVING_DC',flush=True);j.study('std1').run();report['dc_solve_seconds']=time.perf_counter()-start
            report['mesh']={'vertices':int(j.mesh('mesh1').getNumVertex()),'elements':int(j.mesh('mesh1').getNumElem())}
            y=np.linspace(-1.65,-.70,381);coords=np.vstack([np.full_like(y,1.3),y,np.full_like(y,13.2)])
            potential=interpolate(j,coords)
            np.savez_compressed(out/'profile.npz',coords_mm=coords,potential_V=potential)
            report['potential_range_V']=[float(potential.min()),float(potential.max())]
        model.save(str(out/'model.mph'))
        report['status']='solved' if args.solve else 'mapped'
    except Exception as exc:
        report['status']='failed';report['error']=str(exc);traceback.print_exc()
    finally:
        write_json(out/'report.json',report);client.remove(model)
        print('FINISHED',report['status'],flush=True)

if __name__=='__main__': main()
